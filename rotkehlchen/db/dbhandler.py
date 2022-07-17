import json
import logging
import os
import re
import shutil
import tempfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset, EvmToken
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
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import EventType, LiquidityPoolEvent
from rotkehlchen.chain.ethereum.modules.aave.common import atoken_to_asset
from rotkehlchen.chain.ethereum.modules.aave.structures import AaveEvent, aave_event_from_db
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
)
from rotkehlchen.chain.ethereum.modules.sushiswap import SUSHISWAP_EVENTS_PREFIX
from rotkehlchen.chain.ethereum.modules.uniswap import UNISWAP_EVENTS_PREFIX
from rotkehlchen.chain.ethereum.trades import AMMSwap
from rotkehlchen.chain.ethereum.types import NodeName, WeightedNode
from rotkehlchen.constants.assets import A_ETH, A_ETH2, A_USD
from rotkehlchen.constants.ethereum import YEARN_VAULTS_PREFIX, YEARN_VAULTS_V2_PREFIX
from rotkehlchen.constants.limits import (
    FREE_ASSET_MOVEMENTS_LIMIT,
    FREE_TRADES_LIMIT,
    FREE_USER_NOTES_LIMIT,
)
from rotkehlchen.constants.misc import NFT_DIRECTIVE, ONE, ZERO
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.constants import (
    BINANCE_MARKETS_KEY,
    KRAKEN_ACCOUNT_TYPE_KEY,
    USER_CREDENTIAL_MAPPING_KEYS,
)
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType, DBCursor
from rotkehlchen.db.eth2 import ETH2_DEPOSITS_PREFIX
from rotkehlchen.db.ethtx import DBEthTx
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    TradesFilterQuery,
    UserNotesFilterQuery,
)
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.db.misc import detect_sqlcipher_version
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.schema_transient import DB_SCRIPT_CREATE_TRANSIENT_TABLES
from rotkehlchen.db.settings import (
    DEFAULT_PREMIUM_SHOULD_SYNC,
    ROTKEHLCHEN_DB_VERSION,
    ROTKEHLCHEN_TRANSIENT_DB_VERSION,
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
    combine_asset_balances,
    deserialize_tags_from_db,
    form_query_to_filter_timestamps,
    insert_tag_mappings,
    is_valid_db_blockchain_account,
    need_cursor,
    need_writable_cursor,
    str_to_bool,
)
from rotkehlchen.errors.api import AuthenticationError, IncorrectApiKeyFormat
from rotkehlchen.errors.asset import UnknownAsset, UnsupportedAsset
from rotkehlchen.errors.misc import InputError, SystemPermissionError, TagConstraintError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.ftx import FTX_SUBACCOUNT_DB_SETTING
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.serialization.deserialize import deserialize_hex_color_code
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetMovementCategory,
    BlockchainAccountData,
    BTCAddress,
    ChecksumEvmAddress,
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
    UserNote,
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

DBTupleType = Literal[
    'trade',
    'asset_movement',
    'margin_position',
    'ethereum_transaction',
    'amm_swap',
    'accounting_event',
    'history_event',
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

SETTING_TO_DEFAULT_TYPE = {
    'version': (int, ROTKEHLCHEN_DB_VERSION),
    'last_write_ts': (int, Timestamp(0)),
    'last_data_upload_ts': (int, Timestamp(0)),
    'premium_should_sync': (str_to_bool, DEFAULT_PREMIUM_SHOULD_SYNC),
    'main_currency': (Asset, A_USD),
}


DB_BACKUP_RE = re.compile(r'(\d+)_rotkehlchen_db_v(\d+).backup')


def _protect_password_sqlcipher(password: str) -> str:
    """A double quote in the password would close the string. To escape it double it

    source: https://stackoverflow.com/a/603579/110395
"""
    return password.replace(r'"', r'""')


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
    if tuple_type == 'history_event':
        return (
            f'History event with event identifier {data[0]} from '
            f'{Location.deserialize_from_db(data[3])}.'
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
            sql_vm_instructions_cb: int,
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
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        self.sqlcipher_version = detect_sqlcipher_version()
        self.last_write_ts: Optional[Timestamp] = None
        self.conn: DBConnection = None  # type: ignore
        self.conn_transient: DBConnection = None  # type: ignore
        self._connect(password)
        self._run_actions_after_first_connection(password)
        with self.user_write() as cursor:
            if initial_settings is not None:
                self.set_settings(cursor, initial_settings)
            self.update_owned_assets_in_globaldb(cursor)
            self.add_globaldb_assetids(cursor)

    def __del__(self) -> None:
        self.logout()

    def logout(self) -> None:
        if self.conn is not None:
            self.disconnect(conn_attribute='conn')
        if self.conn_transient is not None:
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
        if self.conn_transient:
            transient_version = 0
            cursor = self.conn_transient.cursor()
            try:
                result = cursor.execute('SELECT value FROM settings WHERE name=?', ('version',)).fetchone()  # noqa: E501
                if result is not None:
                    transient_version = int(result[0])
            except sqlcipher.DatabaseError:
                pass   # not created yet

            if transient_version != ROTKEHLCHEN_TRANSIENT_DB_VERSION:
                # "upgrade" transient DB
                tables = list(cursor.execute('select name from sqlite_master where type is "table"'))  # noqa: E501
                cursor.executescript('PRAGMA foreign_keys = OFF;')
                cursor.executescript(';'.join([f'DROP TABLE IF EXISTS {name[0]}' for name in tables]))  # noqa: E501
                cursor.executescript('PRAGMA foreign_keys = ON;')
            self.conn_transient.executescript(DB_SCRIPT_CREATE_TRANSIENT_TABLES)
            cursor.execute(
                'INSERT OR IGNORE INTO settings(name, value) VALUES(?, ?)',
                ('version', str(ROTKEHLCHEN_TRANSIENT_DB_VERSION)),
            )
            self.conn_transient.commit()

    def get_md5hash(self, transient: bool = False) -> str:
        """Get the md5hash of the DB

        May raise:
        - SystemPermissionError if there are permission errors when accessing the DB
        """
        assert self.conn is None, 'md5hash should be taken only with a closed DB'
        if transient:  # type: ignore
            return file_md5(self.user_data_dir / TRANSIENT_DB_NAME)
        return file_md5(self.user_data_dir / MAIN_DB_NAME)

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['version']) -> int:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['last_write_ts', 'last_data_upload_ts']) -> Timestamp:  # noqa: E501
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['premium_should_sync']) -> bool:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['main_currency']) -> Asset:
        ...

    def get_setting(  # pylint: disable=no-self-use
            self,
            cursor: 'DBCursor',
            name: Literal['version', 'last_write_ts', 'last_data_upload_ts', 'premium_should_sync', 'main_currency'],  # noqa: E501
    ) -> Union[int, Timestamp, bool, Asset]:
        deserializer, default_value = SETTING_TO_DEFAULT_TYPE[name]
        cursor.execute(
            'SELECT value FROM settings WHERE name=?;', (name,),
        )
        result = cursor.fetchone()
        if result is not None:
            return deserializer(result[0])  # type: ignore

        return default_value  # type: ignore

    def set_setting(  # pylint: disable=no-self-use
            self,
            write_cursor: 'DBCursor',
            name: Literal['version', 'last_write_ts', 'last_data_upload_ts', 'premium_should_sync'],  # noqa: E501
            value: Union[int, Timestamp],
    ) -> None:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (name, str(value)),
        )

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
            connection_type = DBConnectionType.USER
        else:
            fullpath = self.user_data_dir / TRANSIENT_DB_NAME
            connection_type = DBConnectionType.TRANSIENT
        try:
            conn = DBConnection(
                path=str(fullpath),
                connection_type=connection_type,
                sql_vm_instructions_cb=self.sql_vm_instructions_cb,
            )
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            raise SystemPermissionError(
                f'Could not open database file: {fullpath}. Permission errors?',
            ) from e

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
            self.conn = DBConnection(
                path=tempdbpath,
                connection_type=DBConnectionType.USER,
                sql_vm_instructions_cb=self.sql_vm_instructions_cb,
            )
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

    @contextmanager
    def user_write(self) -> Iterator[DBCursor]:
        """Get a write context for the user db and after write is finished
        also update the last write timestamp
        """
        cursor = self.conn.cursor()
        try:
            yield cursor
        except Exception:
            self.conn.rollback()
            raise
        else:
            # Also keep it in memory for faster querying
            self.last_write_ts = ts_now()
            cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('last_write_ts', str(self.last_write_ts)),
            )
            self.conn.commit()
        finally:
            cursor.close()

    @contextmanager
    def transient_write(self) -> Iterator[DBCursor]:
        """Get a write context for the transient user db and after write is finished
        also commit
        """
        cursor = self.conn_transient.cursor()
        try:
            yield cursor
        except Exception:
            self.conn.rollback()
            raise
        else:
            self.conn_transient.commit()
        finally:
            cursor.close()

    # pylint: disable=no-self-use
    def get_settings(self, cursor: 'DBCursor', have_premium: bool = False) -> DBSettings:
        """Aggregates settings from DB and from the given args and returns the settings object"""
        cursor.execute('SELECT name, value FROM settings;')
        settings_dict = {}
        for q in cursor:
            settings_dict[q[0]] = q[1]

        # Also add the non-DB saved settings
        settings_dict['have_premium'] = have_premium
        return db_settings_from_dict(settings_dict, self.msg_aggregator)

    # pylint: disable=no-self-use
    def set_settings(self, write_cursor: 'DBCursor', settings: ModifiableDBSettings) -> None:
        settings_dict = settings.serialize()
        write_cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            list(settings_dict.items()),
        )

    # pylint: disable=no-self-use
    @need_writable_cursor('user_write')
    def add_external_service_credentials(
            self,
            write_cursor: 'DBCursor',
            credentials: List[ExternalServiceApiCredentials],
    ) -> None:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key) VALUES(?, ?)',
            [c.serialize_for_db() for c in credentials],
        )

    def delete_external_service_credentials(self, services: List[ExternalService]) -> None:
        with self.user_write() as cursor:
            cursor.executemany(
                'DELETE FROM external_service_credentials WHERE name=?;',
                [(service.name.lower(),) for service in services],
            )

    def get_all_external_service_credentials(self) -> List[ExternalServiceApiCredentials]:
        """Returns a list with all the external service credentials saved in the DB"""
        with self.conn.read_ctx() as cursor:
            cursor.execute('SELECT name, api_key from external_service_credentials;')

            result = []
            for q in cursor:
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
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT api_key from external_service_credentials WHERE name=?;',
                (service_name.name.lower(),),
            )
            result = cursor.fetchone()
            if result is None:
                return None

            # There can only be 1 result, since name is the primary key of the table
            return ExternalServiceApiCredentials(service=service_name, api_key=result[0])

    # pylint: disable=no-self-use
    @need_writable_cursor('user_write')
    def add_to_ignored_assets(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        write_cursor.execute(
            'INSERT INTO multisettings(name, value) VALUES(?, ?)',
            ('ignored_asset', asset.identifier),
        )

    # pylint: disable=no-self-use
    def remove_from_ignored_assets(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        write_cursor.execute(
            'DELETE FROM multisettings WHERE name="ignored_asset" AND value=?;',
            (asset.identifier,),
        )

    def get_ignored_assets(self, cursor: 'DBCursor') -> List[Asset]:
        cursor.execute(
            'SELECT value FROM multisettings WHERE name="ignored_asset";',
        )
        assets = []
        for asset_setting in cursor:
            try:
                asset = Asset(asset_setting[0])
            except UnknownAsset:
                msg = (
                    f'Found unknown asset {asset_setting[0]} in the list of ignored '
                    f'assets. Removing it.'
                )
                with self.user_write() as write_cursor:
                    write_cursor.execute(
                        'DELETE FROM multisettings WHERE name="ignored_asset" AND value=?;',
                        (asset_setting[0],),
                    )
                self.msg_aggregator.add_warning(msg)
                continue

            assets.append(asset)

        return assets

    def add_to_ignored_action_ids(
            self,
            write_cursor: 'DBCursor',
            action_type: ActionType,
            identifiers: List[str],
    ) -> None:
        """Adds a list of identifiers to be ignored for a given action type

        Raises InputError in case of adding already existing ignored action
        """
        tuples = [(action_type.serialize_for_db(), x) for x in identifiers]
        try:
            write_cursor.executemany(
                'INSERT INTO ignored_actions(type, identifier) VALUES(?, ?)',
                tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError('One of the given action ids already exists in the dataase') from e  # noqa: E501

    def remove_from_ignored_action_ids(
            self,
            write_cursor: 'DBCursor',
            action_type: ActionType,
            identifiers: List[str],
    ) -> None:
        """Removes a list of identifiers to be ignored for a given action type

        Raises InputError in case of removing an action that is not in the DB
        """
        tuples = [(action_type.serialize_for_db(), x) for x in identifiers]
        write_cursor.executemany(
            'DELETE FROM ignored_actions WHERE type=? AND identifier=?;',
            tuples,
        )
        affected_rows = write_cursor.rowcount
        if affected_rows != len(identifiers):
            raise InputError(
                f'Tried to remove {len(identifiers) - affected_rows} '
                f'ignored actions that do not exist',
            )

    # pylint: disable=no-self-use
    def get_ignored_action_ids(
            self,
            cursor: 'DBCursor',
            action_type: Optional[ActionType],
    ) -> Dict[ActionType, List[str]]:
        query = 'SELECT type, identifier from ignored_actions'
        tuples: Tuple
        if action_type is None:
            query += ';'
            tuples = ()
        else:
            query += ' WHERE type=?;'
            tuples = (action_type.serialize_for_db(),)

        cursor.execute(query, tuples)
        mapping = defaultdict(list)
        for entry in cursor:
            mapping[ActionType.deserialize_from_db(entry[0])].append(entry[1])

        return mapping

    # pylint: disable=no-self-use
    def add_multiple_balances(self, write_cursor: 'DBCursor', balances: List[DBAssetBalance]) -> None:  # noqa: E501
        """Execute addition of multiple balances in the DB"""
        serialized_balances = [balance.serialize_for_db() for balance in balances]
        try:
            write_cursor.executemany(
                'INSERT INTO timed_balances(category, timestamp, currency, amount, usd_value) '
                'VALUES(?, ?, ?, ?, ?)',
                serialized_balances,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                'Adding timed_balance failed. Either unknown asset identifier '
                'or an entry for the given timestamp already exists',
            ) from e

    # pylint: disable=no-self-use
    def add_aave_events(self, write_cursor: 'DBCursor', address: ChecksumEvmAddress, events: Sequence[AaveEvent]) -> None:  # noqa: E501
        for e in events:
            event_tuple = e.to_db_tuple(address)
            try:
                write_cursor.execute(
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

    def get_aave_events(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            atoken: Optional[EvmToken] = None,
    ) -> List[AaveEvent]:
        """Get aave for a single address and a single aToken """
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

        events = []
        cursor.execute(querystr, values)
        for result in cursor:
            try:
                event = aave_event_from_db(result)
            except DeserializationError:
                continue  # skip entry. Above function should already log an error
            events.append(event)

        return events

    def delete_aave_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical aave event data"""
        write_cursor.execute('DELETE FROM aave_events;')
        write_cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')

    def add_adex_events(
            self,
            write_cursor: 'DBCursor',
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
        for event in events:
            event_tuple = event.to_db_tuple()
            try:
                write_cursor.execute(query, event_tuple)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add an AdEx event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping event.',
                )
                continue

    # pylint: disable=no-self-use
    @need_cursor('conn.read_ctx')
    def get_adex_events(
            self,
            cursor: 'DBCursor',
            from_timestamp: Optional[Timestamp] = None,
            to_timestamp: Optional[Timestamp] = None,
            address: Optional[ChecksumEvmAddress] = None,
            bond_id: Optional[str] = None,
            event_type: Optional[AdexEventType] = None,
    ) -> List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]:
        """Returns a list of AdEx events optionally filtered by time and address.
        """
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
        events = []
        cursor.execute(query, bindings)
        for event_tuple in cursor:
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

    def delete_adex_events_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical AdEx events data"""
        write_cursor.execute('DELETE FROM adex_events;')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?', (f'{ADEX_EVENTS_PREFIX}%',),
        )

    def delete_balancer_trades_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical Balancer trades data"""
        write_cursor.execute(
            'DELETE FROM amm_swaps WHERE location=?',
            (Location.BALANCER.serialize_for_db(),),  # pylint: disable=no-member
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{BALANCER_TRADES_PREFIX}%',),
        )

    def delete_balancer_events_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical Balancer events data"""
        write_cursor.execute('DELETE FROM balancer_events;')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{BALANCER_EVENTS_PREFIX}%',),
        )

    def delete_eth2_deposits(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical ETH2 eth2_deposits data"""
        write_cursor.execute('DELETE FROM eth2_deposits;')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{ETH2_DEPOSITS_PREFIX}%',),
        )

    def delete_eth2_daily_stats(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical ETH2 eth2_daily_staking_details data"""
        write_cursor.execute('DELETE FROM eth2_daily_staking_details;')

    def add_amm_events(self, write_cursor: 'DBCursor', events: Sequence[LiquidityPoolEvent]) -> None:  # noqa: E501
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
        for event in events:
            event_tuple = event.to_db_tuple()
            try:
                write_cursor.execute(query, event_tuple)
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                self.msg_aggregator.add_warning(
                    f'Tried to add an AMM event that already exists in the DB. '
                    f'Event data: {event_tuple}. Skipping event.',
                )
                continue

    def get_amm_events(
            self,
            cursor: 'DBCursor',
            events: List[EventType],
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            address: Optional[ChecksumEvmAddress] = None,
    ) -> List[LiquidityPoolEvent]:
        """Returns a list of amm events optionally filtered by time, location
        and address
        """
        events_sql_str = ", ".join([f'"{EventType.serialize_for_db(event)}"' for event in events])
        querystr = f'SELECT * FROM amm_events WHERE amm_events.type IN ({events_sql_str}) '

        # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
        if address is not None:
            querystr += f'AND address="{address}" '

        querystr, bindings = form_query_to_filter_timestamps(querystr, 'timestamp', from_ts, to_ts)

        cursor.execute(querystr, bindings)
        db_events = []
        for event_tuple in cursor:
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
        with self.user_write() as cursor:
            if module_name is None:
                self.delete_uniswap_trades_data(cursor)
                self.delete_uniswap_events_data(cursor)
                self.delete_sushiswap_trades_data(cursor)
                self.delete_sushiswap_events_data(cursor)
                self.delete_balancer_trades_data(cursor)
                self.delete_balancer_events_data(cursor)
                self.delete_aave_data(cursor)
                self.delete_adex_events_data(cursor)
                self.delete_yearn_vaults_data(write_cursor=cursor, version=1)
                self.delete_yearn_vaults_data(write_cursor=cursor, version=2)
                self.delete_loopring_data(cursor)
                self.delete_eth2_deposits(cursor)
                self.delete_eth2_daily_stats(cursor)
                log.debug('Purged all module data from the DB')
                return

            if module_name == 'uniswap':
                self.delete_uniswap_trades_data(cursor)
                self.delete_uniswap_events_data(cursor)
            elif module_name == 'sushiswap':
                self.delete_sushiswap_trades_data(cursor)
                self.delete_sushiswap_events_data(cursor)
            elif module_name == 'balancer':
                self.delete_balancer_trades_data(cursor)
                self.delete_balancer_events_data(cursor)
            elif module_name == 'aave':
                self.delete_aave_data(cursor)
            elif module_name == 'adex':
                self.delete_adex_events_data(cursor)
            elif module_name == 'yearn_vaults':
                self.delete_yearn_vaults_data(write_cursor=cursor, version=1)
            elif module_name == 'yearn_vaults_v2':
                self.delete_yearn_vaults_data(write_cursor=cursor, version=2)
            elif module_name == 'loopring':
                self.delete_loopring_data(cursor)
            elif module_name == 'eth2':
                self.delete_eth2_deposits(cursor)
                self.delete_eth2_daily_stats(cursor)
            else:
                log.debug(f'Requested to purge {module_name} data from the DB but nothing to do')
                return

            log.debug(f'Purged {module_name} data from the DB')

    def delete_uniswap_trades_data(self, write_cursor: DBCursor) -> None:
        """Delete all historical Uniswap trades data"""
        write_cursor.execute(
            'DELETE FROM amm_swaps WHERE location=?',
            (Location.UNISWAP.serialize_for_db(),),  # pylint: disable=no-member
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{UNISWAP_TRADES_PREFIX}%',),
        )

    def delete_uniswap_events_data(self, write_cursor: DBCursor) -> None:
        """Delete all historical Uniswap events data"""
        write_cursor.execute(
            'DELETE FROM amm_events WHERE amm_events.type IN (?, ?);',
            (EventType.serialize_for_db(EventType.MINT_UNISWAP), EventType.serialize_for_db(EventType.BURN_UNISWAP)),  # noqa: E501
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{UNISWAP_EVENTS_PREFIX}%',),
        )

    def delete_sushiswap_trades_data(self, write_cursor: DBCursor) -> None:
        """Delete all historical Sushiswap trades data"""
        write_cursor.execute(
            'DELETE FROM amm_swaps WHERE location=?',
            (Location.SUSHISWAP.serialize_for_db(),),  # pylint: disable=no-member
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{SUSHISWAP_TRADES_PREFIX}%',),
        )

    def delete_sushiswap_events_data(self, write_cursor: DBCursor) -> None:
        """Delete all historical Sushiswap events data"""
        write_cursor.execute(
            'DELETE FROM amm_events WHERE amm_events.type IN (?, ?)',
            (EventType.serialize_for_db(EventType.MINT_SUSHISWAP), EventType.serialize_for_db(EventType.BURN_SUSHISWAP)),  # noqa: E501
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            (f'{SUSHISWAP_EVENTS_PREFIX}%',),
        )

    def delete_yearn_vaults_data(self, write_cursor: 'DBCursor', version: int) -> None:
        """Delete all historical yearn vault events data"""
        if version not in (1, 2):
            log.error(f'Called delete yearn vault data with non valid version {version}')
            return None
        prefix = YEARN_VAULTS_PREFIX
        if version == 2:
            prefix = YEARN_VAULTS_V2_PREFIX
        write_cursor.execute('DELETE FROM yearn_vaults_events WHERE version=?', (version,))
        write_cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE ?', (f'{prefix}%',))
        return None

    def delete_loopring_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all loopring related data"""
        write_cursor.execute('DELETE FROM multisettings WHERE name LIKE "loopring_%";')

    # pylint: disable=no-self-use
    def get_used_query_range(self, cursor: 'DBCursor', name: str) -> Optional[Tuple[Timestamp, Timestamp]]:  # noqa: E501
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
        cursor.execute('SELECT start_ts, end_ts from used_query_ranges WHERE name=?', (name,))
        result = cursor.fetchone()
        if result is None:
            return None

        return Timestamp(int(result[0])), Timestamp(int(result[1]))

    def delete_used_query_range_for_exchange(self, write_cursor: 'DBCursor', location: Location) -> None:  # noqa: E501
        """Delete the query ranges for the given exchange name"""
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{str(location)}\\_%', '\\'),
        )

    def purge_exchange_data(self, write_cursor: 'DBCursor', location: Location) -> None:
        self.delete_used_query_range_for_exchange(write_cursor=write_cursor, location=location)
        write_cursor.execute(
            'DELETE FROM trades WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        write_cursor.execute(
            'DELETE FROM asset_movements WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        write_cursor.execute(
            'DELETE FROM ledger_actions WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        write_cursor.execute(
            'DELETE FROM asset_movements WHERE location = ?;',
            (location.serialize_for_db(),),
        )
        write_cursor.execute(
            'DELETE FROM history_events WHERE location = ?;',
            (location.serialize_for_db(),),
        )

    def update_used_query_range(self, write_cursor: 'DBCursor', name: str, start_ts: Timestamp, end_ts: Timestamp) -> None:  # noqa: E501
        write_cursor.execute(
            'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
            (name, str(start_ts), str(end_ts)),
        )

    def update_used_block_query_range(self, write_cursor: 'DBCursor', name: str, from_block: int, to_block: int) -> None:  # noqa: E501
        self.update_used_query_range(write_cursor, name, from_block, to_block)  # type: ignore

    def get_last_balance_save_time(self, cursor: 'DBCursor') -> Timestamp:
        cursor.execute(
            'SELECT MAX(timestamp) from timed_location_data',
        )
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return Timestamp(0)

        return Timestamp(int(result[0]))

    def add_multiple_location_data(self, write_cursor: 'DBCursor', location_data: List[LocationData]) -> None:  # noqa: E501
        """Execute addition of multiple location data in the DB"""
        for entry in location_data:
            try:
                write_cursor.execute(
                    'INSERT INTO timed_location_data('
                    '    timestamp, location, usd_value) '
                    ' VALUES(?, ?, ?)',
                    (entry.time, entry.location, entry.usd_value),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(
                    f'Tried to add a timed_location_data for '
                    f'{str(Location.deserialize_from_db(entry.location))} at'
                    f' already existing timestamp {entry.time}.',
                ) from e

    # pylint: disable=no-self-use
    def add_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> None:
        # Insert the blockchain account addresses and labels to the DB
        tuples = [(
            blockchain.value,
            entry.address,
            entry.label,
        ) for entry in account_data]
        try:
            write_cursor.executemany(
                'INSERT INTO blockchain_accounts(blockchain, account, label) VALUES (?, ?, ?)',
                tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Blockchain account/s {[x.address for x in account_data]} already exist',
            ) from e

        insert_tag_mappings(write_cursor=write_cursor, data=account_data, object_reference_keys=['address'])  # noqa: E501

    def edit_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            account_data: List[BlockchainAccountData],
    ) -> None:
        """Edit the given blockchain accounts

        At this point in the calling chain we should already know that:
        - All tags exist in the DB
        - All accounts exist in the DB
        """
        # Delete the current tag mappings for all affected accounts
        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', [(x.address,) for x in account_data],
        )

        # Update the blockchain account labels in the DB
        tuples = [(
            entry.label,
            entry.address,
            blockchain.value,
        ) for entry in account_data]
        write_cursor.executemany(
            'UPDATE blockchain_accounts SET label=? WHERE account=? AND blockchain=?;', tuples,
        )
        if write_cursor.rowcount != len(account_data):
            msg = (
                f'When updating blockchain accounts {len(account_data)} entries should '
                f'have been edited but only {write_cursor.rowcount} were. Should not happen.'
            )
            log.error(msg)
            raise InputError(msg)

        insert_tag_mappings(write_cursor=write_cursor, data=account_data, object_reference_keys=['address'])  # noqa: E501

    def remove_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes the given blockchain accounts from the DB

        May raise:
        - InputError if any of the given accounts to delete did not exist
        """
        # First remove all transaction related information for this address.
        # Needs to happen before the address is removed since removing the address
        # will also remove ethtx_address_mappings, thus making it impossible
        # to figure out which transactions are touched by this address
        if blockchain == SupportedBlockchain.ETHEREUM:
            for address in accounts:
                self.delete_data_for_ethereum_address(write_cursor, address)  # type: ignore

        tuples = [(blockchain.value, x) for x in accounts]
        account_tuples = [(x,) for x in accounts]

        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', account_tuples,
        )
        write_cursor.executemany(
            'DELETE FROM blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', tuples,
        )
        affected_rows = write_cursor.rowcount
        if affected_rows != len(accounts):
            raise InputError(
                f'Tried to remove {len(accounts) - affected_rows} '
                f'{blockchain.value} accounts that do not exist',
            )

    def _get_address_details(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Timestamp]]:
        query = cursor.execute(
            'SELECT tokens_list, timestamp FROM ethereum_accounts_details WHERE account = ?',
            (address,),
        )
        result = query.fetchall()
        if len(result) == 0:
            return None, None  # no saved entry

        last_update_ts = Timestamp(result[0][1])
        try:
            json_ret = json.loads(result[0][0])
        except json.decoder.JSONDecodeError as e:
            # This should never happen
            self.msg_aggregator.add_warning(
                f'Found undecodeable json {result[0][0]} in the DB for {address}.'
                f'Error: {str(e)}',
            )
            return None, last_update_ts

        if not isinstance(json_ret, dict):
            # This can happen if the DB is old and still has only a list of saved tokens
            return None, last_update_ts  # In that case just consider it outdated

        return json_ret, last_update_ts

    def get_tokens_for_address(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
    ) -> Tuple[Optional[List[EvmToken]], Optional[Timestamp]]:
        """Gets the detected tokens for the given address if the given current time
        is recent enough.

        If not, or if there is no saved entry, return None
        """
        json_ret, last_update_ts = self._get_address_details(cursor, address)
        if json_ret is None:
            return None, last_update_ts
        tokens_list = json_ret.get('tokens', None)
        if tokens_list is None:
            return None, last_update_ts

        if not isinstance(tokens_list, list):
            # This should never happen
            self.msg_aggregator.add_warning(
                f'Found non-list tokens_list {json_ret} in the DB for {address}.',
            )
            return None, last_update_ts

        if len(tokens_list) == 0:
            return None, last_update_ts

        returned_list = []
        for x in tokens_list:
            try:
                token = EvmToken.from_identifier(x)
            except (DeserializationError, UnknownAsset):
                token = None
            if token is None:
                self.msg_aggregator.add_warning(
                    f'Could not deserialize {x} as a token when reading latest '
                    f'tokens list of {address}',
                )
                continue

            returned_list.append(token)

        return returned_list, last_update_ts

    def _get_address_details_json(self, cursor: 'DBCursor', address: ChecksumEvmAddress) -> Optional[Dict[str, Any]]:  # noqa: E501
        query = cursor.execute(
            'SELECT tokens_list, timestamp FROM ethereum_accounts_details WHERE account = ?',
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
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            tokens: List[EvmToken],
    ) -> None:
        """Saves detected tokens for an address"""
        old_details = self._get_address_details_json(write_cursor, address)
        new_details = {}
        if old_details and 'univ2_lp_tokens' in old_details:
            new_details['univ2_lp_tokens'] = old_details['univ2_lp_tokens']
        new_details['tokens'] = [x.identifier for x in tokens]
        now = ts_now()
        write_cursor.execute(
            'INSERT OR REPLACE INTO ethereum_accounts_details '
            '(account, tokens_list, timestamp) VALUES (?, ?, ?)',
            (address, json.dumps(new_details), now),
        )

    def get_blockchain_accounts(self, cursor: 'DBCursor') -> BlockchainAccounts:
        """Returns a Blockchain accounts instance containing all blockchain account addresses"""
        eth_list = []
        btc_list = []
        bch_list = []
        ksm_list = []
        dot_list = []
        avax_list = []

        supported_blockchains = {blockchain.value for blockchain in SupportedBlockchain}
        cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts;',
        )
        for entry in cursor:
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
            elif entry[0] == SupportedBlockchain.BITCOIN_CASH.value:
                bch_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.ETHEREUM.value:
                eth_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.KUSAMA.value:
                ksm_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.AVALANCHE.value:
                avax_list.append(entry[1])
            elif entry[0] == SupportedBlockchain.POLKADOT.value:
                dot_list.append(entry[1])

        return BlockchainAccounts(eth=eth_list, btc=btc_list, bch=bch_list, ksm=ksm_list, dot=dot_list, avax=avax_list)  # noqa: E501

    def get_blockchain_account_data(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> List[BlockchainAccountData]:
        """Returns account data for a particular blockchain.

        Each account entry contains address and potentially label and tags
        """
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
            cursor: 'DBCursor',
            balance_type: Optional[BalanceType] = BalanceType.ASSET,
    ) -> List[ManuallyTrackedBalance]:
        """Returns the manually tracked balances from the DB"""
        query_balance_type = ''
        if balance_type is not None:
            query_balance_type = f'WHERE A.category="{balance_type.serialize_for_db()}"'
        query = cursor.execute(
            f'SELECT A.asset, A.label, A.amount, A.location, group_concat(B.tag_name,","), '
            f'A.category, A.id FROM manually_tracked_balances as A '
            f'LEFT OUTER JOIN tag_mappings as B on B.object_reference = A.id '
            f'{query_balance_type} GROUP BY label;',
        )

        data = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[4])
            try:
                balance_type = BalanceType.deserialize_from_db(entry[5])
                data.append(ManuallyTrackedBalance(
                    id=entry[6],
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

    # pylint: disable=no-self-use
    def add_manually_tracked_balances(self, write_cursor: 'DBCursor', data: List[ManuallyTrackedBalance]) -> None:  # noqa: E501
        """Adds manually tracked balances in the DB

        May raise:
        - InputError if one of the given balance entries already exist in the DB
        """
        # Insert the manually tracked balances in the DB
        try:
            for entry in data:
                write_cursor.execute(
                    'INSERT INTO manually_tracked_balances(asset, label, amount, location, category) '  # noqa: E501
                    'VALUES (?, ?, ?, ?, ?)', (entry.asset.identifier, entry.label, str(entry.amount), entry.location.serialize_for_db(), entry.balance_type.serialize_for_db()),  # noqa: E501
                )
                entry.id = write_cursor.lastrowid
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'One of the manually tracked balance entries already exists in the DB. {str(e)}',
            ) from e

        insert_tag_mappings(write_cursor=write_cursor, data=data, object_reference_keys=['id'])

        # make sure assets are included in the global db user owned assets
        GlobalDBHandler().add_user_owned_assets([x.asset for x in data])

    def edit_manually_tracked_balances(self, write_cursor: 'DBCursor', data: List[ManuallyTrackedBalance]) -> None:  # noqa: E501
        """Edits manually tracked balances

        Edits the manually tracked balances for each of the given balance labels.

        At this point in the calling chain we should already know that:
        - All tags exist in the DB

        May raise:
        - InputError if any of the manually tracked balance labels to edit do not
        exist in the DB
        """
        # Delete the current tag mappings for all affected balance entries
        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', [(x.id,) for x in data],
        )

        # Update the manually tracked balance entries in the DB
        tuples = [(
            entry.asset.identifier,
            str(entry.amount),
            entry.location.serialize_for_db(),
            BalanceType.serialize_for_db(entry.balance_type),
            entry.label,
            entry.id,
        ) for entry in data]

        write_cursor.executemany(
            'UPDATE manually_tracked_balances SET asset=?, amount=?, location=?, category=?, label=?'  # noqa: E501
            'WHERE id=?;', tuples,
        )
        if write_cursor.rowcount != len(data):
            msg = 'Tried to edit manually tracked balance entry that did not exist in the DB'
            raise InputError(msg)
        insert_tag_mappings(write_cursor=write_cursor, data=data, object_reference_keys=['id'])

    def remove_manually_tracked_balances(self, write_cursor: 'DBCursor', ids: List[int]) -> None:
        """
        Removes manually tracked balances for the given ids

        May raise:
        - InputError if any of the given manually tracked balance labels
        to delete did not exist
        """
        tuples = [(x,) for x in ids]
        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE '
            'object_reference = ?;', tuples,
        )
        write_cursor.executemany(
            'DELETE FROM manually_tracked_balances WHERE id = ?;', tuples,
        )
        affected_rows = write_cursor.rowcount
        if affected_rows != len(ids):
            raise InputError(
                f'Tried to remove {len(ids) - affected_rows} '
                f'manually tracked balance ids that do not exist',
            )

    def save_balances_data(self, write_cursor: 'DBCursor', data: Dict[str, Any], timestamp: Timestamp) -> None:  # noqa: E501
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
                amount=val['amount'],
                usd_value=val['usd_value'],
            ))

        for key, val in data['liabilities'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {str(key)}'
            assert isinstance(key, Asset), msg
            balances.append(DBAssetBalance(
                category=BalanceType.LIABILITY,
                time=timestamp,
                asset=key,
                amount=val['amount'],
                usd_value=val['usd_value'],
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
        try:
            self.add_multiple_balances(write_cursor, balances)
            self.add_multiple_location_data(write_cursor, locations)
        except InputError as err:
            self.msg_aggregator.add_warning(str(err))

    def add_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            passphrase: Optional[str] = None,
            kraken_account_type: Optional[KrakenAccountType] = None,
            PAIRS: Optional[List[str]] = None,  # noqa: N803
            ftx_subaccount: Optional[str] = None,
    ) -> None:
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {str(location)}')

        with self.user_write() as cursor:
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
                    (name, location.serialize_for_db(), KRAKEN_ACCOUNT_TYPE_KEY, kraken_account_type.serialize()),  # noqa: E501
                )

            if location in (Location.BINANCE, Location.BINANCEUS) and PAIRS is not None:
                self.set_binance_pairs(cursor, name=name, pairs=PAIRS, location=location)

            if location == Location.FTX and ftx_subaccount is not None:
                self.set_ftx_subaccount(cursor, name, ftx_subaccount)

    def edit_exchange(
            self,
            write_cursor: 'DBCursor',
            name: str,
            location: Location,
            new_name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            PAIRS: Optional[List[str]],  # noqa: N803
            ftx_subaccount: Optional[str],
    ) -> None:
        """May raise InputError if something is wrong with editing the DB"""
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {str(location)}')

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
                write_cursor.execute(querystr, bindings)
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials due to {str(e)}') from e

        if location == Location.KRAKEN and kraken_account_type is not None:
            try:
                write_cursor.execute(
                    'INSERT OR REPLACE INTO user_credentials_mappings '
                    '(credential_name, credential_location, setting_name, setting_value) '
                    'VALUES (?, ?, ?, ?)',
                    (
                        new_name if new_name is not None else name,
                        location.serialize_for_db(),
                        KRAKEN_ACCOUNT_TYPE_KEY,
                        kraken_account_type.serialize(),
                    ),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials_mappings due to {str(e)}') from e  # noqa: E501

        location_is_binance = location in (Location.BINANCE, Location.BINANCEUS)
        if location_is_binance and PAIRS is not None:
            try:
                exchange_name = new_name if new_name is not None else name
                self.set_binance_pairs(write_cursor, name=exchange_name, pairs=PAIRS, location=location)  # noqa: E501
                # Also delete used query ranges to allow fetching missing trades
                # from the possible new pairs
                write_cursor.execute(
                    'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
                    (f'{str(location)}\\_trades_%', '\\'),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials_mappings due to {str(e)}') from e  # noqa: E501
        if location == Location.FTX and ftx_subaccount is not None:
            try:
                exchange_name = new_name if new_name is not None else name
                self.set_ftx_subaccount(write_cursor, exchange_name, ftx_subaccount)
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials_mappings due to {str(e)}') from e  # noqa: E501

        if new_name is not None:
            exchange_re = re.compile(r'(.*?)_(trades|margins|asset_movements|ledger_actions).*')
            used_ranges = write_cursor.execute(
                'SELECT * from used_query_ranges WHERE name LIKE ?',
                (f'{str(location)}_%_{name}',),
            )
            entry_types = set()
            for used_range in used_ranges:
                range_name = used_range[0]
                match = exchange_re.search(range_name)
                if match is None:
                    continue
                entry_types.add(match.group(2))
            write_cursor.executemany(
                'UPDATE used_query_ranges SET name=? WHERE name=?',
                [
                    (f'{str(location)}_{entry_type}_{new_name}', f'{str(location)}_{entry_type}_{name}')  # noqa: E501
                    for entry_type in entry_types
                ],
            )

    def remove_exchange(self, write_cursor: 'DBCursor', name: str, location: Location) -> None:
        write_cursor.execute(
            'DELETE FROM user_credentials WHERE name=? AND location=?',
            (name, location.serialize_for_db()),
        )

    def get_exchange_credentials(
            self,
            cursor: 'DBCursor',
            location: Location = None,
            name: str = None,
    ) -> Dict[Location, List[ExchangeApiCredentials]]:
        """Gets all exchange credentials

        If an exchange name and location are passed the credentials are filtered further
        """
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
            try:
                location = Location.deserialize_from_db(entry[1])
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Found unknown location {entry[1]} for exchange {entry[0]} at '
                    f'get_exchange_credentials. This could mean that you are opening '
                    f'the app with an older version. {str(e)}',
                )
                continue
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
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT setting_name, setting_value FROM user_credentials_mappings '
                'WHERE credential_name=? AND credential_location=?',
                (name, location.serialize_for_db()),
            )
            extras = {}
            for entry in cursor:
                if entry[0] not in USER_CREDENTIAL_MAPPING_KEYS:
                    log.error(
                        f'Unknown credential setting {entry[0]} found in the DB. Skipping.',
                    )
                    continue

                key = entry[0]
                if key == KRAKEN_ACCOUNT_TYPE_KEY:
                    try:
                        extras[key] = KrakenAccountType.deserialize(entry[1])
                    except DeserializationError as e:
                        log.error(f'Couldnt deserialize kraken account type from DB. {str(e)}')
                        continue
                else:
                    extras[key] = entry[1]

        return extras

    def set_binance_pairs(self, write_cursor: 'DBCursor', name: str, pairs: List[str], location: Location) -> None:  # noqa: E501
        """Sets the market pairs used by the user on a specific binance exchange"""
        data = json.dumps(pairs)
        write_cursor.execute(
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

    def get_binance_pairs(self, name: str, location: Location) -> List[str]:
        """Gets the market pairs used by the user on a specific binance exchange"""
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT setting_value FROM user_credentials_mappings WHERE '
                'credential_name=? AND credential_location=? AND setting_name=?',
                (name, location.serialize_for_db(), BINANCE_MARKETS_KEY),  # noqa: E501
            )
            data = cursor.fetchone()
            if data and data[0] != '':
                return json.loads(data[0])
            return []

    def set_ftx_subaccount(self, write_cursor: 'DBCursor', ftx_name: str, subaccount_name: str) -> None:  # noqa: E501
        """This function may raise sqlcipher.DatabaseError"""
        write_cursor.execute(
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
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT setting_value FROM user_credentials_mappings WHERE '
                'credential_name=? AND credential_location=? AND setting_name=?',
                (ftx_name, Location.FTX.serialize_for_db(), FTX_SUBACCOUNT_DB_SETTING),  # noqa: E501 pylint: disable=no-member
            )
            data = cursor.fetchone()
            if data and data[0].strip() != '':
                return data[0]
            return None

    def write_tuples(
            self,
            write_cursor: 'DBCursor',
            tuple_type: DBTupleType,
            query: str,
            tuples: Sequence[Tuple[Any, ...]],
            **kwargs: Optional[ChecksumEvmAddress],
    ) -> None:
        relevant_address = kwargs.get('relevant_address')
        try:
            write_cursor.executemany(query, tuples)
            if relevant_address is not None:
                mapping_tuples = [(relevant_address, x[0], 'ETH') for x in tuples]
                write_cursor.executemany(
                    'INSERT OR IGNORE INTO ethtx_address_mappings(address, tx_hash, blockchain) '
                    'VALUES(?, ?, ?)',
                    mapping_tuples,
                )
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            # That means that one of the tuples hit a constraint, most probably
            # already existing in the DB, in which case we resort to writing them
            # one by one to only reject the duplicates
            for entry in tuples:
                try:
                    write_cursor.execute(query, entry)
                    if relevant_address is not None:
                        write_cursor.execute(
                            'INSERT OR IGNORE INTO ethtx_address_mappings '
                            '(address, tx_hash, blockchain) VALUES(?, ?, ?)',
                            (relevant_address, entry[0], 'ETH'),
                        )
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    if tuple_type == 'ethereum_transaction':
                        # if we reach here it means the transaction is already in the DB
                        # But this can't be avoided with the way we query etherscan
                        # right now since we don't query transactions in a specific
                        # time range, so duplicate addition attempts can happen.
                        # Also if we have transactions of one account sending to the
                        # other and both accounts are being tracked.
                        if relevant_address is not None:
                            write_cursor.execute(
                                'INSERT OR IGNORE INTO ethtx_address_mappings '
                                '(address, tx_hash, blockchain) VALUES(?, ?, ?)',
                                (relevant_address, entry[0], 'ETH'),
                            )
                        string_repr = db_tuple_to_str(entry, tuple_type)
                        log.debug(
                            f'Did not add "{string_repr}" to the DB due to "{str(e)}". '
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

    def add_margin_positions(self, write_cursor: 'DBCursor', margin_positions: List[MarginPosition]) -> None:  # noqa: E501
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
        self.write_tuples(write_cursor=write_cursor, tuple_type='margin_position', query=query, tuples=margin_tuples)  # noqa: E501

    def get_margin_positions(
            self,
            cursor: 'DBCursor',
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[Location] = None,
    ) -> List[MarginPosition]:
        """Returns a list of margin positions optionally filtered by time and location

        The returned list is ordered from oldest to newest
        """
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

    def add_asset_movements(self, write_cursor: 'DBCursor', asset_movements: List[AssetMovement]) -> None:  # noqa: E501
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
              timestamp,
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
        self.write_tuples(write_cursor=write_cursor, tuple_type='asset_movement', query=query, tuples=movement_tuples)  # noqa: E501

    def get_asset_movements_and_limit_info(
            self,
            filter_query: AssetMovementsFilterQuery,
            has_premium: bool,
    ) -> Tuple[List[AssetMovement], int]:
        """Gets all asset movements for the query from the DB

        Also returns how many are the total found for the filter
        """
        with self.conn.read_ctx() as cursor:
            movements = self.get_asset_movements(cursor, filter_query=filter_query, has_premium=has_premium)  # noqa: E501
            query, bindings = filter_query.prepare(with_pagination=False)
            query = 'SELECT COUNT(*) from asset_movements ' + query
            total_found_result = cursor.execute(query, bindings)
            return movements, total_found_result.fetchone()[0]

    def get_asset_movements(
            self,
            cursor: 'DBCursor',
            filter_query: AssetMovementsFilterQuery,
            has_premium: bool,
    ) -> List[AssetMovement]:
        """Returns a list of asset movements optionally filtered by the given filter.

        Returned list is ordered according to the passed filter query
        """
        query, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT * from asset_movements ' + query
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT * FROM (SELECT * from asset_movements ORDER BY timestamp DESC LIMIT ?) ' + query  # noqa: E501
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

    # pylint: disable=no-self-use
    def get_entries_count(
            self,
            cursor: 'DBCursor',
            entries_table: Literal[
                'asset_movements',
                'trades',
                'ethereum_transactions',
                'amm_swaps',
                'combined_trades_view',
                'ledger_actions',
                'eth2_daily_staking_details',
                'entries_notes',
                'user_notes',
            ],
            op: Literal['OR', 'AND'] = 'OR',
            **kwargs: Any,
    ) -> int:
        """Returns how many of a certain type of entry are saved in the DB"""
        cursorstr = f'SELECT COUNT(*) from {entries_table}'
        if len(kwargs) != 0:
            cursorstr += ' WHERE'
        op.join([f' {arg} = "{val}" ' for arg, val in kwargs.items()])
        cursorstr += ';'
        cursor.execute(cursorstr)
        return cursor.fetchone()[0]

    def delete_data_for_ethereum_address(self, write_cursor: 'DBCursor', address: ChecksumEvmAddress) -> None:  # noqa: E501
        """Deletes all ethereum related data from the DB for a single ethereum address"""
        other_eth_accounts = self.get_blockchain_accounts(write_cursor).eth
        if address in other_eth_accounts:
            other_eth_accounts.remove(address)

        write_cursor.execute('DELETE FROM used_query_ranges WHERE name = ?', (f'aave_events_{address}',))  # noqa: E501
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name = ?',
            (f'{ADEX_EVENTS_PREFIX}_{address}',),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name = ?',
            (f'{BALANCER_EVENTS_PREFIX}_{address}',),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name = ?',
            (f'{BALANCER_TRADES_PREFIX}_{address}',),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name = ?',
            (f'{UNISWAP_EVENTS_PREFIX}_{address}',),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name = ?',
            (f'{UNISWAP_TRADES_PREFIX}_{address}',),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name = ?',
            (f'{ETH2_DEPOSITS_PREFIX}_{address}',),
        )
        write_cursor.execute('DELETE FROM ethereum_accounts_details WHERE account = ?', (address,))
        write_cursor.execute('DELETE FROM aave_events WHERE address = ?', (address,))
        write_cursor.execute('DELETE FROM adex_events WHERE address = ?', (address,))
        write_cursor.execute('DELETE FROM balancer_events WHERE address=?;', (address,))
        write_cursor.execute('DELETE FROM amm_events WHERE address=?;', (address,))
        write_cursor.execute(
            'DELETE FROM multisettings WHERE name LIKE "queried_address_%" AND value = ?',
            (address,),
        )
        loopring = DBLoopring(self)
        loopring.remove_accountid_mapping(write_cursor, address)

        dbtx = DBEthTx(self)
        dbtx.delete_transactions(write_cursor, address)
        write_cursor.execute('DELETE FROM amm_swaps WHERE address=?;', (address,))
        write_cursor.execute('DELETE FROM eth2_deposits WHERE from_address=?;', (address,))

    def add_trades(self, write_cursor: 'DBCursor', trades: List[Trade]) -> None:
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
              timestamp,
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
        self.write_tuples(write_cursor=write_cursor, tuple_type='trade', query=query, tuples=trade_tuples)  # noqa: E501

    def edit_trade(
            self,
            write_cursor: 'DBCursor',
            old_trade_id: str,
            trade: Trade,
    ) -> Tuple[bool, str]:
        write_cursor.execute(
            'UPDATE trades SET '
            '  id=?, '
            '  timestamp=?,'
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
        if write_cursor.rowcount == 0:
            return False, 'Tried to edit non existing trade id'

        return True, ''

    def get_trades_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: TradesFilterQuery,
            has_premium: bool,
    ) -> Tuple[List[Trade], int]:
        """Gets all trades for the query from the DB

        Also returns how many are the total found for the filter
        """
        trades = self.get_trades(cursor, filter_query=filter_query, has_premium=has_premium)
        table_name = 'combined_trades_view' if has_premium else 'trades'
        query, bindings = filter_query.prepare(with_pagination=False)
        query = f'SELECT COUNT(*) from {table_name} ' + query
        total_found_result = cursor.execute(query, bindings)
        return trades, total_found_result.fetchone()[0]

    def get_trades(self, cursor: 'DBCursor', filter_query: TradesFilterQuery, has_premium: bool) -> List[Trade]:  # noqa: E501
        """Returns a list of trades optionally filtered by various filters.

        This will also take into account AMMSwaps and return them as trades via a view.

        The returned list is ordered according to the passed filter query"""
        query, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT * from combined_trades_view ' + query
            results = cursor.execute(query, bindings)
        else:
            query = 'SELECT * FROM (SELECT * from trades ORDER BY timestamp DESC LIMIT ?) ' + query  # noqa: E501
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

    def delete_trade(self, write_cursor: 'DBCursor', trade_id: str) -> Tuple[bool, str]:
        write_cursor.execute('DELETE FROM trades WHERE id=?', (trade_id,))
        if write_cursor.rowcount == 0:
            return False, 'Tried to delete non-existing trade'
        return True, ''

    def add_amm_swaps(self, write_cursor: 'DBCursor', swaps: List[AMMSwap]) -> None:
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
        self.write_tuples(write_cursor, tuple_type='amm_swap', query=query, tuples=swap_tuples)

    def get_amm_swaps(
            self,
            cursor: 'DBCursor',
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[Location] = None,
            address: Optional[ChecksumEvmAddress] = None,
    ) -> List[AMMSwap]:
        """Returns a list of AMM swaps optionally filtered by time, location
        and address
        """
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
        cursor.close()
        # Do not update the last write here. If we are starting in a new machine
        # then this write is mandatory and to sync with data from server we need
        # an empty last write ts in that case

    def delete_premium_credentials(self) -> bool:
        """Delete the rotki premium credentials in the DB for the logged-in user"""
        with self.user_write() as cursor:
            try:
                cursor.execute(
                    'DELETE FROM user_credentials WHERE name=?', ('rotkehlchen',),
                )
            except sqlcipher.OperationalError as e:  # pylint: disable=no-member
                log.error(f'Could not delete rotki premium credentials: {str(e)}')
                return False
        return True

    def get_rotkehlchen_premium(self, cursor: 'DBCursor') -> Optional[PremiumCredentials]:
        cursor.execute(
            'SELECT api_key, api_secret FROM user_credentials where name="rotkehlchen";',
        )
        result = cursor.fetchone()
        if result is None:
            return None

        try:
            credentials = PremiumCredentials(
                given_api_key=result[0],
                given_api_secret=result[1],
            )
        except IncorrectApiKeyFormat:
            self.msg_aggregator.add_error(
                'Incorrect rotki API Key/Secret format found in the DB. Skipping ...',
            )
            return None

        return credentials

    def get_netvalue_data(
            self,
            from_ts: Timestamp,
            include_nfts: bool = True,
    ) -> Tuple[List[str], List[str]]:
        """Get all entries of net value data from the DB"""
        with self.conn.read_ctx() as cursor:
            # Get the total location ("H") entries in ascending time
            cursor.execute(
                'SELECT timestamp, usd_value FROM timed_location_data '
                'WHERE location="H" AND timestamp >= ? ORDER BY timestamp ASC;',
                (from_ts,),
            )
            if not include_nfts:
                with self.conn.read_ctx() as nft_cursor:
                    nft_cursor.execute(
                        'SELECT timestamp, SUM(usd_value) FROM timed_balances WHERE '
                        'timestamp >= ? AND currency LIKE ? GROUP BY timestamp',
                        (from_ts, f'{NFT_DIRECTIVE}%'),
                    )
                    nft_values = {time: value for time, value in nft_cursor}

            data = []
            times_int = []
            for entry in cursor:
                times_int.append(entry[0])
                if include_nfts:
                    total = entry[1]
                else:
                    total = str(FVal(entry[1]) - FVal(nft_values.get(entry[0], 0)))
                data.append(total)
        return times_int, data

    def query_timed_balances(
            self,
            cursor: 'DBCursor',
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

        settings = self.get_settings(cursor)
        querystr = (
            'SELECT timestamp, amount, usd_value, category FROM timed_balances '
            'WHERE timestamp BETWEEN ? AND ? AND currency=?'
        )
        bindings = [from_ts, to_ts, asset.identifier]

        if settings.treat_eth2_as_eth and asset.identifier == 'ETH':
            assert balance_type is not None, 'Asset balances and liabilities can\'t be queried at the same time when eth2 is equivalent to eth'  # noqa: E501
            querystr = querystr.replace('currency=?', 'currency IN (?,?)')
            bindings.append('ETH2')

        if balance_type is not None:
            querystr += ' AND category=?'
            bindings.append(balance_type.serialize_for_db())
        querystr += ' ORDER BY timestamp ASC;'

        cursor.execute(querystr, bindings)
        results = cursor.fetchall()
        balances = []
        results_length = len(results)
        for idx, result in enumerate(results):
            entry_time = result[0]
            category = BalanceType.deserialize_from_db(result[3])
            balances.append(
                SingleDBAssetBalance(
                    time=entry_time,
                    amount=FVal(result[1]),
                    usd_value=FVal(result[2]),
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
                        amount=ZERO,
                        usd_value=ZERO,
                        category=category,
                    ),
                )

        if settings.treat_eth2_as_eth and asset.identifier == 'ETH':
            return combine_asset_balances(balances)

        return balances

    def query_owned_assets(self, cursor: 'DBCursor') -> List[Asset]:
        """Query the DB for a list of all assets ever owned

        The assets are taken from:
        - Balance snapshots
        - Trades the user made
        - Manual balances
        """
        # TODO: Perhaps also add amm swaps here
        # but think on the performance. This is a synchronous api call so if
        # it starts taking too much time the calling logic needs to change
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
                cursor.execute(
                    f'SELECT DISTINCT {columns_str} FROM {table_name} {condition};',
                    bindings,
                )
            except sqlcipher.OperationalError as e:    # pylint: disable=no-member
                log.error(f'Could not fetch assets from table {table_name}. {str(e)}')
                continue

            for result in cursor:
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

    def update_owned_assets_in_globaldb(self, cursor: 'DBCursor') -> None:
        """Makes sure all owned assets of the user are in the Global DB"""
        assets = self.query_owned_assets(cursor)
        GlobalDBHandler().add_user_owned_assets(assets)

    # pylint: disable=no-self-use
    def add_asset_identifiers(self, write_cursor: 'DBCursor', asset_identifiers: List[str]) -> None:  # noqa: E501
        """Adds an asset to the user db asset identifier table"""
        write_cursor.executemany(
            'INSERT OR IGNORE INTO assets(identifier) VALUES(?);',
            [(x,) for x in asset_identifiers],
        )

    def add_globaldb_assetids(self, write_cursor: 'DBCursor') -> None:
        """Makes sure that all the GlobalDB asset identifiers are mirrored in the user DB"""
        cursor = GlobalDBHandler().conn.cursor()  # after succesfull update add all asset ids
        query = cursor.execute('SELECT identifier from assets;')
        self.add_asset_identifiers(write_cursor, [x[0] for x in query])

    def delete_asset_identifier(self, write_cursor: 'DBCursor', asset_id: str) -> None:
        """Deletes an asset identifier from the user db asset identifier table

        May raise:
        - InputError if a foreign key error is encountered during deletion
        """
        try:
            write_cursor.execute(
                'DELETE FROM assets WHERE identifier=?;',
                (asset_id,),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Failed to delete asset with id {asset_id} from the DB since '
                f'the user owns it now or did some time in the past',
            ) from e

    def replace_asset_identifier(self, source_identifier: str, target_asset: Asset) -> None:
        """Replaces a given source identifier either both in the global or the local
        user DB with another given asset.

        May raise:
        - UnknownAsset if the source_identifier can be found nowhere
        - InputError if it's not possible to perform the replacement for some reason
        """
        globaldb = GlobalDBHandler()
        globaldb_data = globaldb.get_asset_data(identifier=source_identifier, form_with_incomplete_data=True)  # noqa: E501

        with self.conn.read_ctx() as cursor:
            userdb_query = cursor.execute(
                'SELECT COUNT(*) FROM assets WHERE identifier=?;', (source_identifier,),
            ).fetchone()[0]

        if userdb_query == 0 and globaldb_data is None:
            raise UnknownAsset(source_identifier)

        if globaldb_data is not None:
            globaldb.delete_asset_by_identifer(source_identifier, globaldb_data.asset_type)

        if userdb_query != 0:
            with self.user_write() as write_cursor:
                # the tricky part here is that we need to disable foreign keys for this
                # approach and disabling foreign keys needs a commit. So rollback is impossible.
                # But there is no way this can fail. (famous last words)
                write_cursor.executescript('PRAGMA foreign_keys = OFF;')
                write_cursor.execute(
                    'DELETE from assets WHERE identifier=?;',
                    (target_asset.identifier,),
                )
                write_cursor.executescript('PRAGMA foreign_keys = ON;')
                write_cursor.execute(
                    'UPDATE assets SET identifier=? WHERE identifier=?;',
                    (target_asset.identifier, source_identifier),
                )

    def get_latest_location_value_distribution(self) -> List[LocationData]:
        """Gets the latest location data

        Returns a list of `LocationData` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all locations
        """
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT timestamp, location, usd_value FROM timed_location_data WHERE '
                'timestamp=(SELECT MAX(timestamp) FROM timed_location_data) AND usd_value!=0;',
            )
            locations = []
            for result in cursor:
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
        with self.conn.read_ctx() as cursor:
            ignored_assets = self.get_ignored_assets(cursor)
            treat_eth2_as_eth = self.get_settings(cursor).treat_eth2_as_eth
            cursor.execute(
                'SELECT timestamp, currency, amount, usd_value, category FROM timed_balances '
                'WHERE timestamp=(SELECT MAX(timestamp) from timed_balances) AND category = ? '
                'ORDER BY CAST(usd_value AS REAL) DESC;',
                (BalanceType.ASSET.serialize_for_db(),),  # pylint: disable=no-member
            )
            asset_balances = []
            eth_balance = DBAssetBalance(
                time=Timestamp(0),
                category=BalanceType.ASSET,
                asset=A_ETH,
                amount=ZERO,
                usd_value=ZERO,
            )
            for result in cursor:
                asset = Asset(result[1])
                time = Timestamp(result[0])
                amount = FVal(result[2])
                usd_value = FVal(result[3])
                if asset in ignored_assets:
                    continue
                # show eth & eth2 as eth in value distribution by asset
                if treat_eth2_as_eth is True and asset in (A_ETH, A_ETH2):
                    eth_balance.time = time
                    eth_balance.amount = eth_balance.amount + amount
                    eth_balance.usd_value = eth_balance.usd_value + usd_value
                else:
                    asset_balances.append(
                        DBAssetBalance(
                            time=time,
                            asset=asset,
                            amount=amount,
                            usd_value=usd_value,
                            category=BalanceType.deserialize_from_db(result[4]),
                        ),
                    )
            # only add the eth_balance if it contains a balance > 0
            if eth_balance.amount > ZERO:
                # respect descending order `usd_value`
                for index, balance in enumerate(asset_balances):
                    if eth_balance.usd_value > balance.usd_value:
                        asset_balances.insert(index, eth_balance)
                        break
                else:
                    asset_balances.append(eth_balance)
        return asset_balances

    def get_tags(self, cursor: 'DBCursor') -> Dict[str, Tag]:
        tags_mapping: Dict[str, Tag] = {}
        cursor.execute(
            'SELECT name, description, background_color, foreground_color FROM tags;',
        )
        for result in cursor:
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
            write_cursor: 'DBCursor',
            name: str,
            description: Optional[str],
            background_color: HexColorCode,
            foreground_color: HexColorCode,
    ) -> None:
        """Adds a new tag to the DB

        Raises:
        - TagConstraintError: If the tag with the given name already exists
        """
        try:
            write_cursor.execute(
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

    def edit_tag(
            self,
            write_cursor: 'DBCursor',
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
        write_cursor.execute(querystr, query_values)
        if write_cursor.rowcount < 1:
            raise TagConstraintError(
                f'Tried to edit tag with name "{name}" which does not exist',
            )

    def delete_tag(self, write_cursor: 'DBCursor', name: str) -> None:
        """Deletes a tag already existing in the DB

        Raises:
        - TagConstraintError: If the tag name to delete does not exist in the DB
        """
        # Delete the tag mappings for all affected accounts
        write_cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'tag_name = ?;', (name,),
        )
        write_cursor.execute('DELETE from tags WHERE name = ?;', (name,))
        if write_cursor.rowcount < 1:
            raise TagConstraintError(
                f'Tried to delete tag with name "{name}" which does not exist',
            )

    def ensure_tags_exist(
            self,
            cursor: 'DBCursor',
            given_data: Union[
                List[BlockchainAccountData],
                List[ManuallyTrackedBalance],
                List[XpubData],
            ],
            action: Literal['adding', 'editing'],
            data_type: Literal['blockchain accounts', 'manually tracked balances', 'bitcoin xpub', 'bitcoin cash xpub'],  # noqa: 501
    ) -> None:
        """Make sure that tags included in the data exist in the DB

        May Raise:
        - TagConstraintError if the tags don't exist in the DB
        """
        existing_tags = self.get_tags(cursor)
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

    def add_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """Add the xpub to the DB

        May raise:
        - InputError if the xpub data already exist
        """
        try:
            write_cursor.execute(
                'INSERT INTO xpubs(xpub, derivation_path, label, blockchain) '
                'VALUES (?, ?, ?, ?)',
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    xpub_data.label,
                    blockchain.value,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Xpub {xpub_data.xpub.xpub} for {blockchain.value} with derivation path '
                f'{xpub_data.derivation_path} is already tracked',
            ) from e

    def delete_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """Deletes an xpub from the DB. Also deletes all derived addresses and mappings

        May raise:
        - InputError if the xpub does not exist in the DB
        """
        write_cursor.execute(
            'SELECT COUNT(*) FROM xpubs WHERE xpub=? AND derivation_path IS ? AND blockchain=?;',
            (xpub_data.xpub.xpub, xpub_data.serialize_derivation_path_for_db(), blockchain.value),
        )
        if write_cursor.fetchone()[0] == 0:
            derivation_str = (
                'no derivation path' if xpub_data.derivation_path is None else
                f'derivation path {xpub_data.derivation_path}'
            )
            raise InputError(
                f'Tried to remove non existing xpub {xpub_data.xpub.xpub} for {blockchain.value} '
                f'with {derivation_str}',
            )

        # Delete the tag mappings for all derived addresses
        write_cursor.execute(
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
        write_cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
        # Delete any derived addresses
        write_cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=? AND account IN ('
            'SELECT address from xpub_mappings WHERE xpub=? and derivation_path IS ?);',
            (
                blockchain.value,
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
            ),
        )
        # And then finally delete the xpub itself
        write_cursor.execute(
            'DELETE FROM xpubs WHERE xpub=? AND derivation_path IS ?;',
            (xpub_data.xpub.xpub, xpub_data.serialize_derivation_path_for_db()),
        )

    def edit_bitcoin_xpub(self, write_cursor: 'DBCursor', xpub_data: XpubData) -> None:
        """Edit the xpub tags and label

        May raise:
        - InputError if the xpub data already exist
        """
        try:
            key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore # noqa: E501
            # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None)
            write_cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
            insert_tag_mappings(
                # if we got tags add them to the xpub
                write_cursor=write_cursor,
                data=[xpub_data],
                object_reference_keys=['xpub.xpub', 'derivation_path'],
            )
            write_cursor.execute(
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

    def get_bitcoin_xpub_data(self, cursor: 'DBCursor') -> List[XpubData]:
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

    def get_last_consecutive_xpub_derived_indices(self, cursor: 'DBCursor', xpub_data: XpubData) -> Tuple[int, int]:  # noqa: E501
        """
        Get the last known receiving and change derived indices from the given
        xpub that are consecutive since the beginning.

        For example if we have derived indices 0, 1, 4, 5 then this will return 1.

        This tells us from where to start deriving again safely
        """
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
            cursor: 'DBCursor',
            addresses: List[BTCAddress],
    ) -> Dict[BTCAddress, XpubData]:
        data = {}
        for address in addresses:
            cursor.execute(
                'SELECT B.address, A.xpub, A.derivation_path FROM xpubs as A '
                'LEFT OUTER JOIN xpub_mappings as B '
                'ON B.xpub = A.xpub AND B.derivation_path IS A.derivation_path '
                'WHERE B.address=?;', (address,),
            )
            result = cursor.fetchall()
            if len(result) == 0:
                continue

            data[result[0][0]] = XpubData(
                xpub=HDKey.from_xpub(result[0][1], path='m'),
                derivation_path=deserialize_derivation_path_for_db(result[0][2]),
            )

        return data

    def ensure_xpub_mappings_exist(
            self,
            write_cursor: 'DBCursor',
            xpub: str,
            derivation_path: Optional[str],
            derived_addresses_data: List[XpubDerivedAddressData],
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """Create if not existing the mappings between the addresses and the xpub"""
        tuples = [
            (
                x.address,
                xpub,
                '' if derivation_path is None else derivation_path,
                x.account_index,
                x.derived_index,
                blockchain.value,
            ) for x in derived_addresses_data
        ]
        for entry in tuples:
            try:
                write_cursor.execute(
                    'INSERT INTO xpub_mappings'
                    '(address, xpub, derivation_path, account_index, derived_index, blockchain) '
                    'VALUES (?, ?, ?, ?, ?, ?)',
                    entry,
                )
            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                # mapping already exists
                continue

    def _ensure_data_integrity(
            self,
            cursor: 'DBCursor',
            table_name: str,
            klass: Union[Type[Trade], Type[AssetMovement], Type[MarginPosition]],
    ) -> None:
        updates: List[Tuple[str, str]] = []
        log.debug(f'db integrity: start {table_name}')
        cursor.execute(f'SELECT * from {table_name};')
        for result in cursor:
            try:
                obj = klass.deserialize_from_db(result)
            except (DeserializationError, UnknownAsset):
                continue

            db_id = result[0]
            actual_id = obj.identifier
            if actual_id != db_id:
                updates.append((actual_id, db_id))

        log.debug(f'db integrity: check updates {table_name}')
        if len(updates) != 0:
            log.debug(
                f'Found {len(updates)} identifier discrepancies in the DB '
                f'for {table_name}. Correcting...',
            )
            with self.user_write() as write_cursor:
                write_cursor.executemany(f'UPDATE {table_name} SET id = ? WHERE id =?;', updates)
        log.debug(f'db integrity: end {table_name}')

    def ensure_data_integrity(self) -> None:
        """Runs some checks for data integrity of the DB that can't be verified by SQLite

        For now it mostly tackles https://github.com/rotki/rotki/issues/3010 ,
        the problem of identifiers of trades, asset movements and margin positions
        changing and no longer corresponding to the calculated id.
        """
        start_time = ts_now()
        log.debug('Starting DB data integrity check')
        with self.conn.read_ctx() as cursor:
            self._ensure_data_integrity(cursor, 'trades', Trade)
            self._ensure_data_integrity(cursor, 'asset_movements', AssetMovement)
            self._ensure_data_integrity(cursor, 'margin_positions', MarginPosition)
        log.debug(f'DB data integrity check finished after {ts_now() - start_time} seconds')

    def get_db_info(self, cursor: 'DBCursor') -> Dict[str, Any]:
        filepath = self.user_data_dir / 'rotkehlchen.db'
        size = Path(self.user_data_dir / 'rotkehlchen.db').stat().st_size
        version = self.get_setting(cursor, 'version')
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
        with self.conn.read_ctx() as cursor:
            version = self.get_setting(cursor, 'version')
        new_db_filename = f'{ts_now()}_rotkehlchen_db_v{version}.backup'
        new_db_path = self.user_data_dir / new_db_filename
        shutil.copyfile(
            self.user_data_dir / 'rotkehlchen.db',
            new_db_path,
        )
        return new_db_path

    def get_associated_locations(self) -> Set[Location]:
        with self.conn.read_ctx() as cursor:
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
            if cursor.fetchone()[0] >= 1:  # should always return number
                locations.add(Location.BALANCER)
        return locations

    def should_save_balances(self, cursor: 'DBCursor') -> bool:
        """
        Returns whether or not we can save data to the database depending on
        the balance data saving frequency setting
        """
        last_save = self.get_last_balance_save_time(cursor)
        settings = self.get_settings(cursor)
        # Setting is saved in hours, convert to seconds here
        period = settings.balance_save_frequency * 60 * 60
        now = ts_now()
        return now - last_save > period

    def get_web3_nodes(self, only_active: bool = False) -> List[WeightedNode]:
        """
        Get all the nodes in the database. If only_active is set to true only the nodes that
        have the column active set to True will be returned.
        """
        with self.conn.read_ctx() as cursor:
            if only_active:
                cursor.execute('SELECT identifier, name, endpoint, owned, weight, active FROM web3_nodes WHERE active=1 AND CAST(weight as decimal) != 0;')  # noqa: E501
            else:
                cursor.execute(
                    'SELECT identifier, name, endpoint, owned, weight, active FROM web3_nodes;',
                )
            return [
                WeightedNode(
                    identifier=entry[0],
                    node_info=NodeName(
                        name=entry[1],
                        endpoint=entry[2],
                        owned=bool(entry[3]),
                    ),
                    weight=FVal(entry[4]),
                    active=bool(entry[5]),
                )
                for entry in cursor
            ]

    def _rebalance_web3_nodes_weights(
            self,
            write_cursor: 'DBCursor',
            proportion_to_share: FVal,
            exclude_identifier: Optional[int],
    ) -> None:
        """
        Weights for nodes have to be in the range between 0 and 1. This function adjusts the
        weights of all other nodes to keep the proportions correct. After setting a node weight
        to X, the `proportion_to_share` between all remaining nodes becomes `1 - X`.
        exclude_identifier is the identifier of the node whose weight we add or edit.
        In case of deletion it's omitted and `None`is passed.
        """
        if exclude_identifier is None:
            write_cursor.execute('SELECT identifier, weight FROM web3_nodes WHERE owned=0')
        else:
            write_cursor.execute(
                'SELECT identifier, weight FROM web3_nodes WHERE identifier != ? AND owned=0',
                (exclude_identifier,),
            )
        new_weights = []
        nodes_weights = write_cursor.fetchall()
        weight_sum = sum(FVal(node[1]) for node in nodes_weights)
        for node_id, weight in nodes_weights:
            if exclude_identifier:
                new_weights.append((str(FVal(weight) / weight_sum * proportion_to_share), node_id))
            else:
                new_weights.append((str(FVal(weight) / weight_sum), node_id))
        write_cursor.executemany(
            'UPDATE web3_nodes SET weight=? WHERE identifier=?',
            new_weights,
        )

    def add_web3_node(self, node: WeightedNode) -> None:
        with self.user_write() as cursor:
            try:
                cursor.execute(
                    'INSERT INTO web3_nodes(name, endpoint, owned, active, weight) VALUES (?, ?, ?, ?, ?)',   # noqa: E501
                    node.serialize_for_db(),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(f'Node with name {node.node_info.name} already exists in db') from e  # noqa: E501
            self._rebalance_web3_nodes_weights(
                write_cursor=cursor,
                proportion_to_share=ONE - node.weight,
                exclude_identifier=cursor.lastrowid,
            )

    def update_web3_node(self, node: WeightedNode) -> None:
        with self.conn.read_ctx() as cursor:
            cursor.execute('SELECT COUNT(*) FROM web3_nodes WHERE name=?', (node.node_info.name,))
            if cursor.fetchone() != (1,):
                raise InputError(f'Node with name {node.node_info.name} doesn\'t exist')
        with self.user_write() as cursor:
            cursor.execute(
                'UPDATE web3_nodes SET name=?, endpoint=?, owned=?, active=?, weight=? WHERE identifier=?',  # noqa: E501
                (
                    node.node_info.name,
                    node.node_info.endpoint,
                    node.node_info.owned,
                    node.active,
                    str(node.weight),
                    node.identifier,
                ),
            )
            self._rebalance_web3_nodes_weights(
                write_cursor=cursor,
                proportion_to_share=ONE - node.weight,
                exclude_identifier=node.identifier,
            )

    def delete_web3_node(self, identifier: int) -> None:
        """Delete a web3 node based on name.
        May raise:
        - InputError if no entry with such name is in the database.
        """
        with self.user_write() as cursor:
            cursor.execute('DELETE FROM web3_nodes WHERE identifier=?', (identifier,))
            if cursor.rowcount == 0:
                raise InputError(f'node with name {identifier} was not found in the database')
            self._rebalance_web3_nodes_weights(
                write_cursor=cursor,
                proportion_to_share=ONE,
                exclude_identifier=None,
            )

    def get_user_notes(
            self,
            filter_query: UserNotesFilterQuery,
            cursor: 'DBCursor',
            has_premium: bool,
    ) -> List[UserNote]:
        """Returns all the notes created by a user filtered by the given filter"""
        query, bindings = filter_query.prepare()
        if has_premium:
            query = 'SELECT identifier, title, content, location, last_update_timestamp, is_pinned FROM user_notes ' + query  # noqa: E501
            cursor.execute(query, bindings)
        else:
            query = 'SELECT identifier, title, content, location, last_update_timestamp, is_pinned FROM (SELECT identifier, title, content, location, last_update_timestamp, is_pinned from user_notes ORDER BY last_update_timestamp DESC LIMIT ?) ' + query  # noqa: E501
            cursor.execute(query, [FREE_USER_NOTES_LIMIT] + bindings)

        return [UserNote.deserialize_from_db(entry) for entry in cursor]

    def get_user_notes_and_limit_info(
            self,
            filter_query: UserNotesFilterQuery,
            cursor: 'DBCursor',
            has_premium: bool,
    ) -> Tuple[List[UserNote], int]:
        """Gets all user_notes for the query from the DB

        Also returns how many are the total found for the filter
        """
        user_notes = self.get_user_notes(filter_query=filter_query, cursor=cursor, has_premium=has_premium)  # noqa: E501
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from user_notes ' + query
        total_found_result = cursor.execute(query, bindings)
        return user_notes, total_found_result.fetchone()[0]

    def add_user_note(
            self,
            title: str,
            content: str,
            location: str,
            is_pinned: bool,
            has_premium: bool,
    ) -> int:
        """Add a user_note entry to the DB"""
        with self.user_write() as write_cursor:
            if has_premium is False:
                num_user_notes = self.get_entries_count(
                    cursor=write_cursor,
                    entries_table='user_notes',
                )
                if num_user_notes >= FREE_USER_NOTES_LIMIT:
                    msg = (
                        f'The limit of {FREE_USER_NOTES_LIMIT} user notes has been '
                        f'reached in the free plan. To get more notes you can upgrade to '
                        f'premium: https://rotki.com/products'
                    )
                    raise InputError(msg)

            write_cursor.execute(
                'INSERT INTO user_notes(title, content, location, last_update_timestamp, is_pinned) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
                (title, content, location, ts_now(), is_pinned),
            )
            return write_cursor.lastrowid

    def edit_user_note(self, user_note: UserNote) -> None:
        """Edit an already existing user_note entry's content.
        May raise:
        - InputError if editing a user note that does not exist.
        """
        with self.user_write() as write_cursor:
            write_cursor.execute(
                'UPDATE user_notes SET title=?, content=?, last_update_timestamp=?, is_pinned=? WHERE identifier=?',  # noqa: E501
                (
                    user_note.title,
                    user_note.content,
                    ts_now(),
                    user_note.is_pinned,
                    user_note.identifier,
                ),
            )
            if write_cursor.rowcount == 0:
                raise InputError(f'User note with identifier {user_note.identifier} does not exist')  # noqa: E501

    def delete_user_note(self, identifier: int) -> None:
        """Delete user note entry from the DB.
        May raise:
        - InputError if identifier not present in DB.
        """
        with self.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM user_notes WHERE identifier=?', (identifier,))
            if write_cursor.rowcount == 0:
                raise InputError(f'User note with identifier {identifier} not found in database')
