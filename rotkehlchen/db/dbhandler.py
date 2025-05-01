import json
import logging
import os
import re
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, Literal, Optional, Unpack, cast, overload

from gevent.lock import Semaphore
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import (
    BlockchainAccountData,
    BlockchainAccounts,
    SingleBlockchainAccountData,
)
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.chain.bitcoin.xpub import (
    XpubData,
    XpubDerivedAddressData,
    deserialize_derivation_path_for_db,
)
from rotkehlchen.chain.ethereum.constants import ETHEREUM_ETHERSCAN_NODE_NAME
from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2, A_USD
from rotkehlchen.constants.limits import FREE_USER_NOTES_LIMIT
from rotkehlchen.constants.misc import NFT_DIRECTIVE, USERDB_NAME
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.cache import (
    AddressArgType,
    BinancePairLastTradeArgsType,
    DBCacheDynamic,
    DBCacheStatic,
    ExtraTxArgType,
    IndexArgType,
    LabeledLocationArgsType,
    LabeledLocationIdArgsType,
)
from rotkehlchen.db.constants import (
    BINANCE_MARKETS_KEY,
    EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS,
    EVM_ACCOUNTS_DETAILS_TOKENS,
    EXTRAINTERNALTXPREFIX,
    KRAKEN_ACCOUNT_TYPE_KEY,
    USER_CREDENTIAL_MAPPING_KEYS,
)
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType, DBCursor
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import UserNotesFilterQuery
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.db.misc import detect_sqlcipher_version
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.schema_transient import DB_SCRIPT_CREATE_TRANSIENT_TABLES
from rotkehlchen.db.settings import (
    DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY,
    DEFAULT_LAST_DATA_MIGRATION,
    DEFAULT_PREMIUM_SHOULD_SYNC,
    ROTKEHLCHEN_DB_VERSION,
    ROTKEHLCHEN_TRANSIENT_DB_VERSION,
    CachedSettings,
    DBSettings,
    ModifiableDBSettings,
    db_settings_from_dict,
    serialize_db_setting,
)
from rotkehlchen.db.upgrade_manager import DBUpgradeManager
from rotkehlchen.db.utils import (
    DBAssetBalance,
    DBTupleType,
    LocationData,
    SingleDBAssetBalance,
    Tag,
    combine_asset_balances,
    db_tuple_to_str,
    deserialize_tags_from_db,
    form_query_to_filter_timestamps,
    insert_tag_mappings,
    is_valid_db_blockchain_account,
    protect_password_sqlcipher,
    replace_tag_mappings,
    str_to_bool,
)
from rotkehlchen.errors.api import (
    AuthenticationError,
    IncorrectApiKeyFormat,
    RotkehlchenPermissionError,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import (
    DBUpgradeError,
    InputError,
    SystemPermissionError,
    TagConstraintError,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.serialization.deserialize import deserialize_hex_color_code, deserialize_timestamp
from rotkehlchen.types import (
    ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE,
    EVM_CHAINS_WITH_TRANSACTIONS,
    SPAM_PROTOCOL,
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_EVM_CHAINS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_EVMLIKE_CHAINS,
    SUPPORTED_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_SUBSTRATE_CHAINS,
    AnyBlockchainAddress,
    ApiKey,
    ApiSecret,
    BTCAddress,
    ChecksumEvmAddress,
    ExchangeApiCredentials,
    ExchangeLocationID,
    ExternalService,
    ExternalServiceApiCredentials,
    HexColorCode,
    ListOfBlockchainAddresses,
    Location,
    PurgeableModuleName,
    SupportedBlockchain,
    Timestamp,
    UserNote,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.hashing import file_md5
from rotkehlchen.utils.misc import get_chunks, ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

KDF_ITER = 64000
DBINFO_FILENAME = 'dbinfo.json'
TRANSIENT_DB_NAME = 'rotkehlchen_transient.db'


# Tuples that contain first the name of a table and then the columns that
# reference assets ids. This is used to query all assets that a user has ever owned.
TABLES_WITH_ASSETS = (
    ('manually_tracked_balances', 'asset'),
    ('margin_positions', 'pl_currency', 'fee_currency'),
    ('timed_balances', 'currency'),
    ('history_events', 'asset'),
)


DB_BACKUP_RE = re.compile(r'(\d+)_rotkehlchen_db_v(\d+).backup')


# https://stackoverflow.com/questions/4814167/storing-time-series-data-relational-or-non
# http://www.sql-join.com/sql-join-types


class DBHandler:
    def __init__(
            self,
            user_data_dir: Path,
            password: str,
            msg_aggregator: MessagesAggregator,
            initial_settings: ModifiableDBSettings | None,
            sql_vm_instructions_cb: int,
            resume_from_backup: bool,
    ):
        """Database constructor

        May raise:
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported or if db is in a half-upgraded state and there is no backup.
        - AuthenticationError if SQLCipher version problems are detected
        - SystemPermissionError if the DB file's permissions are not correct
        - DBSchemaError if database schema is malformed
        """
        self.msg_aggregator = msg_aggregator
        self.user_data_dir = user_data_dir
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        self.sqlcipher_version = detect_sqlcipher_version()
        self.setting_to_default_type = {
            'version': (int, ROTKEHLCHEN_DB_VERSION),
            'last_write_ts': (int, Timestamp(0)),
            'premium_should_sync': (str_to_bool, DEFAULT_PREMIUM_SHOULD_SYNC),
            'main_currency': (lambda x: Asset(x).resolve(), A_USD.resolve_to_fiat_asset()),
            'ongoing_upgrade_from_version': (int, None),
            'last_data_migration': (int, DEFAULT_LAST_DATA_MIGRATION),
            'non_syncing_exchanges': (lambda data: [ExchangeLocationID.deserialize(x) for x in json.loads(data)], []),  # noqa: E501
            'beacon_rpc_endpoint': (str, None),
            'ask_user_upon_size_discrepancy': (str_to_bool, DEFAULT_ASK_USER_UPON_SIZE_DISCREPANCY),  # noqa: E501
        }
        self.conn: DBConnection = None  # type: ignore
        self.conn_transient: DBConnection = None  # type: ignore
        # Lock to make sure that 2 callers of get_or_create_evm_token do not go in at the same time
        self.get_or_create_evm_token_lock = Semaphore()
        self.password = password
        self._connect()
        self._check_unfinished_upgrades(resume_from_backup=resume_from_backup)
        self._run_actions_after_first_connection()
        with self.user_write() as cursor:
            if initial_settings is not None:
                self.set_settings(cursor, initial_settings)
            self.update_owned_assets_in_globaldb(cursor)
            self.sync_globaldb_assets(cursor)

    def _check_unfinished_upgrades(self, resume_from_backup: bool) -> None:
        """
        Checks the database whether there are any not finished upgrades and automatically uses a
        backup if there are any. If no backup found, throws an error to the user
        """
        with self.conn.read_ctx() as cursor:
            try:
                ongoing_upgrade_from_version = self.get_setting(
                    cursor=cursor,
                    name='ongoing_upgrade_from_version',
                )
            except sqlcipher.OperationalError:  # pylint: disable=no-member
                return  # fresh database. Nothing to upgrade.
        if ongoing_upgrade_from_version is None:
            return  # We are all good

        # if there is an unfinished upgrade, check user approval to resume from backup
        if resume_from_backup is False:
            raise RotkehlchenPermissionError(
                error_message=(
                    'The encrypted database is in a semi upgraded state. '
                    'Either resume from a backup or solve the issue manually.'
                ),
                payload=None,
            )

        # If resume_from_backup is True, the user gave approval.
        # Replace the db with a backup and reconnect
        self.disconnect()
        backup_postfix = f'rotkehlchen_db_v{ongoing_upgrade_from_version}.backup'
        found_backups = list(filter(
            lambda x: x[-len(backup_postfix):] == backup_postfix,
            os.listdir(self.user_data_dir),
        ))
        if len(found_backups) == 0:
            raise DBUpgradeError(
                f'Your encrypted database is in a half-upgraded state at '
                f'v{ongoing_upgrade_from_version} and there was no backup '
                'found. Please open an issue on our github or contact us in our discord server.',
            )

        backup_to_use = max(found_backups)  # Use latest backup
        shutil.copyfile(
            self.user_data_dir / backup_to_use,
            self.user_data_dir / USERDB_NAME,
        )
        self.msg_aggregator.add_warning(
            f'Your encrypted database was in a half-upgraded state. '
            f'Trying to login with a backup {backup_to_use}',
        )
        self._connect()

    def logout(self) -> None:
        self.password = ''
        if self.conn is not None:
            self.disconnect(conn_attribute='conn')
        if self.conn_transient is not None:
            self.disconnect(conn_attribute='conn_transient')
        try:
            dbinfo = {'sqlcipher_version': self.sqlcipher_version, 'md5_hash': self.get_md5hash()}
        except (SystemPermissionError, FileNotFoundError) as e:
            # If there is problems opening the DB at destruction just log and exit
            log.error(f'At DB teardown could not open the DB: {e!s}')
            return

        Path(self.user_data_dir / DBINFO_FILENAME).write_text(rlk_jsondumps(dbinfo), encoding='utf8')  # noqa: E501

    def _check_settings(self) -> None:
        """Check that the non_syncing_exchanges setting only has active locations."""
        with self.conn.read_ctx() as cursor:
            non_syncing_exchanges = self.get_setting(
                cursor=cursor,
                name='non_syncing_exchanges',
            )

        valid_locations = [
            exchange_location_id
            for exchange_location_id in non_syncing_exchanges
            if exchange_location_id.location in SUPPORTED_EXCHANGES
        ]
        if len(valid_locations) != len(non_syncing_exchanges):
            with self.user_write() as write_cursor:
                self.set_setting(
                    write_cursor=write_cursor,
                    name='non_syncing_exchanges',
                    value=serialize_db_setting(
                        value=valid_locations,
                        setting='non_syncing_exchanges',
                        is_modifiable=True,
                    ),
                )

    def _run_actions_after_first_connection(self) -> None:
        """Perform the actions that are needed after the first DB connection

        Such as:
            - DB Upgrades
            - Create tables that are missing for new version
            - sanity checks

        May raise:
        - AuthenticationError if a wrong password is given or if the DB is corrupt
        - DBUpgradeError if there is a problem with DB upgrading or if the version
        is older than the one supported.
        - DBSchemaError if database schema is malformed.
        """
        # Run upgrades if needed -- only for user DB
        fresh_db = DBUpgradeManager(self).run_upgrades()
        if fresh_db:  # create tables during the first run and add the DB version
            self.conn.executescript(DB_SCRIPT_CREATE_TABLES)
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('version', str(ROTKEHLCHEN_DB_VERSION)),
            )

        # run checks on the database
        self.conn.schema_sanity_check()
        self._check_settings()

        # This logic executes only for the transient db
        self._connect(conn_attribute='conn_transient')
        transient_version = 0
        cursor = self.conn_transient.cursor()
        with suppress(sqlcipher.DatabaseError):  # pylint: disable=no-member  # not created yet
            result = cursor.execute('SELECT value FROM settings WHERE name=?', ('version',)).fetchone()  # noqa: E501
            if result is not None:
                transient_version = int(result[0])

        if transient_version != ROTKEHLCHEN_TRANSIENT_DB_VERSION:
            # "upgrade" transient DB
            tables = list(cursor.execute("SELECT name FROM sqlite_master WHERE type IS 'table'"))
            cursor.executescript('PRAGMA foreign_keys = OFF;')
            cursor.executescript(';'.join([f'DROP TABLE IF EXISTS {name[0]}' for name in tables]))
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
        return file_md5(self.user_data_dir / USERDB_NAME)

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['version']) -> int:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['last_write_ts']) -> Timestamp:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['premium_should_sync']) -> bool:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['main_currency']) -> AssetWithOracles:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['ongoing_upgrade_from_version']) -> int | None:  # noqa: E501
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['last_data_migration']) -> int | None:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['non_syncing_exchanges']) -> list['ExchangeLocationID']:  # noqa: E501
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['beacon_rpc_endpoint']) -> str:
        ...

    @overload
    def get_setting(self, cursor: 'DBCursor', name: Literal['ask_user_upon_size_discrepancy']) -> bool:  # noqa: E501
        ...

    def get_setting(
            self,
            cursor: 'DBCursor',
            name: Literal[
                'version',
                'last_write_ts',
                'premium_should_sync',
                'main_currency',
                'ongoing_upgrade_from_version',
                'last_data_migration',
                'non_syncing_exchanges',
                'beacon_rpc_endpoint',
                'ask_user_upon_size_discrepancy',
            ],
    ) -> int | Timestamp | bool | AssetWithOracles | list['ExchangeLocationID'] | str | None:
        deserializer, default_value = self.setting_to_default_type[name]
        cursor.execute(
            'SELECT value FROM settings WHERE name=?;', (name,),
        )
        result = cursor.fetchone()
        if result is not None:
            return deserializer(result[0])  # type: ignore

        return default_value  # type: ignore

    def set_setting(
            self,
            write_cursor: 'DBCursor',
            name: Literal[
                'version',
                'last_write_ts',
                'premium_should_sync',
                'ongoing_upgrade_from_version',
                'main_currency',
                'non_syncing_exchanges',
                'ask_user_upon_size_discrepancy',
            ],
            value: int | (Timestamp | Asset) | str | bool,
    ) -> None:
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (name, str(value)),
        )
        CachedSettings().update_entry(name, value)

    def _connect(self, conn_attribute: Literal['conn', 'conn_transient'] = 'conn') -> None:
        """Connect to the DB using password

        May raise:
        - SystemPermissionError if we are unable to open the DB file,
        probably due to permission errors
        - AuthenticationError if the given password is not the right one for the DB
        """
        if conn_attribute == 'conn':
            fullpath = self.user_data_dir / USERDB_NAME
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

        password_for_sqlcipher = protect_password_sqlcipher(self.password)
        script = f"PRAGMA key='{password_for_sqlcipher}';"
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
            # switch to WAL mode: https://www.sqlite.org/wal.html
            conn.execute('PRAGMA journal_mode=WAL;')
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            conn.close()
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
        new_password_for_sqlcipher = protect_password_sqlcipher(new_password)
        script = f"PRAGMA rekey='{new_password_for_sqlcipher}';"
        if self.sqlcipher_version == 3:
            script += f'PRAGMA kdf_iter={KDF_ITER};'
        try:
            conn.executescript(script)
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            log.error(
                f'At change password could not re-key the open {conn_attribute} '
                f'database: {e!s}',
            )
            return False
        return True

    def change_password(self, new_password: str) -> bool:
        """Changes the password for the currently logged in user"""
        result = (
            self._change_password(new_password, 'conn') and
            self._change_password(new_password, 'conn_transient')
        )
        if result is True:
            self.password = new_password
        return result

    def disconnect(self, conn_attribute: Literal['conn', 'conn_transient'] = 'conn') -> None:
        conn = getattr(self, conn_attribute, None)
        if conn:
            conn.close()
            setattr(self, conn_attribute, None)

    def export_unencrypted(self, temppath: Path) -> None:
        """Export the unencrypted DB to the temppath as plaintext DB

        The critical section is absolutely needed as a context switch
        from inside this execute script can result in:
        1. coming into this code again from another greenlet which can result
        to DB plaintext already in use
        2. Having a DB transaction open between the attach and detach and not
        closed when we detach which will result in DB plaintext locked.
        """
        with self.conn.critical_section():
            # flush the wal file to have up to date information when exporting data
            self.conn.execute('PRAGMA wal_checkpoint;')
            self.conn.executescript(
                f"ATTACH DATABASE '{temppath}' AS plaintext KEY '';"
                "SELECT sqlcipher_export('plaintext');"
                "DETACH DATABASE plaintext;",
            )

    def import_unencrypted(self, unencrypted_db_data: bytes) -> None:
        """Imports an unencrypted DB from raw data

        May raise:
        - DBUpgradeError if the rotki DB version is newer than the software or
        there is a DB upgrade and there is an error or if the version is older
        than the one supported.
        - AuthenticationError if the wrong password is given
        """
        self.conn.execute('PRAGMA wal_checkpoint;')
        self.disconnect()
        rdbpath = self.user_data_dir / USERDB_NAME
        # Make copy of existing encrypted DB before removing it
        shutil.copy2(
            rdbpath,
            self.user_data_dir / 'rotkehlchen_temp_backup.db',
        )
        rdbpath.unlink()

        # dump the unencrypted data into a temporary file
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdirname:  # needed on windows, see https://tinyurl.com/tmp-win-err  # noqa: E501
            tempdbpath = Path(tmpdirname) / 'temp.db'
            tempdbpath.write_bytes(unencrypted_db_data)

            # Now attach to the unencrypted DB and copy it to our DB and encrypt it
            self.conn = DBConnection(
                path=tempdbpath,
                connection_type=DBConnectionType.USER,
                sql_vm_instructions_cb=self.sql_vm_instructions_cb,
            )
            password_for_sqlcipher = protect_password_sqlcipher(self.password)
            script = f"ATTACH DATABASE '{rdbpath}' AS encrypted KEY '{password_for_sqlcipher}';"
            if self.sqlcipher_version == 3:
                script += f'PRAGMA encrypted.kdf_iter={KDF_ITER};'
            script += "SELECT sqlcipher_export('encrypted');DETACH DATABASE encrypted;"
            self.conn.executescript(script)
            self.disconnect()

        try:
            self._connect()
        except SystemPermissionError as e:
            raise AssertionError(
                f'Permission error when reopening the DB. {e!s}. Should never happen here',
            ) from e
        self._run_actions_after_first_connection()
        # all went okay, remove the original temp backup
        (self.user_data_dir / 'rotkehlchen_temp_backup.db').unlink()

    @contextmanager
    def user_write(self) -> Iterator[DBCursor]:
        """Get a write context for the user db and after write is finished
        also update the last write timestamp
        """
        # TODO: Rethink this
        with self.conn.write_ctx(commit_ts=True) as cursor:
            yield cursor

    @contextmanager
    def transient_write(self) -> Iterator[DBCursor]:
        """Get a write context for the transient user db and after write is finished
        also commit
        """
        with self.conn_transient.write_ctx() as cursor:
            yield cursor

    def get_settings(self, cursor: 'DBCursor', have_premium: bool = False) -> DBSettings:
        """Aggregates settings from DB and from the given args and returns the settings object"""
        cursor.execute('SELECT name, value FROM settings;')
        settings_dict = {}
        for q in cursor:
            settings_dict[q[0]] = q[1]

        # Also add the non-DB saved settings
        settings_dict['have_premium'] = have_premium
        return db_settings_from_dict(settings_dict, self.msg_aggregator)

    def set_settings(self, write_cursor: 'DBCursor', settings: ModifiableDBSettings) -> None:
        settings_dict = settings.serialize()
        write_cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            list(settings_dict.items()),
        )
        CachedSettings().update_entries(settings)

    def get_cache_for_api(self, cursor: 'DBCursor') -> dict[str, int]:
        """Returns a few key-value pairs that are used in the API
        from the `key_value_cache` table of the DB. Defaults to `Timestamp(0)` if not found"""
        cursor.execute(
            'SELECT name, value FROM key_value_cache WHERE name IN (?,?);',
            (DBCacheStatic.LAST_DATA_UPLOAD_TS.value, DBCacheStatic.LAST_BALANCE_SAVE.value),
        )
        db_cache = {name: int(value) for name, value in cursor}
        return {  # Return with default value, if needed
            DBCacheStatic.LAST_BALANCE_SAVE.value: db_cache.get(DBCacheStatic.LAST_BALANCE_SAVE.value, 0),  # noqa: E501
            DBCacheStatic.LAST_DATA_UPLOAD_TS.value: db_cache.get(DBCacheStatic.LAST_DATA_UPLOAD_TS.value, 0),  # noqa: E501
        }

    def get_static_cache(
            self,
            cursor: 'DBCursor',
            name: DBCacheStatic,
    ) -> Timestamp | None:
        """Returns the cache value from the `key_value_cache` table of the DB
        according to the given `name`. Defaults to `None` if not found"""
        value = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?;', (name.value,),
        ).fetchone()
        return None if value is None else Timestamp(int(value[0]))

    def set_static_cache(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheStatic,
            value: Timestamp,
    ) -> None:
        """Save the name-value pair of the cache with constant name
        to the `key_value_cache` table of the DB"""
        write_cursor.execute(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            (name.value, value),
        )

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_CRYPTOTX_OFFSET],
            **kwargs: Unpack[LabeledLocationArgsType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.BINANCE_PAIR_LAST_ID],
            **kwargs: Unpack[BinancePairLastTradeArgsType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_TS],
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> Timestamp | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_ID],
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> str | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_BLOCK_ID],
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_TS],
            **kwargs: Unpack[AddressArgType],
    ) -> Timestamp | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_IDX],
            **kwargs: Unpack[AddressArgType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.EXTRA_INTERNAL_TX],
            **kwargs: Unpack[ExtraTxArgType],
    ) -> ChecksumEvmAddress | None:
        ...

    @overload
    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS],
            **kwargs: Unpack[IndexArgType],
    ) -> Timestamp | None:
        ...

    def get_dynamic_cache(
            self,
            cursor: 'DBCursor',
            name: DBCacheDynamic,
            **kwargs: Any,
    ) -> int | Timestamp | str | ChecksumEvmAddress | None:
        """Returns the cache value from the `key_value_cache` table of the DB
        according to the given `name` and `kwargs`. Defaults to `None` if not found."""
        value = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?;', (name.get_db_key(**kwargs),),
        ).fetchone()
        return None if value is None else name.deserialize_callback(value[0])

    def delete_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheDynamic,
            **kwargs: str,
    ) -> None:
        """Delete the cache value from the `key_value_cache` table of the DB
        according to the given `name` and `kwargs` if it exists"""
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name=?;', (name.get_db_key(**kwargs),),
        ).fetchone()

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_CRYPTOTX_OFFSET],
            value: int,
            **kwargs: Unpack[LabeledLocationArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.BINANCE_PAIR_LAST_ID],
            value: int,
            **kwargs: Unpack[BinancePairLastTradeArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_TS],
            value: Timestamp,
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_ID],
            value: int,
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_BLOCK_ID],
            value: int,
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_TS],
            value: Timestamp,
            **kwargs: Unpack[AddressArgType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_IDX],
            value: int,
            **kwargs: Unpack[AddressArgType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.EXTRA_INTERNAL_TX],
            value: ChecksumEvmAddress,
            **kwargs: Unpack[ExtraTxArgType],
    ) -> None:
        ...

    @overload
    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS],
            value: Timestamp,
            **kwargs: Unpack[IndexArgType],
    ) -> None:
        ...

    def set_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheDynamic,
            value: int | Timestamp | ChecksumEvmAddress,
            **kwargs: Any,
    ) -> None:
        """Save the name-value pair of the cache with variable name to the `key_value_cache` table."""  # noqa: E501
        write_cursor.execute(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            (name.get_db_key(**kwargs), value),
        )

    def add_external_service_credentials(
            self,
            write_cursor: 'DBCursor',
            credentials: list[ExternalServiceApiCredentials],
    ) -> None:
        write_cursor.executemany(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) VALUES(?, ?, ?)',  # noqa: E501
            [c.serialize_for_db() for c in credentials],
        )

    def delete_external_service_credentials(self, services: list[ExternalService]) -> None:
        with self.user_write() as cursor:
            cursor.executemany(
                'DELETE FROM external_service_credentials WHERE name=?;',
                [(service.name.lower(),) for service in services],
            )

    def get_all_external_service_credentials(self) -> list[ExternalServiceApiCredentials]:
        """Returns a list with all the external service credentials saved in the DB"""
        with self.conn.read_ctx() as cursor:
            cursor.execute('SELECT name, api_key, api_secret from external_service_credentials;')

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
                    api_secret=q[2],
                ))
        return result

    def get_external_service_credentials(
            self,
            service_name: ExternalService,
    ) -> ExternalServiceApiCredentials | None:
        """If existing it returns the external service credentials for the given service"""
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT api_key, api_secret from external_service_credentials WHERE name=?;',
                (service_name.name.lower(),),
            )
            if (result := cursor.fetchone()) is None:
                return None

            # There can only be 1 result, since name is the primary key of the table
            return ExternalServiceApiCredentials(service=service_name, api_key=result[0], api_secret=result[1])  # noqa: E501

    def add_to_ignored_assets(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        """Add a new asset to the set of ignored assets. If the asset was already marked as
        ignored then we don't do anything.
        """
        write_cursor.execute(
            'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
            ('ignored_asset', asset.identifier),
        )

    def ignore_multiple_assets(self, write_cursor: 'DBCursor', assets: list[str]) -> None:
        """Add the provided identifiers to the list of ignored assets. If any asset was already
        marked as ignored then we don't do anything.
        """
        write_cursor.executemany(
            'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
            [('ignored_asset', asset_identifier) for asset_identifier in assets],
        )

    def remove_from_ignored_assets(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        write_cursor.execute(
            "DELETE FROM multisettings WHERE name='ignored_asset' AND value=?;",
            (asset.identifier,),
        )

    def get_ignored_asset_ids(self, cursor: 'DBCursor', only_nfts: bool = False) -> set[str]:
        """Gets the ignored asset ids without converting each one of them to an asset object

        We used to have a heavier version which converted them to an asset but removed
        it due to unnecessary roundtrips to the global DB for each asset initialization
        """
        bindings = []
        query = "SELECT value FROM multisettings WHERE name='ignored_asset' "
        if only_nfts is True:
            query += 'AND value LIKE ?'
            bindings.append(f'{NFT_DIRECTIVE}%')
        cursor.execute(query, bindings)
        return {x[0] for x in cursor}

    def add_to_ignored_action_ids(
            self,
            write_cursor: 'DBCursor',
            identifiers: list[str],
    ) -> None:
        """Adds a list of identifiers to be ignored.

        Raises InputError in case of adding already existing ignored action
        """
        tuples = [(x,) for x in identifiers]
        try:
            write_cursor.executemany(
                'INSERT INTO ignored_actions(identifier) VALUES(?)',
                tuples,
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError('One of the given action ids already exists in the database') from e

    def remove_from_ignored_action_ids(
            self,
            write_cursor: 'DBCursor',
            identifiers: list[str],
    ) -> None:
        """Removes a list of identifiers to be ignored.

        Raises InputError in case of removing an action that is not in the DB
        """
        tuples = [(x,) for x in identifiers]
        write_cursor.executemany(
            'DELETE FROM ignored_actions WHERE identifier=?;',
            tuples,
        )
        affected_rows = write_cursor.rowcount
        if affected_rows != len(identifiers):
            raise InputError(
                f'Tried to remove {len(identifiers) - affected_rows} '
                f'ignored actions that do not exist',
            )

    def get_ignored_action_ids(
            self,
            cursor: 'DBCursor',
    ) -> set[str]:
        return {entry[0] for entry in cursor.execute('SELECT identifier from ignored_actions;')}

    def add_multiple_balances(self, write_cursor: 'DBCursor', balances: list[DBAssetBalance]) -> None:  # noqa: E501
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

    def delete_eth2_daily_stats(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical ETH2 eth2_daily_staking_details data"""
        write_cursor.execute('DELETE FROM eth2_daily_staking_details;')

    def delete_cowswap_trade_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all cowswap trade/orders data from the DB"""
        write_cursor.execute('DELETE FROM cowswap_orders;')

    def delete_gnosispay_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all saved gnosispay merchant data from the DB"""
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name=?;',
            (DBCacheStatic.LAST_GNOSISPAY_QUERY_TS.value,),
        )
        write_cursor.execute('DELETE FROM gnosispay_data;')

    def purge_module_data(self, module_name: PurgeableModuleName | None) -> None:
        with self.user_write() as cursor:
            if module_name is None:
                self.delete_loopring_data(cursor)
                self.delete_eth2_daily_stats(cursor)
                self.delete_cowswap_trade_data(cursor)
                self.delete_gnosispay_data(cursor)
                log.debug('Purged all module data from the DB')
                return
            elif module_name == 'loopring':
                self.delete_loopring_data(cursor)
            elif module_name == 'eth2':
                self.delete_eth2_daily_stats(cursor)
            elif module_name == 'cowswap':
                self.delete_cowswap_trade_data(cursor)
            elif module_name == 'gnosis_pay':
                self.delete_gnosispay_data(cursor)
            else:
                log.debug(f'Requested to purge {module_name} data from the DB but nothing to do')
                return

            log.debug(f'Purged {module_name} data from the DB')

    def delete_loopring_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all loopring related data"""
        write_cursor.execute("DELETE FROM multisettings WHERE name LIKE 'loopring_%';")

    def get_used_query_range(self, cursor: 'DBCursor', name: str) -> tuple[Timestamp, Timestamp] | None:  # noqa: E501
        """Get the last start/end timestamp range that has been queried for name

        Currently possible names are:
        - {exchange_location_name}_margins_{exchange_name}
        - {location}_history_events_{optional_label}
        - {exchange_location_name}_lending_history_{exchange_name}
        - gnosisbridge_{address}
        """
        cursor.execute('SELECT start_ts, end_ts FROM used_query_ranges WHERE name=?', (name,))
        result = cursor.fetchone()
        if result is None:
            return None

        return Timestamp(int(result[0])), Timestamp(int(result[1]))

    def delete_used_query_range_for_exchange(
            self,
            write_cursor: 'DBCursor',
            location: Location,
            exchange_name: str | None = None,
    ) -> None:
        """Delete the query ranges for the given exchange name"""
        names_to_delete = f'{location!s}\\_%'
        if exchange_name is not None:
            names_to_delete += f'\\_{exchange_name}'
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (names_to_delete, '\\'),
        )
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?;',
            (names_to_delete, '\\'),
        )

    def purge_exchange_data(self, write_cursor: 'DBCursor', location: Location) -> None:
        self.delete_used_query_range_for_exchange(write_cursor=write_cursor, location=location)
        serialized_location = location.serialize_for_db()
        write_cursor.execute('DELETE FROM history_events WHERE location = ?;', (serialized_location,))  # noqa: E501

    def update_used_query_range(self, write_cursor: 'DBCursor', name: str, start_ts: Timestamp, end_ts: Timestamp) -> None:  # noqa: E501
        write_cursor.execute(
            'INSERT OR REPLACE INTO used_query_ranges(name, start_ts, end_ts) VALUES (?, ?, ?)',
            (name, str(start_ts), str(end_ts)),
        )

    def get_last_balance_save_time(self, cursor: 'DBCursor') -> Timestamp:
        cursor.execute(
            'SELECT MAX(timestamp) from timed_location_data',
        )
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return Timestamp(0)

        return Timestamp(int(result[0]))

    def add_multiple_location_data(self, write_cursor: 'DBCursor', location_data: list[LocationData]) -> None:  # noqa: E501
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
                    f'{Location.deserialize_from_db(entry.location)!s} at'
                    f' already existing timestamp {entry.time}.',
                ) from e

    def add_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            account_data: list[BlockchainAccountData],
    ) -> None:
        # Insert the blockchain account addresses and labels to the DB
        blockchain_accounts_query, bindings_to_insert = [], []
        for entry in account_data:
            blockchain_accounts_query.append((entry.chain.value, entry.address))
            if entry.label:
                bindings_to_insert.append((entry.address, entry.chain.value, entry.label))
        try:
            write_cursor.executemany(
                'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
                blockchain_accounts_query,
            )
            if len(bindings_to_insert) > 0:
                write_cursor.executemany(
                    'INSERT OR REPLACE INTO address_book(address, blockchain, name) VALUES (?, ?, ?)',  # noqa: E501
                    bindings_to_insert,
                )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Blockchain account/s {[x.address for x in account_data]} already exist',
            ) from e

        insert_tag_mappings(write_cursor=write_cursor, data=account_data, object_reference_keys=['address'])  # noqa: E501

    def edit_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            account_data: list[BlockchainAccountData],
    ) -> None:
        """Edit the given blockchain accounts

        At this point in the calling chain we should already know that:
        - All tags exist in the DB
        - All accounts exist in the DB
        """
        # Update the blockchain account labels in the DB
        bindings_to_update, bindings_to_delete = [], []
        for entry in account_data:
            if entry.label:
                bindings_to_update.append((entry.address, entry.chain.value, entry.label))
            else:
                bindings_to_delete.append((entry.address, entry.chain.value))

        modified_count, deleted_count = 0, 0
        if len(bindings_to_update) > 0:
            write_cursor.executemany(
                'INSERT OR REPLACE INTO address_book(address, blockchain, name) VALUES (?, ?, ?);',
                bindings_to_update,
            )
            modified_count += write_cursor.rowcount

        if len(bindings_to_delete) > 0:
            write_cursor.executemany(
                'DELETE FROM address_book WHERE address=? AND blockchain=?;',
                bindings_to_delete,
            )
            deleted_count += write_cursor.rowcount

        if modified_count != len(bindings_to_update):
            msg = (
                f'When updating blockchain accounts expected {len(bindings_to_update)} '
                f'modified, but instead there were {modified_count}. Should not happen.'
            )
            log.error(msg)
            raise InputError(msg)

        if deleted_count != len(bindings_to_delete):
            msg = (
                f'When updating blockchain accounts expected {len(bindings_to_delete)} '
                f'deleted, but instead there were {deleted_count}. Should not happen.'
            )
            log.error(msg)
            raise InputError(msg)

        replace_tag_mappings(
            write_cursor=write_cursor,
            data=account_data,
            object_reference_keys=['address'],
        )

    def remove_single_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
            accounts: ListOfBlockchainAddresses,
    ) -> None:
        """Removes the given blockchain accounts from the DB

        May raise:
        - InputError if any of the given accounts to delete did not exist
        """
        # Assure all are there
        accounts_number = write_cursor.execute(
            f'SELECT COUNT(*) from blockchain_accounts WHERE blockchain = ? '
            f'AND account IN ({",".join("?" * len(accounts))})',
            (blockchain.value, *accounts),
        ).fetchone()[0]
        if accounts_number != len(accounts):
            raise InputError(
                f'Tried to remove {len(accounts) - accounts_number} '
                f'{blockchain.value} accounts that do not exist',
            )

        tuples = [(blockchain.value, x) for x in accounts]

        # First remove all transaction related information for this address.
        # Needs to happen before the address is removed since removing the address
        # will also remove evmtx_address_mappings, thus making it impossible
        # to figure out which transactions are touched by this address
        if blockchain in EVM_CHAINS_WITH_TRANSACTIONS:
            for address in accounts:
                self.delete_data_for_evm_address(write_cursor, address, blockchain)  # type: ignore

        if blockchain in SUPPORTED_EVMLIKE_CHAINS:
            for address in accounts:
                self.delete_data_for_evmlike_address(write_cursor, address, blockchain)  # type: ignore

        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE object_reference = ?;',
            [(account,) for account in accounts],
        )
        write_cursor.executemany(
            'DELETE FROM blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', tuples,
        )

    def get_tokens_for_address(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
            token_exceptions: set[ChecksumEvmAddress],
    ) -> tuple[list[EvmToken] | None, Timestamp | None]:
        """Gets the detected tokens for the given address if the given current time
        is recent enough.

        If not, or if there is no saved entry, return None.
        """
        last_queried_ts = None
        querystr = (
            "SELECT key, value FROM evm_accounts_details WHERE account=? AND chain_id=? "
            "AND (key=? OR key=?) AND value NOT IN "
            "(SELECT value FROM multisettings WHERE name='ignored_asset')"
        )
        bindings = (address, blockchain.to_chain_id().serialize_for_db(), EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS, EVM_ACCOUNTS_DETAILS_TOKENS)  # noqa: E501
        cursor.execute(querystr, bindings)  # original place https://github.com/rotki/rotki/issues/5432 was seen # noqa: E501

        returned_list = []
        for (key, value) in cursor:
            if key == EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS:
                # At the moment last_queried_timestamp is not used. It used to be a cache for the
                # query but since we made token detection not run it is no longer used, but is
                # written. This will probably change in the future again. Related issue:
                # https://github.com/rotki/rotki/issues/5252
                last_queried_ts = deserialize_timestamp(value)
            else:  # should be EVM_ACCOUNTS_DETAILS_TOKENS
                try:
                    # This method is used directly when querying the balances and it is easier
                    # to resolve the token here
                    token = EvmToken(value)
                except (DeserializationError, UnknownAsset):
                    self.msg_aggregator.add_warning(
                        f'Could not deserialize {value} as a token when reading latest '
                        f'tokens list of {address}',
                    )
                    continue

                if token.evm_address not in token_exceptions:
                    returned_list.append(token)

        if len(returned_list) == 0 and last_queried_ts is None:
            return None, None

        return returned_list, last_queried_ts

    def save_tokens_for_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
            tokens: Sequence[Asset],
    ) -> None:
        """Saves detected tokens for an address"""
        now = ts_now()
        chain_id = blockchain.to_chain_id().serialize_for_db()
        insert_rows: list[tuple[ChecksumEvmAddress, int, str, str | Timestamp]] = [
            (
                address,
                chain_id,
                EVM_ACCOUNTS_DETAILS_TOKENS,
                x.identifier,
            )
            for x in tokens
        ]
        # Also add the update row for the timestamp
        insert_rows.append(
            (
                address,
                chain_id,
                EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS,
                now,
            ),
        )
        # Delete previous entries for tokens
        write_cursor.execute(
            'DELETE FROM evm_accounts_details WHERE account=? AND chain_id=? AND KEY IN(?, ?)',
            (address, chain_id, EVM_ACCOUNTS_DETAILS_TOKENS, EVM_ACCOUNTS_DETAILS_LAST_QUERIED_TS),
        )
        # Insert new values
        write_cursor.executemany(
            'INSERT OR REPLACE INTO evm_accounts_details '
            '(account, chain_id, key, value) VALUES (?, ?, ?, ?)',
            insert_rows,
        )

    def get_evm_accounts(self, cursor: 'DBCursor') -> list[ChecksumEvmAddress]:
        """Returns a list of unique EVM accounts from all EVM chains."""
        placeholders = ','.join('?' * len(SUPPORTED_EVM_CHAINS))
        cursor.execute(
            f'SELECT DISTINCT account FROM blockchain_accounts WHERE blockchain IN ({placeholders});',  # noqa: E501
            [chain.value for chain in SUPPORTED_EVM_CHAINS],
        )
        return [entry[0] for entry in cursor]

    def get_blockchain_accounts(self, cursor: 'DBCursor') -> BlockchainAccounts:
        """Returns a Blockchain accounts instance containing all blockchain account addresses"""
        cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts;',
        )
        accounts_lists = defaultdict(list)
        for entry in cursor:
            try:
                blockchain = SupportedBlockchain.deserialize(entry[0])
            except DeserializationError:
                log.warning(f'Unsupported blockchain {entry[0]} found in DB. Ignoring...')
                continue

            if blockchain is None or is_valid_db_blockchain_account(blockchain=blockchain, account=entry[1]) is False:  # noqa: E501
                self.msg_aggregator.add_warning(
                    f'Invalid {entry[0]} account in DB: {entry[1]}. '
                    f'This should not happen unless the DB was manually modified. '
                    f'Skipping entry. This needs to be fixed manually. If you '
                    f'can not do that alone ask for help in the issue tracker',
                )
                continue

            accounts_lists[blockchain.get_key()].append(entry[1])

        return BlockchainAccounts(**{x: tuple(y) for x, y in accounts_lists.items()})

    def get_blockchain_account_data(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> list[SingleBlockchainAccountData]:
        """Returns account data for a particular blockchain.

        Each account entry contains address and potentially label and tags
        """
        query = cursor.execute(
            "SELECT A.account, C.name, group_concat(B.tag_name,',') "
            "FROM blockchain_accounts AS A "
            "LEFT OUTER JOIN tag_mappings AS B ON B.object_reference = A.account "
            "LEFT OUTER JOIN address_book AS C ON C.address = A.account AND (A.blockchain IS C.blockchain OR C.blockchain IS ?) "  # noqa: E501
            "WHERE A.blockchain=? GROUP BY account;",
            (ANY_BLOCKCHAIN_ADDRESSBOOK_VALUE, blockchain.value),
        )

        data = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[2])
            data.append(SingleBlockchainAccountData(
                address=entry[0],
                label=entry[1],
                tags=tags,
            ))

        return data

    @overload
    def get_single_blockchain_addresses(
            self,
            cursor: 'DBCursor',
            blockchain: SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    ) -> list[ChecksumEvmAddress]:
        ...

    @overload
    def get_single_blockchain_addresses(
            self,
            cursor: 'DBCursor',
            blockchain: SUPPORTED_BITCOIN_CHAINS,
    ) -> list[BTCAddress]:
        ...

    @overload
    def get_single_blockchain_addresses(
            self,
            cursor: 'DBCursor',
            blockchain: SUPPORTED_SUBSTRATE_CHAINS,
    ) -> list[SubstrateAddress]:
        ...

    def get_single_blockchain_addresses(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> list[AnyBlockchainAddress]:
        """Returns addresses for a particular blockchain"""
        addresses = []
        cursor.execute(
            'SELECT account FROM blockchain_accounts WHERE blockchain=?',
            (blockchain.value,),
        )
        for entry in cursor:
            if not is_valid_db_blockchain_account(blockchain, entry[0]):
                self.msg_aggregator.add_warning(
                    f'Invalid {blockchain} account in DB: {entry[0]}. '
                    f'This should not happen unless the DB was manually modified. '
                    f'Skipping entry. This needs to be fixed manually. If you '
                    f'can not do that alone ask for help in the issue tracker',
                )
                continue

            addresses.append(entry[0])

        return addresses

    def get_manually_tracked_balances(
            self,
            cursor: 'DBCursor',
            balance_type: BalanceType | None = BalanceType.ASSET,
            include_entries_with_missing_assets: bool = False,
    ) -> list[ManuallyTrackedBalance]:
        """Returns the manually tracked balances from the DB"""
        query_balance_type = ''
        if balance_type is not None:
            query_balance_type = f"WHERE A.category='{balance_type.serialize_for_db()}'"
        query = cursor.execute(
            f"SELECT A.asset, A.label, A.amount, A.location, group_concat(B.tag_name,','), "
            f"A.category, A.id FROM manually_tracked_balances as A "
            f"LEFT OUTER JOIN tag_mappings as B on B.object_reference = A.id "
            f"{query_balance_type} GROUP BY label;",
        )

        data = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[4])
            if (
                (asset_is_missing := not Asset(entry[0]).exists()) is True
                and include_entries_with_missing_assets is False
            ):
                continue

            try:
                balance_type = BalanceType.deserialize_from_db(entry[5])
                data.append(ManuallyTrackedBalance(
                    identifier=entry[6],
                    asset=Asset(entry[0]),
                    label=entry[1],
                    amount=FVal(entry[2]),
                    location=Location.deserialize_from_db(entry[3]),
                    tags=tags,
                    balance_type=balance_type,
                    asset_is_missing=asset_is_missing,
                ))
            except (DeserializationError, ValueError) as e:
                # ValueError would be due to FVal failing
                self.msg_aggregator.add_warning(
                    f'Unexpected data in a ManuallyTrackedBalance entry in the DB: {e!s}',
                )

        return data

    def add_manually_tracked_balances(self, write_cursor: 'DBCursor', data: list[ManuallyTrackedBalance]) -> None:  # noqa: E501
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
                entry.identifier = write_cursor.lastrowid
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'One of the manually tracked balance entries already exists in the DB. {e!s}',
            ) from e

        insert_tag_mappings(write_cursor=write_cursor, data=data, object_reference_keys=['identifier'])  # noqa: E501

        # make sure assets are included in the global db user owned assets
        GlobalDBHandler.add_user_owned_assets([x.asset for x in data])

    def edit_manually_tracked_balances(self, write_cursor: 'DBCursor', data: list[ManuallyTrackedBalance]) -> None:  # noqa: E501
        """Edits manually tracked balances

        Edits the manually tracked balances for each of the given balance labels.

        At this point in the calling chain we should already know that:
        - All tags exist in the DB

        May raise:
        - InputError if any of the manually tracked balance labels to edit do not
        exist in the DB
        """
        # Update the manually tracked balance entries in the DB
        tuples = [(
            entry.asset.identifier,
            str(entry.amount),
            entry.location.serialize_for_db(),
            BalanceType.serialize_for_db(entry.balance_type),
            entry.label,
            entry.identifier,
        ) for entry in data]

        write_cursor.executemany(
            'UPDATE manually_tracked_balances SET asset=?, amount=?, location=?, category=?, label=?'  # noqa: E501
            'WHERE id=?;', tuples,
        )
        if write_cursor.rowcount != len(data):
            msg = 'Tried to edit manually tracked balance entry that did not exist in the DB'
            raise InputError(msg)
        replace_tag_mappings(write_cursor=write_cursor, data=data, object_reference_keys=['identifier'])  # noqa: E501

    def remove_manually_tracked_balances(self, write_cursor: 'DBCursor', ids: list[int]) -> None:
        """
        Removes manually tracked balances for the given ids

        May raise:
        - InputError if any of the given manually tracked balance labels
        to delete did not exist
        """
        tuples = [(x,) for x in ids]
        write_cursor.executemany(
            'DELETE FROM tag_mappings WHERE object_reference = ?;', tuples,
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

    def save_balances_data(self, write_cursor: 'DBCursor', data: dict[str, Any], timestamp: Timestamp) -> None:  # noqa: E501
        """The keys of the data dictionary can be any kind of asset plus 'location'
        and 'net_usd'. This gives us the balance data per assets, the balance data
        per location and finally the total balance

        The balances are saved in the DB at the given timestamp
        """
        balances = []
        locations = []

        for key, val in data['assets'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {key!s}'
            assert isinstance(key, Asset), msg
            balances.append(DBAssetBalance(
                category=BalanceType.ASSET,
                time=timestamp,
                asset=key,
                amount=val['amount'],
                usd_value=val['usd_value'],
            ))

        for key, val in data['liabilities'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {key!s}'
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
            val2 = cast('dict', val2)
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
            api_secret: ApiSecret | None,
            passphrase: str | None = None,
            kraken_account_type: KrakenAccountType | None = None,
            binance_selected_trade_pairs: list[str] | None = None,
    ) -> None:
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {location!s}')

        with self.user_write() as cursor:
            cursor.execute(
                'INSERT INTO user_credentials '
                '(name, location, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?, ?)',
                (name, location.serialize_for_db(), api_key, api_secret.decode() if api_secret is not None else None, passphrase),  # noqa: E501
            )

            if location == Location.KRAKEN and kraken_account_type is not None:
                cursor.execute(
                    'INSERT INTO user_credentials_mappings '
                    '(credential_name, credential_location, setting_name, setting_value) '
                    'VALUES (?, ?, ?, ?)',
                    (name, location.serialize_for_db(), KRAKEN_ACCOUNT_TYPE_KEY, kraken_account_type.serialize()),  # noqa: E501
                )

            if location in (Location.BINANCE, Location.BINANCEUS) and binance_selected_trade_pairs is not None:  # noqa: E501
                self.set_binance_pairs(cursor, name=name, pairs=binance_selected_trade_pairs, location=location)  # noqa: E501

    def edit_exchange(
            self,
            write_cursor: 'DBCursor',
            name: str,
            location: Location,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_selected_trade_pairs: list[str] | None,
    ) -> None:
        """May raise InputError if something is wrong with editing the DB"""
        if location not in SUPPORTED_EXCHANGES:
            raise InputError(f'Unsupported exchange {location!s}')

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
                raise InputError(f'Could not update DB user_credentials due to {e!s}') from e

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
                raise InputError(f'Could not update DB user_credentials_mappings due to {e!s}') from e  # noqa: E501

        location_is_binance = location in (Location.BINANCE, Location.BINANCEUS)
        if location_is_binance and binance_selected_trade_pairs is not None:
            try:
                exchange_name = new_name if new_name is not None else name
                self.set_binance_pairs(write_cursor, name=exchange_name, pairs=binance_selected_trade_pairs, location=location)  # noqa: E501
                # Also delete used query ranges to allow fetching missing trades
                # from the possible new pairs
                write_cursor.execute(
                    'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
                    (f'{location!s}\\_history_events_\\_{name}', '\\'),
                )
            except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
                raise InputError(f'Could not update DB user_credentials_mappings due to {e!s}') from e  # noqa: E501

        if new_name is not None:
            exchange_re = re.compile(r'(.*?)_(margins|history_events).*')
            used_ranges = write_cursor.execute(
                'SELECT * from used_query_ranges WHERE name LIKE ?',
                (f'{location!s}_%_{name}',),
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
                    (f'{location!s}_{entry_type}_{new_name}', f'{location!s}_{entry_type}_{name}')
                    for entry_type in entry_types
                ],
            )

            # also update the name of the events related to this exchange
            write_cursor.execute(
                'UPDATE history_events SET location_label=? WHERE location=? AND location_label=?',
                (new_name, location.serialize_for_db(), name),
            )

    def remove_exchange(self, write_cursor: 'DBCursor', name: str, location: Location) -> None:
        """
        Removes the exchange location from user_credentials and from
        `the non_syncing_exchanges`setting.
        """
        write_cursor.execute(
            'DELETE FROM user_credentials WHERE name=? AND location=?',
            (name, location.serialize_for_db()),
        )

        settings = self.get_settings(write_cursor)
        if len(ignored_locations_settings := settings.non_syncing_exchanges) == 0:
            return

        ignored_exchanges = [
            exchange for exchange in ignored_locations_settings
            if not (exchange.location == location and exchange.name == name)
        ]
        self.set_setting(
            write_cursor=write_cursor,
            name='non_syncing_exchanges',
            value=serialize_db_setting(
                value=ignored_exchanges,
                setting='non_syncing_exchanges',
                is_modifiable=True,
            ),
        )

    def get_exchange_credentials(
            self,
            cursor: 'DBCursor',
            location: Location | None = None,
            name: str | None = None,
    ) -> dict[Location, list[ExchangeApiCredentials]]:
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
                    f'the app with an older version. {e!s}',
                )
                continue

            if location not in SUPPORTED_EXCHANGES:
                continue

            credentials[location].append(ExchangeApiCredentials(
                name=entry[0],
                location=location,
                api_key=ApiKey(entry[2]),
                api_secret=ApiSecret(str.encode(entry[3])) if entry[3] is not None else None,
                passphrase=passphrase,
            ))

        return credentials

    def get_exchange_credentials_extras(self, name: str, location: Location) -> dict[str, Any]:
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
                        log.error(f'Couldnt deserialize kraken account type from DB. {e!s}')
                else:  # can only be BINANCE_MARKETS_KEY
                    try:
                        extras[key] = json.loads(entry[1])
                    except json.JSONDecodeError as e:
                        log.error(f'Could not deserialize binance markets from DB. {e!s}')

        return extras

    def set_binance_pairs(self, write_cursor: 'DBCursor', name: str, pairs: list[str], location: Location) -> None:  # noqa: E501
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

    def get_binance_pairs(self, name: str, location: Location) -> list[str]:
        """Gets the market pairs used by the user on a specific binance exchange"""
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT setting_value FROM user_credentials_mappings WHERE '
                'credential_name=? AND credential_location=? AND setting_name=?',
                (name, location.serialize_for_db(), BINANCE_MARKETS_KEY),
            )
            data = cursor.fetchone()
            if data and data[0] != '':
                return json.loads(data[0])
            return []

    def write_tuples(
            self,
            write_cursor: 'DBCursor',
            tuple_type: DBTupleType,
            query: str,
            tuples: Sequence[tuple[Any, ...]],
            **kwargs: ChecksumEvmAddress | None,
    ) -> None:
        """
        Helper function to help write multiple tuples of some kind of entry and
        log the error if anything is raised.

        For transactions the query is INSERT OR IGNORE as the uniqueness constraints
        are known in advance. Also when used for inputting transactions make sure that
        for one write it's all for the same chain id.

        For the other tables simple `INSERT` is used but the primary key is a unique
        identifier each time so they can't be considered duplicates.
        """
        relevant_address = kwargs.get('relevant_address')
        try:
            write_cursor.executemany(query, tuples)
            if relevant_address is not None:
                if tuple_type == 'evm_transaction':
                    tx_hash_idx, chain_id_idx = 0, 1
                else:  # relevant address can only be left for internal tx
                    tx_hash_idx, chain_id_idx = 4, 5
                write_cursor.executemany(
                    'INSERT OR IGNORE INTO evmtx_address_mappings(tx_id, address) '
                    'SELECT TX.identifier, ? FROM evm_transactions TX WHERE '
                    'TX.tx_hash=? AND TX.chain_id=?',
                    [(relevant_address, x[tx_hash_idx], x[chain_id_idx]) for x in tuples],
                )
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            # That means that one of the tuples hit a constraint, probably some
            # foreign key connection is broken. Try to put them 1 by one.
            for entry in tuples:
                try:
                    last_row_id = write_cursor.lastrowid
                    write_cursor.execute(query, entry)
                    if relevant_address is not None and (new_id := write_cursor.lastrowid) != last_row_id:  # noqa: E501
                        write_cursor.execute(  # new addition happened
                            'INSERT OR IGNORE INTO evmtx_address_mappings '
                            '(tx_id, address) VALUES(?, ?)',
                            (new_id, relevant_address),
                        )
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    string_repr = db_tuple_to_str(entry, tuple_type)
                    log.warning(
                        f'Did not add "{string_repr}" to the DB due to "{e!s}".'
                        f'Some other constraint was hit.',
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

    def add_margin_positions(self, write_cursor: 'DBCursor', margin_positions: list[MarginPosition]) -> None:  # noqa: E501
        margin_tuples: list[tuple[Any, ...]] = []
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
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            location: Location | None = None,
    ) -> list[MarginPosition]:
        """Returns a list of margin positions optionally filtered by time and location

        The returned list is ordered from oldest to newest
        """
        query = 'SELECT * FROM margin_positions '
        if location is not None:
            query += f"WHERE location='{location.serialize_for_db()}' "
        query, bindings = form_query_to_filter_timestamps(query, 'close_time', from_ts, to_ts)
        results = cursor.execute(query, bindings)

        margin_positions = []
        for result in results:
            try:
                margin = MarginPosition.deserialize_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing margin position from the DB. '
                    f'Skipping it. Error was: {e!s}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing margin position from the DB. Skipping it. '
                    f'Unknown asset {e.identifier} found',
                )
                continue
            margin_positions.append(margin)

        return margin_positions

    def get_entries_count(
            self,
            cursor: 'DBCursor',
            entries_table: Literal[
                'address_book',
                'evm_transactions',
                'eth2_daily_staking_details',
                'entries_notes',
                'user_notes',
                'assets',
                'history_events',
                'accounting_rules',
                'unresolved_remote_conflicts',
                'calendar',
            ],
            op: Literal['OR', 'AND'] = 'OR',
            group_by: str | None = None,
            **kwargs: Any,
    ) -> int:
        """Returns how many of a certain type of entry are saved in the DB"""
        cursorstr = f'SELECT COUNT(*) from {entries_table}'
        if len(kwargs) != 0:
            cursorstr += ' WHERE'
            cursorstr += op.join([f' {arg} = "{val}" ' for arg, val in kwargs.items()])
        if group_by is not None:
            cursorstr += f' GROUP BY {group_by}'

        cursorstr += ';'
        cursor.execute(cursorstr)

        if group_by is not None:
            return len(cursor.fetchall())
        # else
        return cursor.fetchone()[0]

    def delete_data_for_evm_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
    ) -> None:
        """Deletes all evm related data from the DB for a single evm address"""
        if blockchain == SupportedBlockchain.ETHEREUM:  # mainnet only behaviour
            write_cursor.execute('DELETE FROM used_query_ranges WHERE name = ?', (f'aave_events_{address}',))  # noqa: E501
            write_cursor.execute(  # queried addresses per module
                "DELETE FROM multisettings WHERE name LIKE 'queried_address_%' AND value = ?",
                (address,),
            )
            loopring = DBLoopring(self)
            loopring.remove_accountid_mapping(write_cursor, address)
            # Delete withdrawals related data
            self.delete_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_TS, address=address)  # noqa: E501
            self.delete_dynamic_cache(write_cursor=write_cursor, name=DBCacheDynamic.WITHDRAWALS_IDX, address=address)  # noqa: E501

        write_cursor.execute(
            'DELETE FROM evm_accounts_details WHERE account=? AND chain_id=?',
            (address, blockchain.to_chain_id().serialize_for_db()),
        )

        write_cursor.execute(
            f"DELETE FROM key_value_cache WHERE name LIKE '{EXTRAINTERNALTXPREFIX}_{blockchain.to_chain_id().value}%' AND value = ?",  # noqa: E501
            (address,),
        )

        dbtx = DBEvmTx(self)
        dbtx.delete_transactions(write_cursor=write_cursor, address=address, chain=blockchain)
        if blockchain == SupportedBlockchain.GNOSIS:
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name=?',
                (f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}',),
            )

    def delete_data_for_evmlike_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SUPPORTED_EVMLIKE_CHAINS_TYPE,  # pylint: disable=unused-argument
    ) -> None:
        """Deletes all evmlike chain related data from the DB for a single evm address

        For now it's always gonna be only zksync lite.
        """
        other_addresses = self.get_single_blockchain_addresses(
            cursor=write_cursor,
            blockchain=SupportedBlockchain.ZKSYNC_LITE,
        )
        other_addresses.remove(address)  # exclude the address in question so it's only the others

        # delete events by tx_hash
        write_cursor.execute(
            'SELECT tx_hash, from_address, to_address FROM zksynclite_transactions WHERE '
            'from_address=? OR to_address=?',
            (address, address),
        )
        hashes_to_remove = [
            x[0] for x in write_cursor
            if x[1] not in other_addresses and x[2] not in other_addresses  # pylint: disable=unsupported-membership-test
        ]
        for hashes_chunk in get_chunks(hashes_to_remove, n=1000):  # limit num of hashes in a query
            write_cursor.execute(  # delete transactions themselves
                f'DELETE FROM zksynclite_transactions WHERE tx_hash IN '
                f'({",".join("?" * len(hashes_chunk))})',
                hashes_chunk,
            )
            write_cursor.execute(
                f'DELETE FROM history_events WHERE identifier IN (SELECT H.identifier '
                f'FROM history_events H INNER JOIN evm_events_info E '
                f'ON H.identifier=E.identifier AND E.tx_hash IN '
                f'({", ".join(["?"] * len(hashes_chunk))}) AND H.location=?)',
                hashes_chunk + [Location.ZKSYNC_LITE.serialize_for_db()],
            )

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
                log.error(f'Could not delete rotki premium credentials: {e!s}')
                return False
        return True

    def get_rotkehlchen_premium(self, cursor: 'DBCursor') -> PremiumCredentials | None:
        cursor.execute(
            "SELECT api_key, api_secret FROM user_credentials where name='rotkehlchen';",
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
    ) -> tuple[list[str], list[str]]:
        """Get all entries of net value data from the DB"""
        with self.conn.read_ctx() as cursor:
            cursor.execute(  # Get the total location ("H") entries in ascending time
                "SELECT timestamp, usd_value FROM timed_location_data "
                "WHERE location='H' AND timestamp >= ? ORDER BY timestamp ASC;",
                (from_ts,),
            )
            if not include_nfts:
                with self.conn.read_ctx() as nft_cursor:
                    nft_cursor.execute(
                        'SELECT timestamp, SUM(usd_value) FROM timed_balances WHERE '
                        'timestamp >= ? AND currency LIKE ? GROUP BY timestamp',
                        (from_ts, f'{NFT_DIRECTIVE}%'),
                    )
                    nft_values = dict(nft_cursor)

            data, times_int = [], []
            for entry in cursor:
                times_int.append(entry[0])
                if include_nfts:
                    total = entry[1]
                else:
                    total = str(FVal(entry[1]) - FVal(nft_values.get(entry[0], 0)))  # pyright: ignore  # nft_values is populated when include_nfts is False

                data.append(total)

        return times_int, data

    @staticmethod
    def _infer_zero_timed_balances(
            cursor: 'DBCursor',
            balances: list[SingleDBAssetBalance],
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> list[SingleDBAssetBalance]:
        """
        Given a list of asset specific timed balances, infers the missing zero timed balances
        for the asset. We add 0 balances on the start and end of a period of 0 balances.
        It addresses this issue: https://github.com/rotki/rotki/issues/2822

        Example
        We have the following timed balances for ETH (value, time):
        (1, 1), (1, 2), (2, 3), (5, 7), (5, 12)
        The timestamps of all timed balances in the DB are:
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
        So we need to infer the following zero timed balances:
        (0, 4), (0, 6), (0, 8), (0, 11)

        Keep in mind that in a case like this (1, 1), (1, 2), (5, 4) we will infer (0, 3)
        despite the fact that it is not strictly needed by the front end.
        """
        if len(balances) == 0:
            return []

        if from_ts is None:
            from_ts = Timestamp(0)
        if to_ts is None:
            to_ts = ts_now()

        cursor.execute(
            'SELECT COUNT(DISTINCT timestamp) FROM timed_balances WHERE timestamp BETWEEN ? AND ?',
            (from_ts, to_ts),
        )
        num_distinct_timestamps = cursor.fetchone()[0]

        asset_timestamps = [b.time for b in balances if b.amount != ZERO]  # ignore timestamps from 0 balances added by the ssf_graph_multiplier setting  # noqa: E501
        if len(asset_timestamps) == num_distinct_timestamps:
            return []

        cursor.execute(
            'SELECT timestamp, category FROM timed_balances WHERE timestamp BETWEEN ? AND ? '
            'ORDER BY timestamp ASC',
            (from_ts, to_ts),
        )
        all_timestamps, all_categories = zip(*cursor, strict=True)
        # dicts maintain insertion order in python 3.7+
        timestamps_have_asset_balance = dict.fromkeys(all_timestamps, False)
        timestamps_with_asset_balance = dict.fromkeys(asset_timestamps, True)
        timestamps_have_asset_balance.update(timestamps_with_asset_balance)
        prev_has_asset_balance = timestamps_have_asset_balance[all_timestamps[0]]  # the value of the first timestamp  # noqa: E501
        prev_timestamp = all_timestamps[0]
        inferred_balances: list[SingleDBAssetBalance] = []
        is_zero_period_open = False
        last_asset_category = all_categories[-1]  # just a placeholder value, no need to calculate the actual value here  # noqa: E501
        for idx, (timestamp, has_asset_balance) in enumerate(timestamps_have_asset_balance.items()):  # noqa: E501
            if idx == len(timestamps_have_asset_balance) - 1 and has_asset_balance is False:
                # If there is no balance for the last timestamp add a zero balance.
                inferred_balances.append(
                    SingleDBAssetBalance(
                        time=timestamp,
                        amount=ZERO,
                        usd_value=ZERO,
                        category=last_asset_category,
                    ),
                )
            elif has_asset_balance is False and prev_has_asset_balance is True:
                # add the start of a zero balance period
                inferred_balances.append(
                    SingleDBAssetBalance(
                        time=timestamp,
                        amount=ZERO,
                        usd_value=ZERO,
                        category=BalanceType.deserialize_from_db(all_categories[idx - 1]),  # the category of the previous timed_balance of the asset  # noqa: E501
                    ),
                )
                is_zero_period_open = True
            elif has_asset_balance is True and prev_has_asset_balance is False and is_zero_period_open is True:  # noqa: E501
                # add the end of a zero balance period
                inferred_balances.append(
                    SingleDBAssetBalance(
                        time=prev_timestamp,
                        amount=ZERO,
                        usd_value=ZERO,
                        category=inferred_balances[-1].category,  # the category of the asset at the start of the zero balance period  # noqa: E501
                    ),
                )
                is_zero_period_open = False
                last_asset_category = inferred_balances[-1].category
            elif has_asset_balance is True:
                last_asset_category = BalanceType.deserialize_from_db(all_categories[idx])
            prev_has_asset_balance, prev_timestamp = has_asset_balance, timestamp
        return inferred_balances

    def query_timed_balances(
            self,
            cursor: 'DBCursor',
            asset: Asset,
            balance_type: BalanceType,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> list[SingleDBAssetBalance]:
        """Query all balance entries for an asset and balance type within a range of timestamps
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

        if settings.treat_eth2_as_eth and asset == A_ETH:
            querystr = querystr.replace('currency=?', 'currency IN (?,?)')
            bindings.append('ETH2')

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
            if settings.ssf_graph_multiplier == 0 or idx == results_length - 1:
                continue

            next_result_time = results[idx + 1][0]
            max_diff = settings.balance_save_frequency * HOUR_IN_SECONDS * settings.ssf_graph_multiplier  # noqa: E501
            while next_result_time - entry_time > max_diff:
                entry_time += settings.balance_save_frequency * HOUR_IN_SECONDS
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

        if settings.infer_zero_timed_balances is True:
            inferred_balances = self._infer_zero_timed_balances(cursor, balances, from_ts, to_ts)
            if len(inferred_balances) != 0:
                balances.extend(inferred_balances)
                balances.sort(key=lambda x: x.time)

        if settings.treat_eth2_as_eth and asset.identifier == 'ETH':
            return combine_asset_balances(balances)

        return balances

    def query_collection_timed_balances(
            self,
            cursor: 'DBCursor',
            collection_id: int,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> list[SingleDBAssetBalance]:
        """Query all balance entries for all assets of a collection within a range of timestamps
        """
        with GlobalDBHandler().conn.read_ctx() as global_cursor:
            global_cursor.execute(
                'SELECT asset FROM multiasset_mappings WHERE collection_id=?',
                (collection_id,),
            )
            asset_balances: list[SingleDBAssetBalance] = []
            for x in global_cursor:
                asset_balances.extend(self.query_timed_balances(
                    cursor=cursor,
                    asset=Asset(x[0]),
                    balance_type=BalanceType.ASSET,
                    from_ts=from_ts,
                    to_ts=to_ts,
                ))

        asset_balances.sort(key=lambda x: x.time)
        return combine_asset_balances(asset_balances)

    def query_owned_assets(self, cursor: 'DBCursor') -> list[Asset]:
        """Query the DB for a list of all assets ever owned

        The assets are taken from:
        - Balance snapshots
        - Manual balances
        """
        # but think on the performance. This is a synchronous api call so if
        # it starts taking too much time the calling logic needs to change
        results = set()
        for table_entry in TABLES_WITH_ASSETS:
            table_name = table_entry[0]
            columns = table_entry[1:]
            columns_str = ', '.join(columns)
            bindings: tuple | tuple[str] = ()
            condition = ''
            if table_name in {'manually_tracked_balances', 'timed_balances'}:
                bindings = (BalanceType.LIABILITY.serialize_for_db(),)
                condition = ' WHERE category!=?'

            try:
                cursor.execute(
                    f'SELECT DISTINCT {columns_str} FROM {table_name} {condition};',
                    bindings,
                )
            except sqlcipher.OperationalError as e:    # pylint: disable=no-member
                log.error(f'Could not fetch assets from table {table_name}. {e!s}')
                continue

            for result in cursor:
                for asset_id in result:
                    try:
                        if asset_id is not None:
                            results.add(Asset(asset_id).check_existence())
                    except UnknownAsset:
                        if table_name == 'manually_tracked_balances':
                            self.msg_aggregator.add_warning(
                                f'Unknown/unsupported asset {asset_id} found in the '
                                f'manually tracked balances. Have you modified the assets DB? '
                                f'Make sure that the aforementioned asset is in there.',
                            )
                        else:
                            log.debug(
                                f'Unknown/unsupported asset {asset_id} found in the database '
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
        GlobalDBHandler.add_user_owned_assets(assets)

    def add_asset_identifiers(self, write_cursor: 'DBCursor', asset_identifiers: list[str]) -> None:  # noqa: E501
        """Adds an asset to the user db asset identifier table"""
        write_cursor.executemany(
            'INSERT OR IGNORE INTO assets(identifier) VALUES(?);',
            [(x,) for x in asset_identifiers],
        )

    def sync_globaldb_assets(self, write_cursor: 'DBCursor') -> None:
        """Makes sure that:
        - all the GlobalDB asset identifiers are mirrored in the user DB
        - all the assets set to have the SPAM_PROTOCOL in the global DB
        are set to be part of the user's ignored list
        """
        with GlobalDBHandler().conn.read_ctx() as cursor:
            # after successful update add all asset ids
            cursor.execute('SELECT identifier from assets;')
            self.add_asset_identifiers(
                write_cursor=write_cursor,
                asset_identifiers=[x[0] for x in cursor],
            )  # could do an attach DB here instead of two different cursor queries but probably would be overkill # noqa: E501
            globaldb_spam = cursor.execute(
                'SELECT identifier FROM evm_tokens WHERE protocol=?',
                (SPAM_PROTOCOL,),
            ).fetchall()
            write_cursor.executemany(
                'INSERT OR IGNORE INTO multisettings(name, value) VALUES(?, ?)',
                [('ignored_asset', identifier[0]) for identifier in globaldb_spam],
            )

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
        user DB with another given asset. There is some limitations/checks for the
        source and target. This is not checked here but at the api level. The limitations are:
        - source and target should not both be EVM assets
        - source and target should not be the same

        DO NOT call this without these checks as it will put the DBs in an inconsistent state.

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
            globaldb.delete_asset_by_identifier(source_identifier)

        if userdb_query != 0:
            with self.user_write() as write_cursor:
                write_cursor.execute(  # merge the assets in the timed_balances table
                    """
                    WITH merged_rows AS (
                        SELECT
                            category,
                            timestamp,
                            currency,
                            SUM(amount) AS total_amount,
                            SUM(usd_value) AS total_usd_value
                        FROM timed_balances
                        WHERE currency IN (?, ?)
                        GROUP BY category, timestamp
                    )
                    UPDATE timed_balances AS tb
                    SET
                        currency = ?,
                        amount = mr.total_amount,
                        usd_value = mr.total_usd_value
                    FROM merged_rows mr
                    WHERE
                        tb.category = mr.category AND
                        tb.timestamp = mr.timestamp AND
                        tb.currency = mr.currency AND
                        tb.currency IN (?, ?);
                    """,
                    (
                        source_identifier,
                        target_asset.identifier,
                        target_asset.identifier,
                        target_asset.identifier,
                        source_identifier,
                    ),
                )
                write_cursor.execute(
                    'DELETE FROM timed_balances WHERE currency=?',
                    (source_identifier,),
                )
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

    def get_latest_location_value_distribution(self) -> list[LocationData]:
        """Gets the latest location data

        Returns a list of `LocationData` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all locations
        """
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT timestamp, location, usd_value FROM timed_location_data WHERE '
                'timestamp=(SELECT MAX(timestamp) FROM timed_location_data) AND usd_value!=0;',
            )
            return [LocationData(
                time=x[0],
                location=x[1],
                usd_value=x[2],
            ) for x in cursor]

    def get_latest_asset_value_distribution(self) -> list[DBAssetBalance]:
        """Gets the latest asset distribution data

        Returns a list of `DBAssetBalance` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all assets

        This will NOT include liabilities

        The list is sorted by usd value going from higher to lower
        """
        with self.conn.read_ctx() as cursor:
            ignored_asset_ids = self.get_ignored_asset_ids(cursor)
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
                asset = Asset(result[1]).check_existence()
                time = Timestamp(result[0])
                amount = FVal(result[2])
                usd_value = FVal(result[3])
                if asset.identifier in ignored_asset_ids:
                    continue
                # show eth & eth2 as eth in value distribution by asset
                if treat_eth2_as_eth is True and asset in (A_ETH, A_ETH2):
                    eth_balance.time = time
                    eth_balance.amount += amount
                    eth_balance.usd_value += usd_value
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

    def get_tags(self, cursor: 'DBCursor') -> dict[str, Tag]:
        tags_mapping: dict[str, Tag] = {}
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
                    f'Tag {name} with invalid color code found in the DB. {e!s}. Skipping tag',
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
            description: str | None,
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
            log.error(f'Unexpected DB error: {msg} while adding a tag')
            raise

    def edit_tag(
            self,
            write_cursor: 'DBCursor',
            name: str,
            description: str | None,
            background_color: HexColorCode | None,
            foreground_color: HexColorCode | None,
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
            given_data: (
                list[SingleBlockchainAccountData] |
                list[BlockchainAccountData] |
                list[ManuallyTrackedBalance] |
                list[XpubData]
            ),
            action: Literal['adding', 'editing'],
            data_type: Literal['blockchain accounts', 'manually tracked balances', 'bitcoin xpub', 'bitcoin cash xpub'],  # noqa: E501
    ) -> None:
        """Make sure that tags included in the data exist in the DB

        May Raise:
        - TagConstraintError if the tags don't exist in the DB
        """
        existing_tags = self.get_tags(cursor)
        # tag comparison is case-insensitive
        existing_tag_keys = [key.lower() for key in existing_tags]

        unknown_tags: set[str] = set()
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
                    xpub_data.blockchain.value,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Xpub {xpub_data.xpub.xpub} for {xpub_data.blockchain.value} with '
                f'derivation path {xpub_data.derivation_path} is already tracked',
            ) from e

    def delete_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
    ) -> None:
        """Deletes an xpub from the DB. Also deletes all derived addresses and mappings

        May raise:
        - InputError if the xpub does not exist in the DB
        """
        write_cursor.execute(
            'SELECT COUNT(*) FROM xpubs WHERE xpub=? AND derivation_path IS ? AND blockchain=?;',
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )
        if write_cursor.fetchone()[0] == 0:
            derivation_str = (
                'no derivation path' if xpub_data.derivation_path is None else
                f'derivation path {xpub_data.derivation_path}'
            )
            raise InputError(
                f'Tried to remove non existing xpub {xpub_data.xpub.xpub} '
                f'for {xpub_data.blockchain!s} with {derivation_str}',
            )

        # Delete the tag mappings for all derived addresses
        write_cursor.execute(
            'DELETE FROM tag_mappings WHERE '
            'object_reference IN ('
            'SELECT address from xpub_mappings WHERE xpub=? AND derivation_path IS ? AND blockchain IS ?);',  # noqa: E501
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )
        # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None
        key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore
        write_cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
        # Delete any derived addresses
        write_cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=? AND account IN ('
            'SELECT address from xpub_mappings WHERE xpub=? AND derivation_path IS ? AND blockchain=?);',  # noqa: E501
            (
                xpub_data.blockchain.value,
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )
        # And then finally delete the xpub itself
        write_cursor.execute(
            'DELETE FROM xpubs WHERE xpub=? AND derivation_path IS ? AND blockchain=?;',
            (
                xpub_data.xpub.xpub,
                xpub_data.serialize_derivation_path_for_db(),
                xpub_data.blockchain.value,
            ),
        )

    def edit_bitcoin_xpub(self, write_cursor: 'DBCursor', xpub_data: XpubData) -> None:
        """Edit the xpub tags and label

        May raise:
        - InputError if the xpub data already exist
        """
        try:
            write_cursor.execute(
                'SELECT address from xpub_mappings WHERE xpub=? AND derivation_path IS ? AND blockchain=?',  # noqa: E501
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    xpub_data.blockchain.value,
                ),
            )
            addresses_data = [
                BlockchainAccountData(
                    chain=xpub_data.blockchain,
                    address=x[0],
                    tags=xpub_data.tags,
                )
                for x in write_cursor
            ]
            # Update tag mappings of the derived addresses
            replace_tag_mappings(
                write_cursor=write_cursor,
                data=addresses_data,
                object_reference_keys=['address'],
            )
            key = xpub_data.xpub.xpub + xpub_data.serialize_derivation_path_for_db()  # type: ignore
            # Delete the tag mappings for the xpub itself (type ignore is for xpub is not None)
            write_cursor.execute('DELETE FROM tag_mappings WHERE object_reference=?', (key,))
            replace_tag_mappings(
                # if we got tags add them to the xpub
                write_cursor=write_cursor,
                data=[xpub_data],
                object_reference_keys=['xpub.xpub', 'derivation_path'],
            )
            write_cursor.execute(
                'UPDATE xpubs SET label=? WHERE xpub=? AND derivation_path=? AND blockchain=?',
                (
                    xpub_data.label,
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    xpub_data.blockchain.value,
                ),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'There was an error when updating Xpub {xpub_data.xpub.xpub} with '
                f'derivation path {xpub_data.derivation_path}',
            ) from e

    def get_bitcoin_xpub_data(
            self,
            cursor: 'DBCursor',
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> list[XpubData]:
        query = cursor.execute(
            "SELECT A.xpub, A.blockchain, A.derivation_path, A.label, "
            "group_concat(B.tag_name,',') FROM xpubs as A LEFT OUTER JOIN tag_mappings AS B ON "
            "B.object_reference = A.xpub || A.derivation_path WHERE A.blockchain=? GROUP BY A.xpub || A.derivation_path",  # noqa: E501
            (blockchain.value,),
        )
        result = []
        for entry in query:
            tags = deserialize_tags_from_db(entry[4])
            result.append(XpubData(
                xpub=HDKey.from_xpub(entry[0], path='m'),
                blockchain=SupportedBlockchain.deserialize(entry[1]),  # type: ignore
                derivation_path=deserialize_derivation_path_for_db(entry[2]),
                label=entry[3],
                tags=tags,
            ))

        return result

    def get_last_consecutive_xpub_derived_indices(self, cursor: 'DBCursor', xpub_data: XpubData) -> tuple[int, int]:  # noqa: E501
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
                'derivation_path IS ? AND account_index=? AND blockchain = ?;',
                (
                    xpub_data.xpub.xpub,
                    xpub_data.serialize_derivation_path_for_db(),
                    acc_idx,
                    xpub_data.blockchain.value,
                ),
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
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
            addresses: Sequence[BTCAddress],
    ) -> dict[BTCAddress, XpubData]:
        data = {}
        for address in addresses:
            cursor.execute(
                'SELECT B.address, A.xpub, A.derivation_path FROM xpubs as A '
                'LEFT OUTER JOIN xpub_mappings as B '
                'ON B.xpub = A.xpub AND B.derivation_path IS A.derivation_path AND B.blockchain = A.blockchain '  # noqa: E501
                'WHERE B.address=? AND B.blockchain=?;', (address, blockchain.value),
            )
            result = cursor.fetchall()
            if len(result) == 0:
                continue

            data[result[0][0]] = XpubData(
                xpub=HDKey.from_xpub(result[0][1], path='m'),
                blockchain=blockchain,
                derivation_path=deserialize_derivation_path_for_db(result[0][2]),
            )

        return data

    def ensure_xpub_mappings_exist(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
            derived_addresses_data: list[XpubDerivedAddressData],
    ) -> None:
        """Create if not existing the mappings between the addresses and the xpub"""
        tuples = [
            (
                x.address,
                xpub_data.xpub.xpub,
                '' if xpub_data.derivation_path is None else xpub_data.derivation_path,
                x.account_index,
                x.derived_index,
                xpub_data.blockchain.value,
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

    def get_db_info(self, cursor: 'DBCursor') -> dict[str, Any]:
        filepath = self.user_data_dir / USERDB_NAME
        size = Path(self.user_data_dir / USERDB_NAME).stat().st_size
        version = self.get_setting(cursor, 'version')
        return {
            'filepath': str(filepath),
            'size': int(size),
            'version': int(version),
        }

    def get_backups(self) -> list[dict[str, Any]]:
        """Returns a list of tuples with possible backups of the user DB"""
        backups = []
        for root, _, files in os.walk(self.user_data_dir):
            for filename in files:
                match = DB_BACKUP_RE.search(filename)
                if match:
                    timestamp = match.group(1)
                    version = match.group(2)
                    try:
                        size: int | None = Path(Path(root) / filename).stat().st_size
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
            self.user_data_dir / USERDB_NAME,
            new_db_path,
        )
        return new_db_path

    def get_associated_locations(self) -> set[Location]:
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT location FROM margin_positions UNION '
                'SELECT location FROM user_credentials UNION '
                'SELECT location FROM history_events',
            )
            return {Location.deserialize_from_db(loc[0]) for loc in cursor}

    def should_save_balances(
            self,
            cursor: 'DBCursor',
            last_query_ts: Timestamp | None = None,
    ) -> bool:
        """
        Returns whether we should save a balance snapshot depending on whether the last snapshot
        and last query timestamps are older than the period defined by the save frequency setting.
        """
        settings = self.get_settings(cursor)
        # Setting is saved in hours, convert to seconds here
        period = settings.balance_save_frequency * 60 * 60
        now = ts_now()
        if last_query_ts is not None and now - last_query_ts < period:
            return False

        last_save = self.get_last_balance_save_time(cursor)
        return now - last_save > period

    def get_rpc_nodes(
            self,
            blockchain: SupportedBlockchain,
            only_active: bool = False,
    ) -> Sequence[WeightedNode]:
        """
        Get all the nodes in the database. If only_active is set to true only the nodes that
        have the column active set to True will be returned.
        """
        with self.conn.read_ctx() as cursor:
            if only_active:
                cursor.execute('SELECT identifier, name, endpoint, owned, weight, active, blockchain FROM rpc_nodes WHERE (blockchain=? OR name=?) AND active=1 AND (CAST(weight as decimal) != 0 OR owned == 1) ORDER BY name;', (blockchain.value, ETHEREUM_ETHERSCAN_NODE_NAME))  # noqa: E501
            else:
                cursor.execute(
                    'SELECT identifier, name, endpoint, owned, weight, active, blockchain FROM rpc_nodes WHERE (blockchain=? OR NAME=?) ORDER BY name;', (blockchain.value, ETHEREUM_ETHERSCAN_NODE_NAME),  # noqa: E501
                )

            return [
                WeightedNode(
                    identifier=entry[0],
                    node_info=NodeName(
                        name=entry[1],
                        endpoint=entry[2],
                        owned=bool(entry[3]),
                        blockchain=SupportedBlockchain.deserialize(entry[6]) if entry[1] != ETHEREUM_ETHERSCAN_NODE_NAME else blockchain,  # type: ignore  # noqa: E501
                    ),
                    weight=FVal(entry[4]),
                    active=bool(entry[5]),
                )
                for entry in cursor
            ]

    def rebalance_rpc_nodes_weights(
            self,
            write_cursor: 'DBCursor',
            proportion_to_share: FVal,
            exclude_identifier: int | None,
            blockchain: SupportedBlockchain,
    ) -> None:
        """
        Weights for nodes have to be in the range between 0 and 1. This function adjusts the
        weights of all other nodes to keep the proportions correct. After setting a node weight
        to X, the `proportion_to_share` between all remaining nodes becomes `1 - X`.
        exclude_identifier is the identifier of the node whose weight we add or edit.
        In case of deletion it's omitted and `None`is passed.
        """
        if exclude_identifier is None:
            write_cursor.execute('SELECT identifier, weight FROM rpc_nodes WHERE owned=0 AND blockchain=?', (blockchain.value,))  # noqa: E501
        else:
            write_cursor.execute(
                'SELECT identifier, weight FROM rpc_nodes WHERE identifier !=? AND owned=0 AND blockchain=?',  # noqa: E501
                (exclude_identifier, blockchain.value),
            )
        new_weights = []
        nodes_weights = write_cursor.fetchall()
        weight_sum = sum(FVal(node[1]) for node in nodes_weights)
        for node_id, weight in nodes_weights:

            if exclude_identifier:
                new_weight = FVal(weight) / weight_sum * proportion_to_share if weight_sum != ZERO else ZERO  # noqa: E501
            else:
                new_weight = FVal(weight) / weight_sum if weight_sum != ZERO else ZERO
            new_weights.append((str(new_weight), node_id))

        write_cursor.executemany(
            'UPDATE rpc_nodes SET weight=? WHERE identifier=?',
            new_weights,
        )

    def is_etherscan_node(self, node_identifier: int) -> bool:
        """Checks if a given node identifier is the etherscan node"""
        with self.conn.read_ctx() as cursor:
            return bool(cursor.execute(
                "SELECT COUNT(*) FROM rpc_nodes WHERE identifier=? AND endpoint=''",
                (node_identifier,),
            ).fetchone()[0])

    def add_rpc_node(self, node: WeightedNode) -> None:
        """
        Adds a new rpc node.
        """
        with self.user_write() as write_cursor:
            try:
                write_cursor.execute(
                    'INSERT INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',   # noqa: E501
                    node.serialize_for_db(),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(
                    f'Node for {node.node_info.blockchain} with endpoint '
                    f'{node.node_info.endpoint} already exists in db',
                ) from e
            self.rebalance_rpc_nodes_weights(
                write_cursor=write_cursor,
                proportion_to_share=ONE - node.weight,
                exclude_identifier=write_cursor.lastrowid,
                blockchain=node.node_info.blockchain,
            )

    def update_rpc_node(self, node: WeightedNode) -> None:
        """
        Edits an existing rpc node.
        Note: we don't allow editing the blockchain field.
        May raise:
        - InputError if no entry with such
        """
        with self.user_write() as cursor:
            try:
                cursor.execute(
                    'UPDATE rpc_nodes SET name=?, endpoint=?, owned=?, active=?, weight=? WHERE identifier=? AND blockchain=?',  # noqa: E501
                    (
                        node.node_info.name,
                        node.node_info.endpoint,
                        node.node_info.owned,
                        node.active,
                        str(node.weight),
                        node.identifier,
                        node.node_info.blockchain.value,
                    ),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(
                    f'Node for {node.node_info.blockchain} with endpoint '
                    f'{node.node_info.endpoint}  already exists in db',
                ) from e

            if cursor.rowcount == 0:
                raise InputError(f"Node with identifier {node.identifier} doesn't exist")

            self.rebalance_rpc_nodes_weights(
                write_cursor=cursor,
                proportion_to_share=ONE - node.weight,
                exclude_identifier=node.identifier,
                blockchain=node.node_info.blockchain,
            )

    def delete_rpc_node(self, identifier: int, blockchain: SupportedBlockchain) -> None:
        """Delete a rpc node by identifier and blockchain.
        May raise:
        - InputError if no entry with such identifier is in the database.
        """
        with self.user_write() as cursor:
            cursor.execute('DELETE FROM rpc_nodes WHERE identifier=? AND blockchain=?', (identifier, blockchain.value))   # noqa: E501
            if cursor.rowcount == 0:
                raise InputError(f'node with id {identifier} and blockchain {blockchain.value} was not found in the database')  # noqa: E501
            self.rebalance_rpc_nodes_weights(
                write_cursor=cursor,
                proportion_to_share=ONE,
                exclude_identifier=None,
                blockchain=blockchain,
            )

    def get_user_notes(
            self,
            filter_query: UserNotesFilterQuery,
            cursor: 'DBCursor',
            has_premium: bool,
    ) -> list[UserNote]:
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
    ) -> tuple[list[UserNote], int]:
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

    def get_nft_mappings(self, identifiers: list[str]) -> dict[str, dict]:
        """
        Given a list of nft identifiers, return a list of nft info (id, name, collection_name)
        for those identifiers.
        """
        with self.conn.read_ctx() as cursor:
            cursor.execute(
                f'SELECT identifier, name, collection_name, image_url FROM nfts WHERE '
                f'identifier IN ({",".join("?" * len(identifiers))})',
                identifiers,
            )
            serialized_nft_type = AssetType.NFT.serialize()
            return {
                entry[0]: {
                    'name': entry[1],
                    'asset_type': serialized_nft_type,
                    'collection_name': entry[2],
                    'image_url': entry[3],
                } for entry in cursor
            }

    def add_skipped_external_event(
            self,
            write_cursor: 'DBCursor',
            location: Location,
            data: dict[str, Any],
            extra_data: dict[str, Any] | None,
    ) -> None:
        """Add a skipped external event to the DB. Duplicates are ignored."""
        serialized_extra_data = None
        if extra_data is not None:
            serialized_extra_data = json.dumps(extra_data, separators=(',', ':'))
        write_cursor.execute(
            'INSERT OR IGNORE INTO skipped_external_events(data, location, extra_data) VALUES(?, ?, ?)',  # noqa: E501
            (json.dumps(data, separators=(',', ':')), location.serialize_for_db(), serialized_extra_data),  # noqa: E501
        )

    def get_chains_to_detect_evm_accounts(self) -> list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE]:
        """Reads the DB for the excluding chains and calculate which chains to
        perform EVM account detection on"""
        with self.conn.read_ctx() as cursor:
            excluded_chains = self.get_settings(cursor).evmchains_to_skip_detection
        return list(set(SUPPORTED_EVM_EVMLIKE_CHAINS) - set(excluded_chains))
