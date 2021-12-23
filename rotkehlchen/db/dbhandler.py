import json
import logging
import os
import re
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Type, Union, cast

from pysqlcipher3 import dbapi2 as sqlcipher
from typing_extensions import Literal

from rotkehlchen.accounting.structures import ActionType, BalanceType, HistoryBaseEntry
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import (
    XpubData,
    XpubDerivedAddressData,
    deserialize_derivation_path_for_db,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap import (
    SUSHISWAP_TRADES_PREFIX,
    UNISWAP_TRADES_PREFIX,
)
from rotkehlchen.chain.ethereum.interfaces.ammswap.typing import EventType, LiquidityPoolEvent
from rotkehlchen.chain.ethereum.modules.aave.common import atoken_to_asset
from rotkehlchen.chain.ethereum.modules.adex import (
    ADEX_EVENTS_PREFIX,
    AdexEventType,
    Bond,
    ChannelWithdraw,
    Unbond,
    UnbondRequest,
    deserialize_adex_event_from_db,
)
from rotkehlchen.chain.ethereum.modules.balancer import (
    BALANCER_EVENTS_PREFIX,
    BALANCER_TRADES_PREFIX,
    BalancerEvent,
)
from rotkehlchen.chain.ethereum.modules.sushiswap import SUSHISWAP_EVENTS_PREFIX
from rotkehlchen.chain.ethereum.modules.uniswap import UNISWAP_EVENTS_PREFIX
from rotkehlchen.chain.ethereum.structures import (
    AaveEvent,
    YearnVault,
    YearnVaultEvent,
    aave_event_from_db,
)
from rotkehlchen.chain.ethereum.trades import AMMSwap
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.constants.ethereum import YEARN_VAULTS_PREFIX, YEARN_VAULTS_V2_PREFIX
from rotkehlchen.constants.limits import FREE_ASSET_MOVEMENTS_LIMIT, FREE_TRADES_LIMIT
from rotkehlchen.constants.misc import NFT_DIRECTIVE
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.eth2 import ETH2_DEPOSITS_PREFIX
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    HistoryEventFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.schema_transient import DB_SCRIPT_CREATE_TRANSIENT_TABLES
from rotkehlchen.db.settings import (
    DEFAULT_PREMIUM_SHOULD_SYNC,
    ROTKEHLCHEN_DB_VERSION,
    DBSettings,
    ModifiableDBSettings,
    db_settings_from_dict,
)
from rotkehlchen.db.upgrade_manager import DBUpgradeManager
from rotkehlchen.db.utils import (
    BlockchainAccounts,
    DBAssetBalance,
    LocationData,
    SingleDBAssetBalance,
    Tag,
    deserialize_tags_from_db,
    form_query_to_filter_timestamps,
    insert_tag_mappings,
    is_valid_db_blockchain_account,
    str_to_bool,
)
from rotkehlchen.errors import (
    AuthenticationError,
    DeserializationError,
    IncorrectApiKeyFormat,
    InputError,
    SystemPermissionError,
    TagConstraintError,
    UnknownAsset,
    UnsupportedAsset,
)
from rotkehlchen.exchanges.binance import BINANCE_MARKETS_KEY
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.ftx import FTX_SUBACCOUNT_DB_SETTING
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.serialization.deserialize import deserialize_hex_color_code
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    BlockchainAccountData,
    BTCAddress,
    ChecksumEthAddress,
    ExchangeApiCredentials,
    ExternalService,
    ExternalServiceApiCredentials,
    HexColorCode,
    ListOfBlockchainAddresses,
    Location,
    ModuleName,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hashing import file_md5
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KDF_ITER = 64000
DBINFO_FILENAME = 'dbinfo.json'
MAIN_DB_NAME = 'rotkehlchen.db'
TRANSIENT_DB_NAME = 'rotkehlchen_transient.db'
PASSWORDCHECK_STATEMENT = 'SELECT name FROM sqlite_master WHERE type="table";'

DBTupleType = Literal[
    'trade',
    'asset_movement',
    'margin_position',
    'ethereum_transaction',
    'amm_swap',
    'accounting_event',
]

# Tuples that contain first the name of a table and then the columns that
# reference assets ids. This is used to query all assets that a user owns.
TABLES_WITH_ASSETS = (
    ('aave_events', 'asset1', 'asset2'),
    ('yearn_vaults_events', 'from_asset', 'to_asset'),
    ('manually_tracked_balances', 'asset'),
    ('trades', 'base_asset', 'quote_asset', 'fee_currency'),
    ('margin_positions', 'pl_currency', 'fee_currency'),
    ('asset_movements', 'asset', 'fee_asset'),
    ('ledger_actions', 'asset', 'rate_asset'),
    ('amm_swaps', 'token0_identifier', 'token1_identifier'),
    ('amm_events', 'token0_identifier', 'token1_identifier'),
    ('adex_events', 'token'),
    ('balancer_events', 'pool_address_token'),
    ('timed_balances', 'currency'),
)


DB_BACKUP_RE = re.compile(r'(\d+)_rotkehlchen_db_v(\d+).backup')


def _protect_password_sqlcipher(password: str) -> str:
    """A double quote in the password would close the string. To escape it double it

    source: https://stackoverflow.com/a/603579/110395
"""
    return password.replace(r'"', r'""')


def detect_sqlcipher_version() -> int:
    """Returns the major part of the version of the system's sqlcipher package"""
    conn = sqlcipher.connect(':memory:')  # pylint: disable=no-member
    query = conn.execute('PRAGMA cipher_version;')
    version = query.fetchall()[0][0]

    match = re.search(r'(\d+).(\d+).(\d+)', version)
    if not match:
        raise ValueError(f'Could not process the version returned by sqlcipher: {version}')

    sqlcipher_version = int(match.group(1))
    conn.close()
    return sqlcipher_version


def db_tuple_to_str(
        data: Tuple[Any, ...],
        tuple_type: DBTupleType,
) -> str:
    """Turns a tuple DB entry for trade, or asset_movement into a user readable string

    This is only intended for error messages.

    TODO: Add some unit tests
    """
    if tuple_type == 'trade':
        return (
            f'{TradeType.deserialize_from_db(data[5])} trade with id {data[0]} '
            f'in {Location.deserialize_from_db(data[2])} and base/quote asset {data[3]} / '
            f'{data[4]} at timestamp {data[1]}'
        )
    if tuple_type == 'asset_movement':
        return (
            f'{AssetMovementCategory.deserialize_from_db(data[2])} of '
            f'{data[4]} with id {data[0]} '
            f'in {Location.deserialize_from_db(data[1])} at timestamp {data[3]}'
        )
    if tuple_type == 'margin_position':
        return (
            f'Margin position with id {data[0]} in  {Location.deserialize_from_db(data[1])} '
            f'for {data[5]} closed at timestamp {data[3]}'
        )
    if tuple_type == 'ethereum_transaction':
        return f'Ethereum transaction with hash "{data[0].hex()}"'
    if tuple_type == 'amm_swap':
        return (
            f'AMM swap with id {data[0]}-{data[1]} '
            f'in {Location.deserialize_from_db(data[6])} '
        )

    raise AssertionError('db_tuple_to_str() called with invalid tuple_type {tuple_type}')


# https://stackoverflow.com/questions/4814167/storing-time-series-data-relational-or-non
# http://www.sql-join.com/sql-join-types
class DBHandler:
    def __init__(
            self,
            user_data_dir: Path,
            password: str,
            msg_aggregator: MessagesAggregator,
            initial_settings: Optional[ModifiableDBSettings],
    ):
        """Database constructor

        May raise:
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error.
        - AuthenticationError if SQLCipher version problems are detected
        - SystemPermissionError if the DB file's permissions are not correct
        """
        self.msg_aggregator = msg_aggregator
        self.user_data_dir = user_data_dir
        self.sqlcipher_version = detect_sqlcipher_version()
        self.last_write_ts: Optional[Timestamp] = None
        self.conn: sqlcipher.Connection = None  # pylint: disable=no-member
        self.conn_transient: sqlcipher.Connection = None  # pylint: disable=no-member
        self._connect(password)
        self._run_actions_after_first_connection(password)
        if initial_settings is not None:
            self.set_settings(initial_settings)
        self.update_owned_assets_in_globaldb()
        self.add_globaldb_assetids()
        self.ensure_data_integrity()

    def __del__(self) -> None:
        if hasattr(self, 'conn') and self.conn:
            self.disconnect(conn_attribute='conn')
        if hasattr(self, 'conn_transient') and self.conn_transient:
            self.disconnect(conn_attribute='conn_transient')
        try:
            dbinfo = {'sqlcipher_version': self.sqlcipher_version, 'md5_hash': self.get_md5hash()}
        except (SystemPermissionError, FileNotFoundError) as e:
            # If there is problems opening the DB at destruction just log and exit
            log.error(f'At DB teardown could not open the DB: {str(e)}')
            return

        with open(self.user_data_dir / DBINFO_FILENAME, 'w') as f:
            f.write(rlk_jsondumps(dbinfo))

    def _run_actions_after_first_connection(self, password: str) -> None:
        """Perform the actions that are needed after the first DB connection

        Such as:
            - DB Upgrades
            - Create tables that are missing for new version

        May raise:
        - AuthenticationError if a wrong password is given or if the DB is corrupt
        - DBUpgradeError if there is a problem with DB upgrading
        """
        # Run upgrades if needed
        fresh_db = DBUpgradeManager(self).run_upgrades()
        # create tables if needed (first run - or some new tables)
        self.conn.executescript(DB_SCRIPT_CREATE_TABLES)
        if fresh_db:  # add DB version. https://github.com/rotki/rotki/issues/3744
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('version', str(ROTKEHLCHEN_DB_VERSION)),
            )
        # set up transient connection
        self._connect(password, conn_attribute='conn_transient')
        # creating tables if necessary
        if hasattr(self, 'conn_transient') and self.conn_transient:
            self.conn_transient.executescript(DB_SCRIPT_CREATE_TRANSIENT_TABLES)

    def get_md5hash(self, transient: bool = False) -> str:
        """Get the md5hash of the DB

        May raise:
        - SystemPermissionError if there are permission errors when accessing the DB
        """
        no_active_connection = not hasattr(self, 'conn') or not self.conn
        assert no_active_connection, 'md5hash should be taken only with a closed DB'
        if transient:
            return file_md5(self.user_data_dir / TRANSIENT_DB_NAME)
        return file_md5(self.user_data_dir / MAIN_DB_NAME)

    def get_version(self) -> int:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings WHERE name=?;', ('version',),
        )
        query = query.fetchall()
        # If setting is not set, it's the latest version
        if len(query) == 0:
            return ROTKEHLCHEN_DB_VERSION

        return int(query[0][0])

    def set_version(self, version: int) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('version', str(version)),
        )
        self.conn.commit()

    def _connect(
            self,
            password: str,
            conn_attribute: Literal['conn', 'conn_transient'] = 'conn',
    ) -> None:
        """Connect to the DB using password

        May raise:
        - SystemPermissionError if we are unable to open the DB file,
        probably due to permission errors
        - AuthenticationError if the given password is not the right one for the DB
        """
        if conn_attribute == 'conn':
            fullpath = self.user_data_dir / MAIN_DB_NAME
        else:
            fullpath = self.user_data_dir / TRANSIENT_DB_NAME
        try:
            conn: sqlcipher.Connection = sqlcipher.connect(str(fullpath))  # pylint: disable=no-member  # noqa: E501
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            raise SystemPermissionError(
                f'Could not open database file: {fullpath}. Permission errors?',
            ) from e

        conn.text_factory = str
        password_for_sqlcipher = _protect_password_sqlcipher(password)
        script = f'PRAGMA key="{password_for_sqlcipher}";'
        if self.sqlcipher_version == 3:
            script += f'PRAGMA kdf_iter={KDF_ITER};'
        try:
            conn.executescript(script)
            conn.execute('PRAGMA foreign_keys=ON')
            # Optimizations for the combined trades view
            # the following will fail with DatabaseError in case of wrong password.
            # If this goes away at any point it needs to be replaced by something
            # that checks the password is correct at this same point in the code
            conn.execute('PRAGMA cache_size = -32768')
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            del self.conn
            raise AuthenticationError(
                'Wrong password or invalid/corrupt database for user',
            ) from e

        setattr(self, conn_attribute, conn)

    def _change_password(
            self,
            new_password: str,
            conn_attribute: Literal['conn', 'conn_transient'],
    ) -> bool:
        conn = getattr(self, conn_attribute, None)
        if conn is None:
            log.error(
                f'Attempted to change password for {conn_attribute} '
                f'database but no such DB connection exists',
            )
            return False
        conn.text_factory = str
        new_password_for_sqlcipher = _protect_password_sqlcipher(new_password)
        script = f'PRAGMA rekey="{new_password_for_sqlcipher}";'
        if self.sqlcipher_version == 3:
            script += f'PRAGMA kdf_iter={KDF_ITER};'
        try:
            conn.executescript(script)
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            log.error(
                f'At change password could not re-key the open {conn_attribute} '
                f'database: {str(e)}',
            )
            return False
        return True

    def change_password(self, new_password: str) -> bool:
        """Changes the password for the currently logged in user"""
        result = (
            self._change_password(new_password, 'conn') and
            self._change_password(new_password, 'conn_transient')
        )
        return result

    def disconnect(self, conn_attribute: Literal['conn', 'conn_transient'] = 'conn') -> None:
        conn = getattr(self, conn_attribute, None)
        if conn:
            conn.close()
            setattr(self, conn_attribute, None)

    def export_unencrypted(self, temppath: Path) -> None:
        self.conn.executescript(
            'ATTACH DATABASE "{}" AS plaintext KEY "";'
            'SELECT sqlcipher_export("plaintext");'
            'DETACH DATABASE plaintext;'.format(temppath),
        )

    def import_unencrypted(self, unencrypted_db_data: bytes, password: str) -> None:
        """Imports an unencrypted DB from raw data

        May raise:
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error.
        - AuthenticationError if the wrong password is given
        """
        self.disconnect()
        rdbpath = self.user_data_dir / MAIN_DB_NAME
        # Make copy of existing encrypted DB before removing it
        shutil.copy2(
            rdbpath,
            self.user_data_dir / 'rotkehlchen_temp_backup.db',
        )
        rdbpath.unlink()

        # dump the unencrypted data into a temporary file
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdbpath = os.path.join(tmpdirname, 'temp.db')
            with open(tempdbpath, 'wb') as f:
                f.write(unencrypted_db_data)

            # Now attach to the unencrypted DB and copy it to our DB and encrypt it
            self.conn = sqlcipher.connect(tempdbpath)  # pylint: disable=no-member
            password_for_sqlcipher = _protect_password_sqlcipher(password)
            script = f'ATTACH DATABASE "{rdbpath}" AS encrypted KEY "{password_for_sqlcipher}";'
            if self.sqlcipher_version == 3:
                script += f'PRAGMA encrypted.kdf_iter={KDF_ITER};'
            script += 'SELECT sqlcipher_export("encrypted");DETACH DATABASE encrypted;'
            self.conn.executescript(script)
            self.disconnect()

        try:
            self._connect(password)
        except SystemPermissionError as e:
            raise AssertionError(
                f'Permission error when reopening the DB. {str(e)}. Should never happen here',
            ) from e
        self._run_actions_after_first_connection(password)
        # all went okay, remove the original temp backup
        (self.user_data_dir / 'rotkehlchen_temp_backup.db').unlink()

    def update_last_write(self) -> None:
        # Also keep it in memory for faster querying
        self.last_write_ts = ts_now()
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('last_write_ts', str(self.last_write_ts)),
        )
        self.conn.commit()

    def get_last_write_ts(self) -> Timestamp:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings where name=?;', ('last_write_ts',),
        )
        query = query.fetchall()
        # If setting is not set, it's 0 by default
        if len(query) == 0:
            ts = 0
        else:
            ts = int(query[0][0])
        return Timestamp(ts)

    def update_last_data_upload_ts(self, ts: Timestamp) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('last_data_upload_ts', str(ts)),
        )
        self.update_last_write()

    def get_last_data_upload_ts(self) -> Timestamp:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings where name=?;', ('last_data_upload_ts',),
        )
        query = query.fetchall()
        # If setting is not set, it's 0 by default
        if len(query) == 0:
            ts = 0
        else:
            ts = int(query[0][0])
        return Timestamp(ts)

    def update_premium_sync(self, should_sync: bool) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('premium_should_sync', str(should_sync)),
        )
        self.update_last_write()

    def get_premium_sync(self) -> bool:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings where name=?;', ('premium_should_sync',),
        )
        query = query.fetchall()
        # If setting is not set, return default
        if len(query) == 0:
            return DEFAULT_PREMIUM_SHOULD_SYNC
        return str_to_bool(query[0][0])

    def get_settings(self, have_premium: bool = False) -> DBSettings:
        """Aggregates settings from DB and from the given args and returns the settings object"""
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT name, value FROM settings;',
        )
        query = query.fetchall()

        settings_dict = {}
        for q in query:
            settings_dict[q[0]] = q[1]

        # Also add the non-DB saved settings
        settings_dict['have_premium'] = have_premium

        return db_settings_from_dict(settings_dict, self.msg_aggregator)

    def get_main_currency(self) -> Asset:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM settings WHERE name="main_currency";',
        )
        query = query.fetchall()
        if len(query) == 0:
            return A_USD

        result = query[0][0]
        return Asset(result)

    def set_settings(self, settings: ModifiableDBSettings) -> None:
        settings_dict = settings.serialize()
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            list(settings_dict.items()),
        )
        self.update_last_write()

    def add_external_service_credentials(
            self,
            credentials: List[ExternalServiceApiCredentials],
    ) -> None:
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key) VALUES(?, ?)',
            [c.serialize_for_db() for c in credentials],
        )
        self.update_last_write()

    def delete_external_service_credentials(self, services: List[ExternalService]) -> None:
        cursor = self.conn.cursor()
        cursor.executemany(
            'DELETE FROM external_service_credentials WHERE name=?;',
            [(service.name.lower(),) for service in services],
        )
        self.update_last_write()

    def get_all_external_service_credentials(self) -> List[ExternalServiceApiCredentials]:
        """Returns a list with all the external service credentials saved in the DB"""
        cursor = self.conn.cursor()
        query = cursor.execute('SELECT name, api_key from external_service_credentials;')

        result = []
        for q in query:
            try:
                service = ExternalService.deserialize(q[0])
            except DeserializationError:
                log.error(f'Unknown external service name "{q[0]}" found in the DB')
                continue

            result.append(ExternalServiceApiCredentials(
                service=service,
                api_key=q[1],
            ))
        return result

    def get_external_service_credentials(
            self,
            service_name: ExternalService,
    ) -> Optional[ExternalServiceApiCredentials]:
        """If existing it returns the external service credentials for the given service"""
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT api_key from external_service_credentials WHERE name=?;',
            (service_name.name.lower(),),
        )
        query = query.fetchall()
        if len(query) == 0:
            return None

        # There can only be 1 result, since name is the primary key of the table
        return ExternalServiceApiCredentials(service=service_name, api_key=query[0][0])

    def add_to_ignored_assets(self, asset: Asset) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO multisettings(name, value) VALUES(?, ?)',
            ('ignored_asset', asset.identifier),
        )
        self.update_last_write()

    def remove_from_ignored_assets(self, asset: Asset) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM multisettings WHERE name="ignored_asset" AND value=?;',
            (asset.identifier,),
        )
        self.update_last_write()

    def get_ignored_assets(self) -> List[Asset]:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT value FROM multisettings WHERE name="ignored_asset";',
        )
        return [Asset(q[0]) for q in cursor]

    def add_to_ignored_action_ids(self, action_type: ActionType, identifiers: List[str]) -> None:
        """Adds a list of identifiers to be ignored for a given action type

        Raises InputError in case of adding already existing ignored action
        """
        cursor = self.conn.cursor()
        tuples = [(action_type.serialize_for_db(), x) for x in identifiers]
        try:
            cursor.executemany(
                'INSERT INTO ignored_actions(type, identifier) VALUES(?, ?)',
                tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError('One of the given action ids already exists in the dataase') from e

        self.update_last_write()

    def remove_from_ignored_action_ids(
            self,
            action_type: ActionType,
            identifiers: List[str],
    ) -> None:
        """Removes a list of identifiers to be ignored for a given action type

        Raises InputError in case of removing an action that is not in the DB
        """
        cursor = self.conn.cursor()
        tuples = [(action_type.serialize_for_db(), x) for x in identifiers]
        cursor.executemany(
            'DELETE FROM ignored_actions WHERE type=? AND identifier=?;',
            tuples,
        )
        affected_rows = cursor.rowcount
        if affected_rows != len(identifiers):
            self.conn.rollback()
            raise InputError(
                f'Tried to remove {len(identifiers) - affected_rows} '
                f'ignored actions that do not exist',
            )
        self.update_last_write()

    def get_ignored_action_ids(
            self,
            action_type: Optional[ActionType],
    ) -> Dict[ActionType, List[str]]:
        cursor = self.conn.cursor()
        query = 'SELECT type, identifier from ignored_actions'

        tuples: Tuple
        if action_type is None:
            query += ';'
            tuples = ()
        else:
            query += ' WHERE type=?;'
            tuples = (action_type.serialize_for_db(),)

        result = cursor.execute(query, tuples)
        mapping = defaultdict(list)
        for entry in result:
            mapping[ActionType.deserialize_from_db(entry[0])].append(entry[1])

        return mapping

    def add_multiple_balances(self, balances: List[DBAssetBalance]) -> None:
        """Execute addition of multiple balances in the DB"""
        cursor = self.conn.cursor()

        for entry in balances:
            try:
                cursor.execute(
                    'INSERT INTO timed_balances('
                    '    time, currency, amount, usd_value, category) '
                    ' VALUES(?, ?, ?, ?, ?)',
                    (entry.time, entry.asset.identifier, entry.amount, entry.usd_value, entry.category.serialize_for_db()),  # noqa: E501
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Adding timed_balance failed. Either asset with identifier '
                    f'{entry.asset.identifier} is not known or an entry for timestamp '
                    f'{entry.time} already exists. Skipping.',
                )
                continue
        self.update_last_write()

    def add_aave_events(self, address: ChecksumEthAddress, events: Sequence[AaveEvent]) -> None:
        cursor = self.conn.cursor()
        for e in events:
            event_tuple = e.to_db_tuple(address)
            try:
                cursor.execute(
                    'INSERT INTO aave_events( '
                    'address, '
                    'event_type, '
                    'block_number, '
                    'timestamp, '
                    'tx_hash, '
                    'log_index, '
                    'asset1, '
                    'asset1_amount, '
                    'asset1_usd_value, '
                    'asset2, '
                    'asset2amount_borrowrate_feeamount, '
                    'asset2usd_value_accruedinterest_feeusdvalue, '
                    'borrow_rate_mode) '

                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ? , ? , ? , ?)',
                    event_tuple,
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add an aave event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping...',
                )
                continue

        self.update_last_write()

    def get_aave_events(
            self,
            address: ChecksumEthAddress,
            atoken: Optional[EthereumToken] = None,
    ) -> List[AaveEvent]:
        """Get aave for a single address and a single aToken """
        cursor = self.conn.cursor()
        querystr = 'SELECT * FROM aave_events '
        values: Tuple
        if atoken is not None:  # when called by blockchain
            underlying_token = atoken_to_asset(atoken)
            if underlying_token is None:  # should never happen
                self.msg_aggregator.add_error(
                    'Tried to query aave events for atoken with no underlying token. '
                    'Returning no events.',
                )
                return []

            querystr += 'WHERE address = ? AND (asset1=? OR asset1=?);'
            values = (address, atoken.identifier, underlying_token.identifier)
        else:  # called by graph
            querystr += 'WHERE address = ?;'
            values = (address,)

        query = cursor.execute(querystr, values)
        events = []
        for result in query:
            try:
                event = aave_event_from_db(result)
            except DeserializationError:
                continue  # skip entry. Above function should already log an error
            events.append(event)

        return events

    def delete_aave_data(self) -> None:
        """Delete all historical aave event data"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM aave_events;')
        cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')
        self.update_last_write()

    def add_adex_events(
            self,
            events: Sequence[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]],
    ) -> None:
        query = (
            """
            INSERT INTO adex_events (
                tx_hash,
                address,
                identity_address,
                timestamp,
                type,
                pool_id,
                amount,
                usd_value,
                bond_id,
                nonce,
                slashed_at,
                unlock_at,
                channel_id,
                token,
                log_index
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        cursor = self.conn.cursor()
        for event in events:
            event_tuple = event.to_db_tuple()
            try:
                cursor.execute(query, event_tuple)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add an AdEx event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping event.',
                )
                continue

        self.update_last_write()

    def get_adex_events(
            self,
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
            address: Optional[ChecksumEthAddress] = None,
            bond_id: Optional[str] = None,
            event_type: Optional[AdexEventType] = None,
    ) -> List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]:
        """Returns a list of AdEx events optionally filtered by time and address.
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM adex_events '
        # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
        filters = []
        if address is not None:
            filters.append(f'address="{address}" ')
        if bond_id is not None:
            filters.append(f'bond_id="{bond_id}"')
        if event_type is not None:
            filters.append(f'type="{str(event_type)}"')

        if filters:
            query += 'WHERE '
            query += 'AND '.join(filters)

        query, bindings = form_query_to_filter_timestamps(
            query=query,
            timestamp_attribute='timestamp',
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )
        results = cursor.execute(query, bindings)

        events = []
        for event_tuple in results:
            try:
                event = deserialize_adex_event_from_db(event_tuple)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing AdEx event from the DB. Skipping event. '
                    f'Error was: {str(e)}',
                )
                continue
            events.append(event)

        return events

    def delete_adex_events_data(self) -> None:
        """Delete all historical AdEx events data"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM adex_events;')
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{ADEX_EVENTS_PREFIX}%";',
        )
        self.update_last_write()

    def add_balancer_events(
            self,
            events: Sequence[BalancerEvent],
    ) -> None:
        query = (
            """
            INSERT INTO balancer_events (
                tx_hash,
                log_index,
                address,
                timestamp,
                type,
                pool_address_token,
                lp_amount,
                usd_value,
                amount0,
                amount1,
                amount2,
                amount3,
                amount4,
                amount5,
                amount6,
                amount7
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """
        )
        cursor = self.conn.cursor()
        for event in events:
            event_tuple = event.to_db_tuple()
            try:
                cursor.execute(query, event_tuple)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add a Balancer event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping event.',
                )
                continue

        self.update_last_write()

    def get_balancer_events(
            self,
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
            address: Optional[ChecksumEthAddress] = None,
    ) -> List[BalancerEvent]:
        """Returns a list of Balancer events optionally filtered by time and address"""
        cursor = self.conn.cursor()
        query = 'SELECT * FROM balancer_events '
        # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
        filters = []
        if address is not None:
            filters.append(f'address="{address}" ')

        if filters:
            query += 'WHERE '
            query += 'AND '.join(filters)

        query, bindings = form_query_to_filter_timestamps(
            query=query,
            timestamp_attribute='timestamp',
            from_ts=from_timestamp,
            to_ts=to_timestamp,
        )
        results = cursor.execute(query, bindings)

        events = []
        for event_tuple in results:
            try:
                event = BalancerEvent.deserialize_from_db(event_tuple)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing Balancer event from the DB. Skipping event. '
                    f'Error was: {str(e)}',
                )
                continue
            events.append(event)

        return events

    def delete_balancer_trades_data(self) -> None:
        """Delete all historical Balancer trades data"""
        cursor = self.conn.cursor()
        cursor.execute(
            f'DELETE FROM amm_swaps WHERE location="{Location.BALANCER.serialize_for_db()}";',  # pylint: disable=no-member  # noqa: E501
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{BALANCER_TRADES_PREFIX}%";',
        )
        self.update_last_write()

    def delete_balancer_events_data(self) -> None:
        """Delete all historical Balancer events data"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM balancer_events;')
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{BALANCER_EVENTS_PREFIX}%";',
        )
        self.update_last_write()

    def delete_eth2_deposits(self) -> None:
        """Delete all historical ETH2 eth2_deposits data"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM eth2_deposits;')
        cursor.execute(f'DELETE FROM used_query_ranges WHERE name LIKE "{ETH2_DEPOSITS_PREFIX}%";')
        self.update_last_write()

    def delete_eth2_daily_stats(self) -> None:
        """Delete all historical ETH2 eth2_daily_staking_details data"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM eth2_daily_staking_details;')
        self.update_last_write()

    def add_amm_events(self, events: Sequence[LiquidityPoolEvent]) -> None:
        query = (
            """
            INSERT INTO amm_events (
                tx_hash,
                log_index,
                address,
                timestamp,
                type,
                pool_address,
                token0_identifier,
                token1_identifier,
                amount0,
                amount1,
                usd_price,
                lp_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        cursor = self.conn.cursor()
        for event in events:
            event_tuple = event.to_db_tuple()
            try:
                cursor.execute(query, event_tuple)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add an AMM event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping event.',
                )
                continue

        self.update_last_write()

    def get_amm_events(
            self,
            events: List[EventType],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            address: Optional[ChecksumEthAddress] = None,
    ) -> List[LiquidityPoolEvent]:
        """Returns a list of amm events optionally filtered by time, location
        and address
        """
        cursor = self.conn.cursor()
        events_sql_str = ", ".join([f'"{EventType.serialize_for_db(event)}"' for event in events])
        query = f'SELECT * FROM amm_events WHERE amm_events.type IN ({events_sql_str}) '

        # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
        if address is not None:
            query += f'AND address="{address}" '

        query, bindings = form_query_to_filter_timestamps(query, 'timestamp', from_ts, to_ts)
        results = cursor.execute(query, bindings)

        db_events = []
        for event_tuple in results:
            try:
                event = LiquidityPoolEvent.deserialize_from_db(event_tuple)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing AMM event from the DB. Skipping event. '
                    f'Error was: {str(e)}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing AMM event from the DB. Skipping event. '
                    f'Unknown asset {e.asset_name} found',
                )
                continue
            db_events.append(event)

        return db_events

    def purge_module_data(self, module_name: Optional[ModuleName]) -> None:
        if module_name is None:
            self.delete_uniswap_trades_data()
            self.delete_uniswap_events_data()
            self.delete_sushiswap_trades_data()
            self.delete_sushiswap_events_data()
            self.delete_balancer_trades_data()
            self.delete_balancer_events_data()
            self.delete_aave_data()
            self.delete_adex_events_data()
            self.delete_yearn_vaults_data(version=1)
            self.delete_yearn_vaults_data(version=2)
            self.delete_loopring_data()
            self.delete_eth2_deposits()
            self.delete_eth2_daily_stats()
            log.debug('Purged all module data from the DB')
            return

        if module_name == 'uniswap':
            self.delete_uniswap_trades_data()
            self.delete_uniswap_events_data()
        elif module_name == 'sushiswap':
            self.delete_sushiswap_trades_data()
            self.delete_sushiswap_events_data()
        elif module_name == 'balancer':
            self.delete_balancer_trades_data()
            self.delete_balancer_events_data()
        elif module_name == 'aave':
            self.delete_aave_data()
        elif module_name == 'adex':
            self.delete_adex_events_data()
        elif module_name == 'yearn_vaults':
            self.delete_yearn_vaults_data(version=1)
        elif module_name == 'yearn_vaults_v2':
            self.delete_yearn_vaults_data(version=2)
        elif module_name == 'loopring':
            self.delete_loopring_data()
        elif module_name == 'eth2':
            self.delete_eth2_deposits()
            self.delete_eth2_daily_stats()
        else:
            log.debug(f'Requested to purge {module_name} data from the DB but nothing to do')
            return

        log.debug(f'Purged {module_name} data from the DB')

    def delete_uniswap_trades_data(self) -> None:
        """Delete all historical Uniswap trades data"""
        cursor = self.conn.cursor()
        cursor.execute(
            f'DELETE FROM amm_swaps WHERE location="{Location.UNISWAP.serialize_for_db()}";',  # pylint: disable=no-member  # noqa: E501
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{UNISWAP_TRADES_PREFIX}%";',
        )
        self.update_last_write()

    def delete_uniswap_events_data(self) -> None:
        """Delete all historical Uniswap events data"""
        cursor = self.conn.cursor()
        mint_uniswap = EventType.serialize_for_db(EventType.MINT_UNISWAP)
        burn_uniswap = EventType.serialize_for_db(EventType.BURN_UNISWAP)
        uniswap_types = f'"{mint_uniswap}", "{burn_uniswap}"'
        cursor.execute(
            f'DELETE FROM amm_events WHERE amm_events.type IN ({uniswap_types});',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{UNISWAP_EVENTS_PREFIX}%";',
        )
        self.update_last_write()

    def delete_sushiswap_trades_data(self) -> None:
        """Delete all historical Sushiswap trades data"""
        cursor = self.conn.cursor()
        cursor.execute(
            f'DELETE FROM amm_swaps WHERE location="{Location.SUSHISWAP.serialize_for_db()}";',  # pylint: disable=no-member  # noqa: E501
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{SUSHISWAP_TRADES_PREFIX}%";',
        )
        self.update_last_write()

    def delete_sushiswap_events_data(self) -> None:
        """Delete all historical Sushiswap events data"""
        cursor = self.conn.cursor()
        mint_sushiswap = EventType.serialize_for_db(EventType.MINT_SUSHISWAP)
        burn_sushiswap = EventType.serialize_for_db(EventType.BURN_SUSHISWAP)
        sushiswap_types = f'"{mint_sushiswap}", "{burn_sushiswap}"'
        cursor.execute(
            f'DELETE FROM amm_events WHERE amm_events.type IN ({sushiswap_types});',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{SUSHISWAP_EVENTS_PREFIX}%";',
        )
        self.update_last_write()

    def add_yearn_vaults_events(
            self,
            address: ChecksumEthAddress,
            events: List[YearnVaultEvent],
    ) -> None:
        cursor = self.conn.cursor()
        for e in events:
            event_tuple = e.serialize_for_db(address)
            try:
                cursor.execute(
                    'INSERT INTO yearn_vaults_events( '
                    'address, '
                    'event_type, '
                    'from_asset, '
                    'from_amount, '
                    'from_usd_value, '
                    'to_asset, '
                    'to_amount, '
                    'to_usd_value, '
                    'pnl_amount, '
                    'pnl_usd_value, '
                    'block_number, '
                    'timestamp, '
                    'tx_hash, '
                    'log_index,'
                    'version)'
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    event_tuple,
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add a yearn vault event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping...',
                )

        self.update_last_write()

    def get_yearn_vaults_events(
            self,
            address: ChecksumEthAddress,
            vault: YearnVault,
    ) -> List[YearnVaultEvent]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT * from yearn_vaults_events WHERE address=? '
            'AND (from_asset=? OR from_asset=?);',
            (address, vault.underlying_token.identifier, vault.token.identifier),
        )
        events = []
        for result in query:
            try:
                events.append(YearnVaultEvent.deserialize_from_db(result))
            except (DeserializationError, UnknownAsset) as e:
                msg = f'Failed to read yearn vault event from database due to {str(e)}'
                self.msg_aggregator.add_warning(msg)
                log.warning(msg, data=result)
        return events

    def get_yearn_vaults_v2_events(
        self,
        address: ChecksumEthAddress,
        from_block: int,
        to_block: int,
    ) -> List[YearnVaultEvent]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT * from yearn_vaults_events WHERE address=? AND version=2 '
            'AND block_number BETWEEN ? AND ?',
            (address, from_block, to_block),
        )
        events = []
        for result in query:
            try:
                events.append(YearnVaultEvent.deserialize_from_db(result))
            except (DeserializationError, UnknownAsset) as e:
                msg = f'Failed to read yearn vault event from database due to {str(e)}'
                self.msg_aggregator.add_warning(msg)
                log.warning(msg, data=result)
        return events

    def delete_yearn_vaults_data(self, version: int = 1) -> None:
        """Delete all historical yearn vault events data"""
        if version not in (1, 2):
            log.error(f'Called delete yearn vault data with non valid version {version}')
            return None
        prefix = YEARN_VAULTS_PREFIX
        if version == 2:
            prefix = YEARN_VAULTS_V2_PREFIX
        cursor = self.conn.cursor()
        cursor.execute(f'DELETE FROM yearn_vaults_events WHERE version={version};')
        cursor.execute(f'DELETE FROM used_query_ranges WHERE name LIKE "{prefix}%";')
        self.update_last_write()
        return None

    def delete_loopring_data(self) -> None:
        """Delete all loopring related data"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM multisettings WHERE name LIKE "loopring_%";')
        self.update_last_write()

    def get_used_query_range(self, name: str) -> Optional[Tuple[Timestamp, Timestamp]]:
        """Get the last start/end timestamp range that has been queried for name

        Currently possible names are:
        - {exchange_location_name}_trades_{exchange_name}
        - {exchange_location_name}_margins_{exchange_name}
        - {exchange_location_name}_asset_movements_{exchange_name}
        - {exchange_location_name}_ledger_actions_{exchange_name}
        - {location}_history_events_{optional_label}
        - aave_events_{address}
        - yearn_vaults_events_{address}
        - yearn_vaults_v2_events_{address}
        """
        cursor = self.conn.cursor()
        query = cursor.execute(
            f'SELECT start_ts, end_ts from used_query_ranges WHERE name="{name}";',
        )
        query = query.fetchall()
        if len(query) == 0 or query[0][0] is None:
            return None

        return Timestamp(int(query[0][0])), Timestamp(int(query[0][1]))

    def delete_used_query_range_for_exchange(self, location: Location) -> None:
        """Delete the query ranges for the given exchange name"""
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{str(location)}\\_%', '\\'),
        )
        self.update_last_write()

    def purge_exchange_data(self, location: Location) -> None:
        self.delete_used_query_range_for_exchange(location)
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM trades WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        cursor.execute(
            'DELETE FROM asset_movements WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        cursor.execute(
            'DELETE FROM ledger_actions WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        cursor.execute(
            'DELETE FROM asset_movements WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        cursor.execute(
            'DELETE FROM history_events WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        self.update_last_write()

    def update_used_query_range(self, name: str, start_ts: Timestamp, end_ts: Timestamp) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
            (name, str(start_ts), str(end_ts)),
        )
        self.update_last_write()

    def update_used_block_query_range(self, name: str, from_block: int, to_block: int) -> None:
        self.update_used_query_range(name, from_block, to_block)  # type: ignore

    def get_last_balance_save_time(self) -> Timestamp:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT MAX(time) from timed_location_data',
        )
        query = query.fetchall()
        if len(query) == 0 or query[0][0] is None:
            return Timestamp(0)

        return Timestamp(int(query[0][0]))

    def add_multiple_location_data(self, location_data: List[LocationData]) -> None:
        """Execute addition of multiple location data in the DB"""
        cursor = self.conn.cursor()
        for entry in location_data:
            try:
                cursor.execute(
                    'INSERT INTO timed_location_data('
                    '    time, location, usd_value) '
                    ' VALUES(?, ?, ?)',
                    (entry.time, entry.location, entry.usd_value),
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add a timed_location_data for '
                    f'{str(Location.deserialize_from_db(entry.location))} at'
                    f' already existing timestamp {entry.time}. Skipping.',
                )
                continue
        self.update_last_write()

    def add_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> None:
        # Insert the blockchain account addresses and labels to the DB
        tuples = [(
            blockchain.value,
            entry.address,
            entry.label,
        ) for entry in account_data]
        cursor = self.conn.cursor()
        try:
            cursor.executemany(
                'INSERT INTO blockchain_accounts(blockchain, account, label) VALUES (?, ?, ?)',
                tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Blockchain account/s {[x.address for x in account_data]} already exist',
            ) from e

        insert_tag_mappings(cursor=cursor, data=account_data, object_reference_keys=['address'])

        self.update_last_write()

    def edit_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> None:
        """Edit the given blockchain accounts

        At this point in the calling chain we should already know that:
        - All tags exist in the DB
        - All accounts exist in the DB
        """
        cursor = self.conn.cursor()
        # Delete the current tag mappings for all affected accounts
        cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', [(x.address,) for x in account_data],
        )

        # Update the blockchain account labels in the DB
        tuples = [(
            entry.label,
            entry.address,
            blockchain.value,
        ) for entry in account_data]
        cursor.executemany(
            'UPDATE blockchain_accounts SET label=? WHERE account=? AND blockchain=?;', tuples,
        )
        if cursor.rowcount != len(account_data):
            msg = (
                f'When updating blockchain accounts {len(account_data)} entries should '
                f'have been edited but only {cursor.rowcount} were. Should not happen.'
            )
            log.error(msg)
            raise AssertionError(msg)
        insert_tag_mappings(cursor=cursor, data=account_data, object_reference_keys=['address'])

        self.update_last_write()

    def remove_blockchain_accounts(
            self,
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes the given blockchain accounts from the DB

        May raise:
        - InputError if any of the given accounts to delete did not exist
        """
        tuples = [(blockchain.value, x) for x in accounts]
        account_tuples = [(x,) for x in accounts]

        cursor = self.conn.cursor()
        cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', account_tuples,
        )
        cursor.executemany(
            'DELETE FROM blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', tuples,
        )
        affected_rows = cursor.rowcount
        if affected_rows != len(accounts):
            self.conn.rollback()
            raise InputError(
                f'Tried to remove {len(accounts) - affected_rows} '
                f'{blockchain.value} accounts that do not exist',
            )

        # Also remove all ethereum address details saved in the DB
        if blockchain == SupportedBlockchain.ETHEREUM:
            for address in accounts:
                self.delete_data_for_ethereum_address(address)  # type: ignore

        self.update_last_write()

    def _get_address_details_if_time(
            self,
            address: ChecksumEthAddress,
            current_time: Timestamp,
    ) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT tokens_list, time FROM ethereum_accounts_details WHERE account = ?',
            (address,),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None  # no saved entry
        if current_time - result[0][1] > 86400:
            return None  # saved entry is outdated

        try:
            json_ret = json.loads(result[0][0])
        except json.decoder.JSONDecodeError as e:
            # This should never happen
            self.msg_aggregator.add_warning(
                f'Found undecodeable json {result[0][0]} in the DB for {address}.'
                f'Error: {str(e)}',
            )
            return None

        if not isinstance(json_ret, dict):
            # This can happen if the DB is old and still has only a list of saved tokens
            return None  # In that case just consider it outdated

        return json_ret

    def get_tokens_for_address_if_time(
            self,
            address: ChecksumEthAddress,
            current_time: Timestamp,
    ) -> Optional[List[EthereumToken]]:
        """Gets the detected tokens for the given address if the given current time
        is recent enough.

        If not, or if there is no saved entry, return None
        """
        json_ret = self._get_address_details_if_time(address, current_time)
        if json_ret is None:
            return None
        tokens_list = json_ret.get('tokens', None)
        if tokens_list is None:
            return None

        if not isinstance(tokens_list, list):
            # This should never happen
            self.msg_aggregator.add_warning(
                f'Found non-list tokens_list {json_ret} in the DB for {address}.',
            )
            return None

        returned_list = []
        for x in tokens_list:
            try:
                token = EthereumToken.from_identifier(x)
            except (DeserializationError, UnknownAsset):
                token = None
            if token is None:
                self.msg_aggregator.add_warning(
                    f'Could not deserialize {x} as a token when reading latest '
                    f'tokens list of {address}',
                )
                continue

            returned_list.append(token)

        return returned_list

    def _get_address_details_json(self, address: ChecksumEthAddress) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT tokens_list, time FROM ethereum_accounts_details WHERE account = ?',
            (address,),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None  # no saved entry

        try:
            json_ret = json.loads(result[0][0])
        except json.decoder.JSONDecodeError as e:
            # This should never happen
            self.msg_aggregator.add_warning(
                f'Found undecodeable json {result[0][0]} in the DB for {address}.'
                f'Error: {str(e)}',
            )
            return None

        return json_ret

    def save_tokens_for_address(
            self,
            address: ChecksumEthAddress,
            tokens: List[EthereumToken],
    ) -> None:
        """Saves detected tokens for an address"""
        old_details = self._get_address_details_json(address)
        new_details = {}
        if old_details and 'univ2_lp_tokens' in old_details:
            new_details['univ2_lp_tokens'] = old_details['univ2_lp_tokens']
        new_details['tokens'] = [x.identifier for x in tokens]
        now = ts_now()
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO ethereum_accounts_details '
            '(account, tokens_list, time) VALUES (?, ?, ?)',
            (address, json.dumps(new_details), now),
        )
        self.update_last_write()

    def get_blockchain_accounts(self) -> BlockchainAccounts:
        """Returns a Blockchain accounts instance containing all blockchain account addresses"""
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts;',
        )
        query = query.fetchall()

        eth_list = []
        btc_list = []
        ksm_list = []
        dot_list = []
        avax_list = []

        supported_blockchains = {blockchain.value for blockchain in SupportedBlockchain}
        for entry in query:
            if entry[0] not in supported_blockchains:
                log.warning(f'Unknown blockchain {entry[0]} found in DB. Ignoring...')
                continue

            if not is_valid_db_blockchain_account(blockchain=entry[0], account=entry[1]):
                self.msg_aggregator.add_warning(
                    f'Invalid {entry[0]} account in DB: {entry[1]}. '
                    f'This should not happen unless the DB was manually modified. '
                    f'Skipping entry. This needs to be fixed manually. If you '
                    f'can not do that alone ask for help in the issue tracker',
                )
                continue

            if entry[0] == SupportedBlockchain.BITCOIN.value:
                btc_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.ETHEREUM.value:
                eth_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.KUSAMA.value:
                ksm_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.AVALANCHE.value:
                avax_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.POLKADOT.value:
                dot_list.append(entry[1])

        return BlockchainAccounts(eth=eth_list, btc=btc_list, ksm=ksm_list, dot=dot_list, avax=avax_list)  # noqa: E501

    def get_blockchain_account_data(
            self,
            blockchain: SupportedBlockchain,
    ) -> List[BlockchainAccountData]:
        """Returns account data for a particular blockchain.

        Each account entry contains address and potentially label and tags
        """
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT A.account, A.label, group_concat(B.tag_name,",") '
            'FROM blockchain_accounts AS A '
            'LEFT OUTER JOIN tag_mappings AS B ON B.object_reference = A.account '
            'WHERE A.blockchain=? GROUP BY account;',
            (blockchain.value,),
        )

        data = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[2])
            data.append(BlockchainAccountData(
                address=entry[0],
                label=entry[1],
                tags=tags,
            ))

        return data

    def get_manually_tracked_balances(
        self,
        balance_type: Optional[BalanceType] = BalanceType.ASSET,
    ) -> List[ManuallyTrackedBalance]:
        """Returns the manually tracked balances from the DB"""
        cursor = self.conn.cursor()
        query_balance_type = ''
        if balance_type is not None:
            query_balance_type = f'WHERE A.category="{balance_type.serialize_for_db()}"'
        query = cursor.execute(
            f'SELECT A.asset, A.label, A.amount, A.location, group_concat(B.tag_name,","), '
            f'A.category FROM manually_tracked_balances as A '
            f'LEFT OUTER JOIN tag_mappings as B on B.object_reference = A.label '
            f'{query_balance_type} GROUP BY label;',
        )

        data = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[4])
            try:
                balance_type = BalanceType.deserialize_from_db(entry[5])
                data.append(ManuallyTrackedBalance(
                    asset=Asset(entry[0]),
                    label=entry[1],
                    amount=FVal(entry[2]),
                    location=Location.deserialize_from_db(entry[3]),
                    tags=tags,
                    balance_type=balance_type,
                ))
            except (DeserializationError, UnknownAsset, UnsupportedAsset, ValueError) as e:
                # ValueError would be due to FVal failing
                self.msg_aggregator.add_warning(
                    f'Unexpected data in a ManuallyTrackedBalance entry in the DB: {str(e)}',
                )

        return data

    def add_manually_tracked_balances(self, data: List[ManuallyTrackedBalance]) -> None:
        """Adds manually tracked balances in the DB

        May raise:
        - InputError if one of the given balance entries already exist in the DB
        """
        # Insert the manually tracked balances in the DB
        tuples = [(
            entry.asset.identifier,
            entry.label,
            str(entry.amount),
            entry.location.serialize_for_db(),
            entry.balance_type.serialize_for_db(),
        ) for entry in data]
        cursor = self.conn.cursor()
        try:
            cursor.executemany(
                'INSERT INTO manually_tracked_balances(asset, label, amount, location, category) '
                'VALUES (?, ?, ?, ?, ?)', tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'One of the manually tracked balance entries already exists in the DB. {str(e)}',
            ) from e
        insert_tag_mappings(cursor=cursor, data=data, object_reference_keys=['label'])

        # make sure assets are included in the global db user owned assets
        GlobalDBHandler().add_user_owned_assets([x.asset for x in data])

        self.update_last_write()

    def edit_manually_tracked_balances(self, data: List[ManuallyTrackedBalance]) -> None:
        """Edits manually tracked balances

        Edits the manually tracked balances for each of the given balance labels.

        At this point in the calling chain we should already know that:
        - All tags exist in the DB

        May raise:
        - InputError if any of the manually tracked balance labels to edit do not
        exist in the DB
        """
        cursor = self.conn.cursor()
        # Delete the current tag mappings for all affected balance entries
        cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', [(x.label,) for x in data],
        )

        # Update the manually tracked balance entries in the DB
        tuples = [(
            entry.asset.identifier,
            str(entry.amount),
            entry.location.serialize_for_db(),
            BalanceType.serialize_for_db(entry.balance_type),
            entry.label,
        ) for entry in data]

        cursor.executemany(
            'UPDATE manually_tracked_balances SET asset=?, amount=?, location=?, category=?'
            'WHERE label=?;', tuples,
        )
        if cursor.rowcount != len(data):
            msg = 'Tried to edit manually tracked balance entry that did not exist in the DB'
            raise InputError(msg)
        insert_tag_mappings(cursor=cursor, data=data, object_reference_keys=['label'])

        self.update_last_write()

    def remove_manually_tracked_balances(self, labels: List[str]) -> None:
        """
        Removes manually tracked balances for the given labels

        May raise:
        - InputError if any of the given manually tracked balance labels
        to delete did not exist
        """
        cursor = self.conn.cursor()
        tuples = [(x,) for x in labels]
        cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', tuples,
        )
        cursor.executemany(
            'DELETE FROM manually_tracked_balances WHERE label = ?;', tuples,
        )
        affected_rows = cursor.rowcount
        if affected_rows != len(labels):
            self.conn.rollback()
            raise InputError(
                f'Tried to remove {len(labels) - affected_rows} '
                f'manually tracked balance labels that do not exist',
            )

        self.update_last_write()

    def remove(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS timed_balances')
        cursor.execute('DROP TABLE IF EXISTS timed_location_data')
        cursor.execute('DROP TABLE IF EXISTS timed_unique_data')
        self.update_last_write()

    def save_balances_data(self, data: Dict[str, Any], timestamp: Timestamp) -> None:
        """The keys of the data dictionary can be any kind of asset plus 'location'
        and 'net_usd'. This gives us the balance data per assets, the balance data
        per location and finally the total balance

        The balances are saved in the DB at the given timestamp
        """
        balances = []
        locations = []

        for key, val in data['assets'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {str(key)}'
            assert isinstance(key, Asset), msg
            balances.append(DBAssetBalance(
                category=BalanceType.ASSET,
                time=timestamp,
                asset=key,
                amount=str(val['amount']),
                usd_value=str(val['usd_value']),
            ))

        for key, val in data['liabilities'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {str(key)}'
            assert isinstance(key, Asset), msg
            balances.append(DBAssetBalance(
                category=BalanceType.LIABILITY,
                time=timestamp,
                asset=key,
                amount=str(val['amount']),
                usd_value=str(val['usd_value']),
            ))

        for key2, val2 in data['location'].items():
            # Here we know val2 is just a Dict since the key to data is 'location'
            val2 = cast(Dict, val2)
            location = Location.deserialize(key2).serialize_for_db()
            locations.append(LocationData(
                time=timestamp, location=location, usd_value=str(val2['usd_value']),
            ))
        locations.append(LocationData(
            time=timestamp,
            location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
            usd_value=str(data['net_usd']),
        ))

        self.add_multiple_balances(balances)
        self.add_multiple_location_data(locations)

    def add_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str] = None,
            kraken_account_type: Optional[KrakenAccountType] = None,
            binance_markets: Optional[List[str]] = None,
            ftx_subaccount_name: Optional[str] = None,
    ) -> None:
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {str(location)}')

        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO user_credentials '
            '(name, location, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?, ?)',
            (name, location.serialize_for_db(), api_key, api_secret.decode(), passphrase),
        )

        if location == Location.KRAKEN and kraken_account_type is not None:
            cursor.execute(
                'INSERT INTO user_credentials_mappings '
                '(credential_name, credential_location, setting_name, setting_value) '
                'VALUES (?, ?, ?, ?)',
                (name, location.serialize_for_db(), 'kraken_account_type', kraken_account_type.serialize()),  # noqa: E501
            )

        if location in (Location.BINANCE, Location.BINANCEUS) and binance_markets is not None:
            self.set_binance_pairs(name, binance_markets, location)

        if location == Location.FTX and ftx_subaccount_name is not None:
            self.set_ftx_subaccount(name, ftx_subaccount_name)

        self.update_last_write()

    def edit_exchange(
            self,
            name: str,
            location: Location,
            new_name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            binance_markets: Optional[List[str]],
            ftx_subaccount_name: Optional[str],
            should_commit: bool = False,
    ) -> None:
        """May raise InputError if something is wrong with editing the DB"""
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {str(location)}')

        cursor = self.conn.cursor()
        if any(x is not None for x in (new_name, passphrase, api_key, api_secret)):
            querystr = 'UPDATE user_credentials SET '
            bindings = []
            if new_name is not None:
                querystr += 'name=?,'
                bindings.append(new_name)
            if passphrase is not None:
                querystr += 'passphrase=?,'
                bindings.append(passphrase)
            if api_key is not None:
                querystr += 'api_key=?,'
                bindings.append(api_key)
            if api_secret is not None:
                querystr += 'api_secret=?,'
                bindings.append(api_secret.decode())

            if querystr[-1] == ',':
                querystr = querystr[:-1]

            querystr += ' WHERE name=? AND location=?;'
            bindings.extend([name, location.serialize_for_db()])

            try:
                cursor.execute(querystr, bindings)
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials due to {str(e)}') from e

        if location == Location.KRAKEN and kraken_account_type is not None:
            try:
                cursor.execute(
                    'INSERT OR REPLACE INTO user_credentials_mappings '
                    '(credential_name, credential_location, setting_name, setting_value) '
                    'VALUES (?, ?, ?, ?)',
                    (
                        new_name if new_name is not None else name,
                        location.serialize_for_db(),
                        'kraken_account_type',
                        kraken_account_type.serialize(),
                    ),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                self.conn.rollback()
                raise InputError(f'Could not update DB user_credentials_mappings due to {str(e)}') from e  # noqa: E501

        location_is_binance = location in (Location.BINANCE, Location.BINANCEUS)
        if location_is_binance and binance_markets is not None:
            try:
                exchange_name = new_name if new_name is not None else name
                self.set_binance_pairs(exchange_name, binance_markets, location)
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                self.conn.rollback()
                raise InputError(f'Could not update DB user_credentials_mappings due to {str(e)}') from e  # noqa: E501
        if location == Location.FTX and ftx_subaccount_name is not None:
            try:
                exchange_name = new_name if new_name is not None else name
                self.set_ftx_subaccount(exchange_name, ftx_subaccount_name)
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                self.conn.rollback()
                raise InputError(f'Could not update DB user_credentials_mappings due to {str(e)}') from e  # noqa: E501

        if new_name is not None:
            exchange_re = re.compile(r'(.*?)_(trades|margins|asset_movements|ledger_actions).*')
            used_ranges_query = f'SELECT * from used_query_ranges WHERE name LIKE "{str(location)}_%_{name}"'  # noqa: E501
            used_ranges = cursor.execute(used_ranges_query)
            entry_types = set()
            for used_range in used_ranges:
                range_name = used_range[0]
                match = exchange_re.search(range_name)
                if match is None:
                    continue
                entry_types.add(match.group(2))
            cursor.executemany(
                'UPDATE used_query_ranges SET name=? WHERE name=?',
                [
                    (f'{str(location)}_{entry_type}_{new_name}', f'{str(location)}_{entry_type}_{name}')  # noqa: E501
                    for entry_type in entry_types
                ],
            )

        if should_commit is True:
            self.update_last_write()

    def remove_exchange(self, name: str, location: Location) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM user_credentials WHERE name=? AND location=?',
            (name, location.serialize_for_db()),
        )
        self.update_last_write()

    def get_exchange_credentials(
            self,
            location: Location = None,
            name: str = None,
    ) -> Dict[Location, List[ExchangeApiCredentials]]:
        """Gets all exchange credentials

        If an exchange name and location are passed the credentials are filtered further
        """
        cursor = self.conn.cursor()
        bindings = ()
        querystr = 'SELECT name, location, api_key, api_secret, passphrase FROM user_credentials'
        if name is not None and location is not None:
            querystr += ' WHERE name=? and location=?'
            bindings = (name, location.serialize_for_db())  # type: ignore
        querystr += ';'
        result = cursor.execute(querystr, bindings)
        credentials = defaultdict(list)
        for entry in result:
            if entry[0] == 'rotkehlchen':
                continue

            passphrase = None if entry[4] is None else entry[4]
            location = Location.deserialize_from_db(entry[1])
            credentials[location].append(ExchangeApiCredentials(
                name=entry[0],
                location=location,
                api_key=ApiKey(entry[2]),
                api_secret=ApiSecret(str.encode(entry[3])),
                passphrase=passphrase,
            ))

        return credentials

    def get_exchange_credentials_extras(self, name: str, location: Location) -> Dict[str, Any]:
        """Returns any extra settings for a particular exchange key credentials"""
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT setting_name, setting_value FROM user_credentials_mappings '
            'WHERE credential_name=? AND credential_location=?',
            (name, location.serialize_for_db()),
        )
        extras = {}
        for entry in result:
            if entry[0] != 'kraken_account_type':
                log.error(
                    f'Unknown credential setting {entry[0]} found in the DB. Skipping.',
                )
                continue

            try:
                extras['kraken_account_type'] = KrakenAccountType.deserialize(entry[1])
            except DeserializationError as e:
                log.error(f'Couldnt deserialize kraken account type from DB. {str(e)}')
                continue

        return extras

    def set_binance_pairs(self, name: str, pairs: List[str], location: Location) -> None:
        cursor = self.conn.cursor()
        data = json.dumps(pairs)
        cursor.execute(
            'INSERT OR REPLACE INTO user_credentials_mappings '
            '(credential_name, credential_location, setting_name, setting_value) '
            'VALUES (?, ?, ?, ?)',
            (
                name,
                location.serialize_for_db(),
                BINANCE_MARKETS_KEY,
                data,
            ),
        )
        self.update_last_write()

    def get_binance_pairs(self, name: str, location: Location) -> List[str]:
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT setting_value FROM user_credentials_mappings WHERE '
            'credential_name=? AND credential_location=? AND setting_name=?',
            (name, location.serialize_for_db(), BINANCE_MARKETS_KEY),  # noqa: E501
        )
        data = result.fetchone()
        if data and data[0] != '':
            return json.loads(data[0])
        return []

    def set_ftx_subaccount(self, ftx_name: str, subaccount_name: str) -> None:
        """This function may raise sqlcipher.DatabaseError"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO user_credentials_mappings '
            '(credential_name, credential_location, setting_name, setting_value) '
            'VALUES (?, ?, ?, ?)',
            (
                ftx_name,
                Location.FTX.serialize_for_db(),  # pylint: disable=no-member
                FTX_SUBACCOUNT_DB_SETTING,
                subaccount_name,
            ),
        )

    def get_ftx_subaccount(self, ftx_name: str) -> Optional[str]:
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT setting_value FROM user_credentials_mappings WHERE '
            'credential_name=? AND credential_location=? AND setting_name=?',
            (ftx_name, Location.FTX.serialize_for_db(), FTX_SUBACCOUNT_DB_SETTING),  # noqa: E501 pylint: disable=no-member
        )
        data = result.fetchone()
        if data and data[0].strip() != '':
            return data[0]
        return None

    def write_tuples(
            self,
            tuple_type: DBTupleType,
            query: str,
            tuples: List[Tuple[Any, ...]],
    ) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.executemany(query, tuples)
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            # That means that one of the tuples hit a constraint, most probably
            # already existing in the DB, in which case we resort to writing them
            # one by one to only reject the duplicates
            for entry in tuples:
                try:
                    cursor.execute(query, entry)
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    if tuple_type == 'ethereum_transaction':
                        # if we reach here it means the transaction is already in the DB
                        # But this can't be avoided with the way we query etherscan
                        # right now since we don't query transactions in a specific
                        # time range, so duplicate addition attempts can happen.
                        # Also if we have transactions of one account sending to the
                        # other and both accounts are being tracked.
                        string_repr = db_tuple_to_str(entry, tuple_type)
                        log.debug(
                            f'Did not add "{string_repr}" to the DB due to "{str(e)}".'
                            f'Either it already exists or some constraint was hit.',
                        )
                        continue

                    string_repr = db_tuple_to_str(entry, tuple_type)
                    log.warning(
                        f'Did not add "{string_repr}" to the DB due to "{str(e)}".'
                        f'It either already exists or some other constraint was hit.',
                    )
                except sqlcipher.InterfaceError:  # pylint: disable=no-member
                    log.critical(f'Interface error with tuple: {entry}')

        except OverflowError:
            self.msg_aggregator.add_error(
                f'Failed to add "{tuple_type}" to the DB with overflow error. '
                f'Check the logs for more details',
            )
            log.error(
                f'Overflow error while trying to add "{tuple_type}" tuples to the'
                f' DB. Tuples: {tuples} with query: {query}',
            )

        self.update_last_write()

    def add_margin_positions(self, margin_positions: List[MarginPosition]) -> None:
        margin_tuples: List[Tuple[Any, ...]] = []
        for margin in margin_positions:
            open_time = 0 if margin.open_time is None else margin.open_time
            margin_tuples.append((
                margin.identifier,
                margin.location.serialize_for_db(),
                open_time,
                margin.close_time,
                str(margin.profit_loss),
                margin.pl_currency.identifier,
                str(margin.fee),
                margin.fee_currency.identifier,
                margin.link,
                margin.notes,
            ))

        query = """
            INSERT INTO margin_positions(
              id,
              location,
              open_time,
              close_time,
              profit_loss,
              pl_currency,
              fee,
              fee_currency,
              link,
              notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.write_tuples(tuple_type='margin_position', query=query, tuples=margin_tuples)

    def get_margin_positions(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[Location] = None,
    ) -> List[MarginPosition]:
        """Returns a list of margin positions optionally filtered by time and location

        The returned list is ordered from oldest to newest
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM margin_positions '
        if location is not None:
            query += f'WHERE location="{location.serialize_for_db()}" '
        query, bindings = form_query_to_filter_timestamps(query, 'close_time', from_ts, to_ts)
        results = cursor.execute(query, bindings)

        margin_positions = []
        for result in results:
            try:
                margin = MarginPosition.deserialize_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing margin position from the DB. '
                    f'Skipping it. Error was: {str(e)}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing margin position from the DB. Skipping it. '
                    f'Unknown asset {e.asset_name} found',
                )
                continue
            margin_positions.append(margin)

        return margin_positions

    def add_asset_movements(self, asset_movements: List[AssetMovement]) -> None:
        movement_tuples: List[Tuple[Any, ...]] = []
        for movement in asset_movements:
            movement_tuples.append((
                movement.identifier,
                movement.location.serialize_for_db(),
                movement.category.serialize_for_db(),
                movement.timestamp,
                movement.asset.identifier,
                str(movement.amount),
                movement.fee_asset.identifier,
                str(movement.fee),
                movement.link,
                movement.address,
                movement.transaction_id,
            ))

        query = """
            INSERT INTO asset_movements(
              id,
              location,
              category,
              time,
              asset,
              amount,
              fee_asset,
              fee,
              link,
              address,
              transaction_id
)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.write_tuples(tuple_type='asset_movement', query=query, tuples=movement_tuples)

    def get_asset_movements_and_limit_info(
            self,
            filter_query: AssetMovementsFilterQuery,
            has_premium: bool,
    ) -> Tuple[List[AssetMovement], int]:
        """Gets all asset movements for the query from the DB

        Also returns how many are the total found for the filter
        """
        movements = self.get_asset_movements(filter_query=filter_query, has_premium=has_premium)
        cursor = self.conn.cursor()
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from asset_movements ' + query
        total_found_result = cursor.execute(query, bindings)
        return movements, total_found_result.fetchone()[0]

    def get_asset_movements(
            self,
            filter_query: AssetMovementsFilterQuery,
            has_premium: bool,
    ) -> List[AssetMovement]:
        """Returns a list of asset movements optionally filtered by the given filter.

        Returned list is ordered according to the passed filter query
        """
        cursor = self.conn.cursor()
        query, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT * from asset_movements ' + query
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT * FROM (SELECT * from asset_movements ORDER BY time DESC LIMIT ?) ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_ASSET_MOVEMENTS_LIMIT] + bindings)

        asset_movements = []
        for result in results:
            try:
                movement = AssetMovement.deserialize_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing asset movement from the DB. '
                    f'Skipping it. Error was: {str(e)}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing asset movement from the DB. Skipping it. '
                    f'Unknown asset {e.asset_name} found',
                )
                continue
            asset_movements.append(movement)

        return asset_movements

    def get_entries_count(
            self,
            entries_table: Literal[
                'asset_movements',
                'trades',
                'ethereum_transactions',
                'amm_swaps',
                'combined_trades_view',
                'ledger_actions',
                'eth2_daily_staking_details',
            ],
            op: Literal['OR', 'AND'] = 'OR',
            **kwargs: Any,
    ) -> int:
        """Returns how many of a certain type of entry are saved in the DB"""
        cursor = self.conn.cursor()
        cursorstr = f'SELECT COUNT(*) from {entries_table}'
        if len(kwargs) != 0:
            cursorstr += ' WHERE'
        op.join([f' {arg} = "{val}" ' for arg, val in kwargs.items()])
        cursorstr += ';'
        query = cursor.execute(cursorstr)
        return query.fetchone()[0]

    def delete_data_for_ethereum_address(self, address: ChecksumEthAddress) -> None:
        """Deletes all ethereum related data from the DB for a single ethereum address"""
        other_eth_accounts = self.get_blockchain_accounts().eth
        if address in other_eth_accounts:
            other_eth_accounts.remove(address)

        cursor = self.conn.cursor()
        cursor.execute(f'DELETE FROM used_query_ranges WHERE name="ethtxs_{address}";')
        cursor.execute(f'DELETE FROM used_query_ranges WHERE name="aave_events_{address}";')
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name="{ADEX_EVENTS_PREFIX}_{address}";',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name="{BALANCER_EVENTS_PREFIX}_{address}";',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name="{BALANCER_TRADES_PREFIX}_{address}";',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name="{UNISWAP_EVENTS_PREFIX}_{address}";',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name="{UNISWAP_TRADES_PREFIX}_{address}";',
        )
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name="{ETH2_DEPOSITS_PREFIX}_{address}";',
        )
        cursor.execute('DELETE FROM ethereum_accounts_details WHERE account = ?', (address,))
        cursor.execute('DELETE FROM aave_events WHERE address = ?', (address,))
        cursor.execute('DELETE FROM adex_events WHERE address = ?', (address,))
        cursor.execute('DELETE FROM balancer_events WHERE address=?;', (address,))
        cursor.execute('DELETE FROM amm_events WHERE address=?;', (address,))
        cursor.execute(
            'DELETE FROM multisettings WHERE name LIKE "queried_address_%" AND value = ?',
            (address,),
        )
        loopring = DBLoopring(self)
        loopring.remove_accountid_mapping(address)

        # For transactions we need to delete all transactions where the address
        # appears in either from or to, BUT no other tracked address is in
        # from or to of the DB entry
        questionmarks = '?' * len(other_eth_accounts)
        # IN operator support in python sqlite is terrible :(
        # https://stackoverflow.com/questions/31473451/sqlite3-in-clause
        cursor.execute(
            f'DELETE FROM ethereum_transactions WHERE '
            f'from_address="{address}" AND to_address NOT IN ({",".join(questionmarks)});',
            other_eth_accounts,
        )
        cursor.execute(
            f'DELETE FROM ethereum_transactions WHERE '
            f'to_address="{address}" AND from_address NOT IN ({",".join(questionmarks)});',
            other_eth_accounts,
        )
        cursor.execute('DELETE FROM amm_swaps WHERE address=?;', (address,))
        cursor.execute('DELETE FROM eth2_deposits WHERE from_address=?;', (address,))

        self.update_last_write()

    def add_trades(self, trades: List[Trade]) -> None:
        trade_tuples: List[Tuple[Any, ...]] = []
        for trade in trades:
            trade_tuples.append((
                trade.identifier,
                trade.timestamp,
                trade.location.serialize_for_db(),
                trade.base_asset.identifier,
                trade.quote_asset.identifier,
                trade.trade_type.serialize_for_db(),
                str(trade.amount),
                str(trade.rate),
                str(trade.fee) if trade.fee else None,
                trade.fee_currency.identifier if trade.fee_currency else None,
                trade.link,
                trade.notes,
            ))

        query = """
            INSERT INTO trades(
              id,
              time,
              location,
              base_asset,
              quote_asset,
              type,
              amount,
              rate,
              fee,
              fee_currency,
              link,
              notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.write_tuples(tuple_type='trade', query=query, tuples=trade_tuples)

    def edit_trade(
            self,
            old_trade_id: str,
            trade: Trade,
    ) -> Tuple[bool, str]:
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE trades SET '
            '  id=?, '
            '  time=?,'
            '  location=?,'
            '  base_asset=?,'
            '  quote_asset=?,'
            '  type=?,'
            '  amount=?,'
            '  rate=?,'
            '  fee=?,'
            '  fee_currency=?,'
            '  link=?,'
            '  notes=? '
            'WHERE id=?',
            (
                trade.identifier,
                trade.timestamp,
                trade.location.serialize_for_db(),
                trade.base_asset.identifier,
                trade.quote_asset.identifier,
                trade.trade_type.serialize_for_db(),
                str(trade.amount),
                str(trade.rate),
                str(trade.fee) if trade.fee else None,
                trade.fee_currency.identifier if trade.fee_currency else None,
                trade.link,
                trade.notes,
                old_trade_id,
            ),
        )
        if cursor.rowcount == 0:
            return False, 'Tried to edit non existing trade id'

        self.update_last_write()
        return True, ''

    def get_trades_and_limit_info(
            self,
            filter_query: TradesFilterQuery,
            has_premium: bool,
    ) -> Tuple[List[Trade], int]:
        """Gets all trades for the query from the DB

        Also returns how many are the total found for the filter
        """
        trades = self.get_trades(filter_query=filter_query, has_premium=has_premium)
        table_name = 'combined_trades_view' if has_premium else 'trades'
        cursor = self.conn.cursor()
        query, bindings = filter_query.prepare(with_pagination=False)
        query = f'SELECT COUNT(*) from {table_name} ' + query
        total_found_result = cursor.execute(query, bindings)
        return trades, total_found_result.fetchone()[0]

    def get_trades(self, filter_query: TradesFilterQuery, has_premium: bool) -> List[Trade]:
        """Returns a list of trades optionally filtered by various filters.

        This will also take into account AMMSwaps and return them as trades via a view.

        The returned list is ordered according to the passed filter query"""
        cursor = self.conn.cursor()
        query, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT * from combined_trades_view ' + query
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT * FROM (SELECT * from trades ORDER BY time DESC LIMIT ?) ' + query  # noqa: E501
            results = cursor.execute(query, [FREE_TRADES_LIMIT] + bindings)

        trades = []
        for result in results:
            try:
                trade = Trade.deserialize_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing trade from the DB. Skipping trade. Error was: {str(e)}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing trade from the DB. Skipping trade. '
                    f'Unknown asset {e.asset_name} found',
                )
                continue
            trades.append(trade)

        return trades

    def delete_trade(self, trade_id: str) -> Tuple[bool, str]:
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM trades WHERE id=?', (trade_id,))
        if cursor.rowcount == 0:
            return False, 'Tried to delete non-existing trade'
        self.update_last_write()
        return True, ''

    def add_amm_swaps(self, swaps: List[AMMSwap]) -> None:
        swap_tuples: List[Tuple[Any, ...]] = []
        for swap in swaps:
            swap_tuples.append(swap.to_db_tuple())

        query = (
            """
            INSERT INTO amm_swaps (
                tx_hash,
                log_index,
                address,
                from_address,
                to_address,
                timestamp,
                location,
                token0_identifier,
                token1_identifier,
                amount0_in,
                amount1_in,
                amount0_out,
                amount1_out
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        self.write_tuples(tuple_type='amm_swap', query=query, tuples=swap_tuples)

    def get_amm_swaps(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[Location] = None,
            address: Optional[ChecksumEthAddress] = None,
    ) -> List[AMMSwap]:
        """Returns a list of AMM swaps optionally filtered by time, location
        and address
        """
        cursor = self.conn.cursor()
        query = 'SELECT * FROM amm_swaps '
        # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
        filters = []
        if location is not None:
            filters.append(f'location="{location.serialize_for_db()}" ')
        if address is not None:
            filters.append(f'address="{address}" ')

        if filters:
            query += 'WHERE '
            query += 'AND '.join(filters)

        query, bindings = form_query_to_filter_timestamps(query, 'timestamp', from_ts, to_ts)
        results = cursor.execute(query, bindings)

        swaps = []
        for result in results:
            try:
                swap = AMMSwap.deserialize_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing AMM swap from the DB. Skipping swap. '
                    f'Error was: {str(e)}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing AMM swap from the DB. Skipping swap. '
                    f'Unknown asset {e.asset_name} found',
                )
                continue
            swaps.append(swap)

        return swaps

    def set_rotkehlchen_premium(self, credentials: PremiumCredentials) -> None:
        """Save the rotki premium credentials in the DB"""
        cursor = self.conn.cursor()
        # We don't care about previous value so simple insert or replace should work
        cursor.execute(
            'INSERT OR REPLACE INTO user_credentials'
            '(name, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?)',
            ('rotkehlchen', credentials.serialize_key(), credentials.serialize_secret(), None),
        )
        self.conn.commit()
        # Do not update the last write here. If we are starting in a new machine
        # then this write is mandatory and to sync with data from server we need
        # an empty last write ts in that case
        # self.update_last_write()

    def del_rotkehlchen_premium(self) -> bool:
        """Delete the rotki premium credentials in the DB for the logged-in user"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                'DELETE FROM user_credentials WHERE name=?', ('rotkehlchen',),
            )
            self.update_last_write()
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            log.error(f'Could not delete rotki premium keys: {str(e)}')
            return False
        return True

    def get_rotkehlchen_premium(self) -> Optional[PremiumCredentials]:
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT api_key, api_secret FROM user_credentials where name="rotkehlchen";',
        )
        result = result.fetchall()
        if len(result) == 1:
            try:
                credentials = PremiumCredentials(
                    given_api_key=result[0][0],
                    given_api_secret=result[0][1],
                )
            except IncorrectApiKeyFormat:
                self.msg_aggregator.add_error(
                    'Incorrect rotki API Key/Secret format found in the DB. Skipping ...',
                )
                return None

            return credentials
        # else
        return None

    def get_netvalue_data(
        self,
        from_ts: Timestamp,
        include_nfts: bool = True,
    ) -> Tuple[List[str], List[str]]:
        """Get all entries of net value data from the DB"""
        cursor = self.conn.cursor()
        # Get the total location ("H") entries in ascending time
        query = cursor.execute(
            f'SELECT time, usd_value FROM timed_location_data '
            f'WHERE location="H" AND time >= {from_ts} ORDER BY time ASC;',
        )
        if not include_nfts:
            nft_cursor = self.conn.cursor()
            nft_balances = nft_cursor.execute(
                f'SELECT time, SUM(usd_value) FROM timed_balances WHERE time >= ? '
                f'AND currency LIKE "{NFT_DIRECTIVE}%" GROUP BY time',
                (from_ts,),
            )
            nft_values = {time: value for time, value in nft_balances}

        data = []
        times_int = []
        for entry in query:
            times_int.append(entry[0])
            if include_nfts:
                total = entry[1]
            else:
                total = str(FVal(entry[1]) - FVal(nft_values.get(entry[0], 0)))
            data.append(total)
        return times_int, data

    def query_timed_balances(
            self,
            asset: Asset,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            balance_type: Optional[BalanceType] = None,
    ) -> List[SingleDBAssetBalance]:
        """Query all balance entries for an asset within a range of timestamps

        Can optionally filter by balance type
        """
        if from_ts is None:
            from_ts = Timestamp(0)
        if to_ts is None:
            to_ts = ts_now()
        settings = self.get_settings()

        querystr = (
            f'SELECT time, amount, usd_value, category FROM timed_balances '
            f'WHERE time BETWEEN {from_ts} AND {to_ts} AND currency="{asset.identifier}"'
        )
        if balance_type is not None:
            querystr += f' AND category="{balance_type.serialize_for_db()}"'
        querystr += ' ORDER BY time ASC;'

        cursor = self.conn.cursor()
        results = cursor.execute(querystr)
        results = results.fetchall()
        balances = []
        results_length = len(results)
        for idx, result in enumerate(results):
            entry_time = result[0]
            category = BalanceType.deserialize_from_db(result[3])
            balances.append(
                SingleDBAssetBalance(
                    time=entry_time,
                    amount=result[1],
                    usd_value=result[2],
                    category=category,
                ),
            )
            if settings.ssf_0graph_multiplier == 0 or idx == results_length - 1:
                continue

            next_result_time = results[idx + 1][0]
            max_diff = settings.balance_save_frequency * HOUR_IN_SECONDS * settings.ssf_0graph_multiplier  # noqa: E501
            while next_result_time - entry_time > max_diff:
                entry_time = entry_time + settings.balance_save_frequency * HOUR_IN_SECONDS
                if entry_time >= next_result_time:
                    break

                balances.append(
                    SingleDBAssetBalance(
                        time=entry_time,
                        amount='0',
                        usd_value='0',
                        category=category,
                    ),
                )

        return balances

    def query_owned_assets(self) -> List[Asset]:
        """Query the DB for a list of all assets ever owned

        The assets are taken from:
        - Balance snapshots
        - Trades the user made
        - Manual balances
        """
        # TODO: Perhaps also add amm swaps here
        # but think on the performance. This is a synchronous api call so if
        # it starts taking too much time the calling logic needs to change
        cursor = self.conn.cursor()

        results = set()
        for table_entry in TABLES_WITH_ASSETS:
            table_name = table_entry[0]
            columns = table_entry[1:]
            columns_str = ", ".join(columns)
            bindings: Union[Tuple, Tuple[str]] = ()
            condition = ''
            if table_name in ('manually_tracked_balances', 'timed_balances'):
                bindings = (BalanceType.LIABILITY.serialize_for_db(),)
                condition = ' WHERE category!=?'

            try:
                query = cursor.execute(
                    f'SELECT DISTINCT {columns_str} FROM {table_name} {condition};',
                    bindings,
                )
            except sqlcipher.OperationalError as e:    # pylint: disable=no-member
                log.error(f'Could not fetch assets from table {table_name}. {str(e)}')
                continue

            for result in query:
                for _, asset_id in enumerate(result):
                    try:
                        if asset_id is not None:
                            results.add(Asset(asset_id))
                    except UnknownAsset:
                        self.msg_aggregator.add_warning(
                            f'Unknown/unsupported asset {asset_id} found in the database. '
                            f'If you believe this should be supported open an issue in github',
                        )
                        continue
                    except DeserializationError:
                        self.msg_aggregator.add_error(
                            f'Asset with non-string type {type(asset_id)} found in the '
                            f'database. Skipping it.',
                        )
                        continue

        return list(results)

    def update_owned_assets_in_globaldb(self) -> None:
        """Makes sure all owned assets of the user are in the Global DB"""
        assets = self.query_owned_assets()
        GlobalDBHandler().add_user_owned_assets(assets)

    def add_asset_identifiers(self, asset_identifiers: List[str]) -> None:
        """Adds an asset to the user db asset identifier table"""
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT OR IGNORE INTO assets(identifier) VALUES(?);',
            [(x,) for x in asset_identifiers],
        )
        self.update_last_write()

    def add_globaldb_assetids(self) -> None:
        """Makes sure that all the GlobalDB asset identifiers are mirrored in the user DB"""
        cursor = GlobalDBHandler()._conn.cursor()  # after succesfull update add all asset ids
        query = cursor.execute('SELECT identifier from assets;')
        self.add_asset_identifiers([x[0] for x in query])

    def delete_asset_identifier(self, asset_id: str) -> None:
        """Deletes an asset identifier from the user db asset identifier table

        May raise:
        - InputError if a foreign key error is encountered during deletion
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'DELETE FROM assets WHERE identifier=?;',
                (asset_id,),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Failed to delete asset with id {asset_id} from the DB since '
                f'the user owns it now or did some time in the past',
            ) from e

        self.update_last_write()

    def replace_asset_identifier(self, source_identifier: str, target_asset: Asset) -> None:
        """Replaces a given source identifier either both in the global or the local
        user DB with another given asset.

        May raise:
        - UnknownAsset if the source_identifier can be found nowhere
        - InputError if it's not possible to perform the replacement for some reason
        """
        globaldb = GlobalDBHandler()
        globaldb_data = globaldb.get_asset_data(identifier=source_identifier, form_with_incomplete_data=True)  # noqa: E501

        cursor = self.conn.cursor()
        userdb_query = cursor.execute(
            'SELECT COUNT(*) FROM assets WHERE identifier=?;', (source_identifier,),
        ).fetchone()[0]

        if userdb_query == 0 and globaldb_data is None:
            raise UnknownAsset(source_identifier)

        if globaldb_data is not None:
            globaldb.delete_asset_by_identifer(source_identifier, globaldb_data.asset_type)

        if userdb_query != 0:
            # the tricky part here is that we need to disable foreign keys for this
            # approach and disabling foreign keys needs a commit. So rollback is impossible.
            # But there is no way this can fail. (famous last words)
            cursor.executescript('PRAGMA foreign_keys = OFF;')
            cursor.execute(
                'DELETE from assets WHERE identifier=?;',
                (target_asset.identifier,),
            )
            cursor.executescript('PRAGMA foreign_keys = ON;')
            cursor.execute(
                'UPDATE assets SET identifier=? WHERE identifier=?;',
                (target_asset.identifier, source_identifier),
            )
            self.update_last_write()

    def get_latest_location_value_distribution(self) -> List[LocationData]:
        """Gets the latest location data

        Returns a list of `LocationData` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all locations
        """
        cursor = self.conn.cursor()
        results = cursor.execute(
            'SELECT time, location, usd_value FROM timed_location_data WHERE '
            'time=(SELECT MAX(time) FROM timed_location_data) AND usd_value!=0;',
        )
        results = results.fetchall()

        locations = []
        for result in results:
            locations.append(
                LocationData(
                    time=result[0],
                    location=result[1],
                    usd_value=result[2],
                ),
            )

        return locations

    def get_latest_asset_value_distribution(self) -> List[DBAssetBalance]:
        """Gets the latest asset distribution data

        Returns a list of `DBAssetBalance` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all assets

        This will NOT include liabilities

        The list is sorted by usd value going from higher to lower
        """
        cursor = self.conn.cursor()
        results = cursor.execute(
            f'SELECT time, currency, amount, usd_value, category FROM timed_balances WHERE '  # pylint: disable=no-member  # noqa: E501
            f'time=(SELECT MAX(time) from timed_balances) AND '
            f'category="{BalanceType.ASSET.serialize_for_db()}" ORDER BY '
            f'CAST(usd_value AS REAL) DESC;',
        )
        results = results.fetchall()
        asset_balances = []
        for result in results:
            asset_balances.append(
                DBAssetBalance(
                    time=result[0],
                    asset=Asset(result[1]),
                    amount=result[2],
                    usd_value=result[3],
                    category=BalanceType.deserialize_from_db(result[4]),
                ),
            )

        return asset_balances

    def get_tags(self) -> Dict[str, Tag]:
        cursor = self.conn.cursor()
        results = cursor.execute(
            'SELECT name, description, background_color, foreground_color FROM tags;',
        )
        tags_mapping: Dict[str, Tag] = {}
        for result in results:
            name = result[0]
            description = result[1]

            if description is not None and not isinstance(description, str):
                self.msg_aggregator.add_warning(
                    f'Tag {name} with invalid description found in the DB. Skipping tag',
                )
                continue

            try:
                background_color = deserialize_hex_color_code(result[2])
                foreground_color = deserialize_hex_color_code(result[3])
            except DeserializationError as e:
                self.msg_aggregator.add_warning(
                    f'Tag {name} with invalid color code found in the DB. {str(e)}. Skipping tag',
                )
                continue

            tags_mapping[name] = Tag(
                name=name,
                description=description,
                background_color=background_color,
                foreground_color=foreground_color,
            )

        return tags_mapping

    def add_tag(
            self,
            name: str,
            description: Optional[str],
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> None:
        """Adds a new tag to the DB

        Raises:
        - TagConstraintError: If the tag with the given name already exists
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO tags'
                '(name, description, background_color, foreground_color) VALUES (?, ?, ?, ?)',
                (name, description, background_color, foreground_color),
            )
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            msg = str(e)
            if 'UNIQUE constraint failed: tags.name' in msg:
                raise TagConstraintError(
                    f'Tag with name {name} already exists. Tag name matching is case insensitive.',
                ) from e

            # else something really bad happened
            log.error('Unexpected DB error: {msg} while adding a tag')
            raise

        self.update_last_write()

    def edit_tag(
            self,
            name: str,
            description: Optional[str],
            background_color: Optional[HexColorCode],
            foreground_color: Optional[HexColorCode],
    ) -> None:
        """Edits a tag already existing in the DB

        Raises:
        - TagConstraintError: If the tag name to edit does not exist in the DB
        - InputError: If no field to edit was given.
        """
        query_values = []
        querystr = 'UPDATE tags SET '
        if description is not None:
            querystr += 'description = ?,'
            query_values.append(description)
        if background_color is not None:
            querystr += 'background_color = ?,'
            query_values.append(background_color)
        if foreground_color is not None:
            querystr += 'foreground_color = ?,'
            query_values.append(foreground_color)

        if len(query_values) == 0:
            raise InputError(f'No field was given to edit for tag "{name}"')

        querystr = querystr[:-1] + 'WHERE name = ?;'
        query_values.append(name)
        cursor = self.conn.cursor()
        cursor.execute(querystr, query_values)
        if cursor.rowcount < 1:
            raise TagConstraintError(
                f'Tried to edit tag with name "{name}" which does not exist',
            )
        self.update_last_write()

    def delete_tag(self, name: str) -> None:
        """Deletes a tag already existing in the DB

        Raises:
        - TagConstraintError: If the tag name to delete does not exist in the DB
        """
        cursor = self.conn.cursor()
        # Delete the tag mappings for all affected accounts
        cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'tag_name = ?;', (name,),
        )
        cursor.execute('DELETE from tags WHERE name = ?;', (name,))
        if cursor.rowcount < 1:
            raise TagConstraintError(
                f'Tried to delete tag with name "{name}" which does not exist',
            )
        self.update_last_write()

    def ensure_tags_exist(
            self,
            given_data: Union[
                List[BlockchainAccountData],
                List[ManuallyTrackedBalance],
                List[XpubData],
            ],
            action: Literal['adding', 'editing'],
            data_type: Literal['blockchain accounts', 'manually tracked balances', 'bitcoin xpub'],
    ) -> None:
        """Make sure that tags included in the data exist in the DB

        May Raise:
        - TagConstraintError if the tags don't exist in the DB
        """
        existing_tags = self.get_tags()
        # tag comparison is case-insensitive
        existing_tag_keys = [key.lower() for key in existing_tags]

        unknown_tags: Set[str] = set()
        for entry in given_data:
            if entry.tags is not None:
                unknown_tags.update(
                    # tag comparison is case-insensitive
                    {t.lower() for t in entry.tags}.difference(existing_tag_keys),
                )

        if len(unknown_tags) != 0:
            raise TagConstraintError(
                f'When {action} {data_type}, unknown tags '
                f'{", ".join(unknown_tags)} were found',
            )

    def add_bitcoin_xpub(self, xpub_data: XpubData) -> None:
        """Add the xpub to the DB

        May raise:
        - InputError if the xpub data already exist
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO xpubs(xpub, derivation_path, label) '
                'VALUES (?, ?, ?)',
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    xpub_data.label,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Xpub {xpub_data.xpub.xpub} with derivation path '
                f'{xpub_data.derivation_path} is already tracked',
            ) from e
        self.update_last_write()

    def delete_bitcoin_xpub(self, xpub_data: XpubData) -> None:
        """Deletes an xpub from the DB. Also deletes all derived addresses and mappings

        May raise:
        - InputError if the xpub does not exist in the DB
        """
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT COUNT(*) FROM xpubs WHERE xpub=? AND derivation_path IS ?;',
            (xpub_data.xpub.xpub, xpub_data.serialize_derivation_path_for_db()),
        )
        if query.fetchone()[0] == 0:
            derivation_str = (
                'no derivation path' if xpub_data.derivation_path is None else
                f'derivation path {xpub_data.derivation_path}'
            )
            raise InputError(
                f'Tried to remove non existing xpub {xpub_data.xpub.xpub} '
                f'with {derivation_str}',
            )

        # Delete the tag mappings for all derived addresses
        cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'object_reference IN ('
            'SELECT address from xpub_mappings WHERE xpub=? and derivation_path IS ?);',
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
            ),
        )
        # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None
        key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore
        cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
        # Delete any derived addresses
        cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=? AND account IN ('
            'SELECT address from xpub_mappings WHERE xpub=? and derivation_path IS ?);',
            (
                SupportedBlockchain.BITCOIN.value,
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
            ),
        )
        # And then finally delete the xpub itself
        cursor.execute(
            'DELETE FROM xpubs WHERE xpub=? AND derivation_path IS ?;',
            (xpub_data.xpub.xpub, xpub_data.serialize_derivation_path_for_db()),
        )

        self.update_last_write()

    def edit_bitcoin_xpub(self, xpub_data: XpubData) -> None:
        """Edit the xpub tags and label

        May raise:
        - InputError if the xpub data already exist
        """
        cursor = self.conn.cursor()
        try:
            key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore # noqa: E501
            # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None)
            cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
            insert_tag_mappings(
                # if we got tags add them to the xpub
                cursor=cursor,
                data=[xpub_data],
                object_reference_keys=['xpub.xpub', 'derivation_path'],
            )
            cursor.execute(
                'UPDATE xpubs SET label=? WHERE xpub=? AND derivation_path=?',
                (
                    xpub_data.label,
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'There was an error when updating Xpub {xpub_data.xpub.xpub} with '
                f'derivation path {xpub_data.derivation_path}',
            ) from e
        self.update_last_write()

    def get_bitcoin_xpub_data(self) -> List[XpubData]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT A.xpub, A.derivation_path, A.label, group_concat(B.tag_name,",") '
            'FROM xpubs as A LEFT OUTER JOIN tag_mappings AS B ON '
            'B.object_reference = A.xpub || A.derivation_path GROUP BY A.xpub || A.derivation_path;',  # noqa: E501
        )
        result = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[3])
            result.append(XpubData(
                xpub=HDKey.from_xpub(entry[0], path='m'),
                derivation_path=deserialize_derivation_path_for_db(entry[1]),
                label=entry[2],
                tags=tags,
            ))

        return result

    def get_last_consecutive_xpub_derived_indices(self, xpub_data: XpubData) -> Tuple[int, int]:
        """
        Get the last known receiving and change derived indices from the given
        xpub that are consecutive since the beginning.

        For example if we have derived indices 0, 1, 4, 5 then this will return 1.

        This tells us from where to start deriving again safely
        """
        cursor = self.conn.cursor()
        returned_indices = []
        for acc_idx in (0, 1):
            query = cursor.execute(
                'SELECT derived_index from xpub_mappings WHERE xpub=? AND '
                'derivation_path IS ? AND account_index=?;',
                (xpub_data.xpub.xpub, xpub_data.serialize_derivation_path_for_db(), acc_idx),
            )
            prev_index = -1
            for result in query:
                index = int(result[0])
                if index != prev_index + 1:
                    break

                prev_index = index

            returned_indices.append(0 if prev_index == -1 else prev_index)

        return tuple(returned_indices)  # type: ignore

    def get_addresses_to_xpub_mapping(
            self,
            addresses: List[BTCAddress],
    ) -> Dict[BTCAddress, XpubData]:
        cursor = self.conn.cursor()

        data = {}
        for address in addresses:
            result = cursor.execute(
                'SELECT B.address, A.xpub, A.derivation_path FROM xpubs as A '
                'LEFT OUTER JOIN xpub_mappings as B '
                'ON B.xpub = A.xpub AND B.derivation_path IS A.derivation_path '
                'WHERE B.address=?;', (address,),
            )
            result = result.fetchall()
            if len(result) == 0:
                continue

            data[result[0][0]] = XpubData(
                xpub=HDKey.from_xpub(result[0][1], path='m'),
                derivation_path=deserialize_derivation_path_for_db(result[0][2]),
            )

        return data

    def ensure_xpub_mappings_exist(
            self,
            xpub: str,
            derivation_path: Optional[str],
            derived_addresses_data: List[XpubDerivedAddressData],
    ) -> None:
        """Create if not existing the mappings between the addresses and the xpub"""
        tuples = [
            (
                x.address,
                xpub,
                '' if derivation_path is None else derivation_path,
                x.account_index,
                x.derived_index,
            ) for x in derived_addresses_data
        ]
        cursor = self.conn.cursor()
        for entry in tuples:
            try:
                cursor.execute(
                    'INSERT INTO xpub_mappings'
                    '(address, xpub, derivation_path, account_index, derived_index) '
                    'VALUES (?, ?, ?, ?, ?)',
                    entry,
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                # mapping already exists
                continue

        self.update_last_write()

    def _ensure_data_integrity(
            self,
            table_name: str,
            klass: Union[Type[Trade], Type[AssetMovement], Type[MarginPosition]],
    ) -> None:
        updates: List[Tuple[str, str]] = []
        cursor = self.conn.cursor()
        results = cursor.execute(f'SELECT * from {table_name};')
        for result in results:
            try:
                obj = klass.deserialize_from_db(result)
            except (DeserializationError, UnknownAsset):
                continue

            db_id = result[0]
            actual_id = obj.identifier
            if actual_id != db_id:
                updates.append((actual_id, db_id))

        if len(updates) != 0:
            log.debug(
                f'Found {len(updates)} identifier discrepancies in the DB '
                f'for {table_name}. Correcting...',
            )
            cursor.executemany(f'UPDATE {table_name} SET id = ? WHERE id =?;', updates)

    def ensure_data_integrity(self) -> None:
        """Runs some checks for data integrity of the DB that can't be verified by SQLite

        For now it mostly tackles https://github.com/rotki/rotki/issues/3010 ,
        the problem of identifiers of trades, asset movements and margin positions
        changing and no longer corresponding to the calculated id.
        """
        start_time = ts_now()
        log.debug('Starting DB data integrity check')
        self._ensure_data_integrity('trades', Trade)
        self._ensure_data_integrity('asset_movements', AssetMovement)
        self._ensure_data_integrity('margin_positions', MarginPosition)
        self.conn.commit()
        log.debug(f'DB data integrity check finished after {ts_now() - start_time} seconds')

    def get_db_info(self) -> Dict[str, Any]:
        filepath = self.user_data_dir / 'rotkehlchen.db'
        size = Path(self.user_data_dir / 'rotkehlchen.db').stat().st_size
        version = self.get_version()
        return {
            'filepath': str(filepath),
            'size': int(size),
            'version': int(version),
        }

    def get_backups(self) -> List[Dict[str, Any]]:
        """Returns a list of tuples with possible backups of the user DB"""
        backups = []
        for root, _, files in os.walk(self.user_data_dir):
            for filename in files:
                match = DB_BACKUP_RE.search(filename)
                if match:
                    timestamp = match.group(1)
                    version = match.group(2)
                    try:
                        size: Optional[int] = Path(Path(root) / filename).stat().st_size
                    except OSError:
                        size = None
                    backups.append({
                        'time': int(timestamp),
                        'version': int(version),
                        'size': size,
                    })

        return backups

    def create_db_backup(self) -> Path:
        """May raise:
        - OSError
        """
        version = self.get_version()
        new_db_filename = f'{ts_now()}_rotkehlchen_db_v{version}.backup'
        new_db_path = self.user_data_dir / new_db_filename
        shutil.copyfile(
            self.user_data_dir / 'rotkehlchen.db',
            new_db_path,
        )
        return new_db_path

    def get_associated_locations(self) -> Set[Location]:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT location FROM trades UNION '
            'SELECT location FROM asset_movements UNION '
            'SELECT location FROM ledger_actions UNION '
            'SELECT location FROM margin_positions UNION '
            'SELECT location FROM user_credentials UNION '
            'SELECT location FROM amm_swaps UNION '
            'SELECT location FROM history_events',
        )
        locations = {Location.deserialize_from_db(loc[0]) for loc in cursor}
        cursor.execute('SELECT DISTINCT type FROM amm_events')
        for event_type in cursor:
            if EventType.deserialize_from_db(event_type[0]) in (EventType.MINT_SUSHISWAP, EventType.BURN_SUSHISWAP):  # noqa: E501
                locations.add(Location.SUSHISWAP)
            else:
                locations.add(Location.UNISWAP)
        cursor.execute('SELECT COUNT(*) FROM balancer_events')
        if cursor.fetchone()[0] >= 1:
            locations.add(Location.BALANCER)
        return locations

    def add_history_events(self, history: List[HistoryBaseEntry]) -> None:
        """Insert a list of history events in database. May raise:
        - InputError if the events couldn't be stored in database
        """
        query_str = """INSERT INTO history_events(identifier, event_identifier, sequence_index,
        timestamp,location, location_label, asset, amount, usd_value, notes,
        type, subtype) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
        cursor = self.conn.cursor()
        events = []
        for event in history:
            try:
                events.append(event.serialize_for_db())
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Failed to process kraken event for database. {str(e)}',
                )
        try:
            cursor.executemany(query_str, events)
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            log.error(f'Failed to save history events: {history}')
            raise InputError(f'Failed to save history events in database. {str(e)}') from e

        self.update_last_write()

    def delete_history_events(self, location: Location) -> None:
        """
        Deletes history entries following the criteria of the filter_query. May raise:
        - DeserializationError if the location is not valid
        """
        # TODO: In the future this method should allow for more granularity in the delete query
        query = 'DELETE FROM history_events WHERE location=?'
        cursor = self.conn.cursor()
        cursor.execute(query, (location.serialize_for_db(),))
        cursor.execute(
            f'DELETE FROM used_query_ranges WHERE name LIKE "{location}_history_events_%"',
        )
        self.update_last_write()

    def get_history_events(self, filter_query: HistoryEventFilterQuery) -> List[HistoryBaseEntry]:
        """
        Get history events using the provided query filter. May raise:
        - DeserializationError
        """
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT * FROM history_events ' + query
        cursor = self.conn.cursor()
        cursor.execute(query, bindings)
        result = []
        for entry in cursor:
            try:
                result.append(HistoryBaseEntry.deserialize_from_db(entry))
            except DeserializationError as e:
                log.debug(f'Failed to deserialize history event {entry}')
                self.msg_aggregator.add_error(
                    f'Failed to read history event from database. {str(e)}',
                )
        return result
