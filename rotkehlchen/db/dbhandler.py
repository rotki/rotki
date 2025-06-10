import logging
import os
import re
import shutil
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, Literal, Optional, Unpack, overload

from gevent.lock import Semaphore
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, AssetWithOracles, EvmToken
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import (
    BlockchainAccountData,
    BlockchainAccounts,
    SingleBlockchainAccountData,
)
from rotkehlchen.chain.bitcoin.xpub import (
    XpubData,
    XpubDerivedAddressData,
)
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.chain.substrate.types import SubstrateAddress
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.misc import USERDB_NAME
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
    EXTRAINTERNALTXPREFIX,
)
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType, DBCursor
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import UserNotesFilterQuery
from rotkehlchen.db.loopring import DBLoopring
from rotkehlchen.db.misc import detect_sqlcipher_version
from rotkehlchen.db.repositories.accounts import AccountsRepository
from rotkehlchen.db.repositories.assets import AssetsRepository
from rotkehlchen.db.repositories.balances import BalancesRepository
from rotkehlchen.db.repositories.cache import CacheRepository
from rotkehlchen.db.repositories.database_management import DatabaseManagementRepository
from rotkehlchen.db.repositories.exchanges import ExchangeRepository
from rotkehlchen.db.repositories.external_services import ExternalServicesRepository
from rotkehlchen.db.repositories.history_events import HistoryEventsRepository
from rotkehlchen.db.repositories.ignored_actions import IgnoredActionsRepository
from rotkehlchen.db.repositories.manual_balances import ManualBalancesRepository
from rotkehlchen.db.repositories.module_data import ModuleDataRepository
from rotkehlchen.db.repositories.nfts import NFTRepository
from rotkehlchen.db.repositories.query_ranges import QueryRangesRepository
from rotkehlchen.db.repositories.rpc_nodes import RPCNodesRepository
from rotkehlchen.db.repositories.settings import SettingsRepository
from rotkehlchen.db.repositories.tags import TagsRepository
from rotkehlchen.db.repositories.user_notes import UserNotesRepository
from rotkehlchen.db.repositories.xpub import XpubRepository
from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.schema_transient import DB_SCRIPT_CREATE_TRANSIENT_TABLES
from rotkehlchen.db.settings import (
    ROTKEHLCHEN_DB_VERSION,
    ROTKEHLCHEN_TRANSIENT_DB_VERSION,
    DBSettings,
    ModifiableDBSettings,
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
    protect_password_sqlcipher,
)
from rotkehlchen.errors.api import (
    AuthenticationError,
    RotkehlchenPermissionError,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import (
    DBUpgradeError,
    SystemPermissionError,
)
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.exchanges.kraken import KrakenAccountType
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    SUPPORTED_BITCOIN_CHAINS,
    SUPPORTED_EVM_CHAINS_TYPE,
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_EVMLIKE_CHAINS,
    SUPPORTED_EVMLIKE_CHAINS_TYPE,
    SUPPORTED_SUBSTRATE_CHAINS,
    AnyBlockchainAddress,
    ApiKey,
    ApiSecret,
    BlockchainAddress,
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
        # Initialize repositories
        self.settings = SettingsRepository()
        self.cache = CacheRepository()
        self.accounts = AccountsRepository(msg_aggregator)
        self.exchanges = ExchangeRepository()
        self.tags = TagsRepository(msg_aggregator)
        self.manual_balances = ManualBalancesRepository(msg_aggregator)
        self.assets = AssetsRepository(msg_aggregator)
        self.xpub = XpubRepository(msg_aggregator)
        self.external_services: ExternalServicesRepository = None  # type: ignore  # initialized after connection
        self.ignored_actions = IgnoredActionsRepository()
        self.balances = BalancesRepository(msg_aggregator)
        self.query_ranges = QueryRangesRepository()
        self.rpc_nodes = RPCNodesRepository()
        self.user_notes = UserNotesRepository(msg_aggregator)
        self.module_data = ModuleDataRepository()
        self.nfts = NFTRepository()
        self.database_management = DatabaseManagementRepository(user_data_dir, msg_aggregator)
        self.history_events = HistoryEventsRepository(msg_aggregator)
        self.conn: DBConnection = None  # type: ignore
        self.conn_transient: DBConnection = None  # type: ignore
        # Lock to make sure that 2 callers of get_or_create_evm_token do not go in at the same time
        self.get_or_create_evm_token_lock = Semaphore()
        self.password = password
        self._connect()
        # Initialize repositories that need connection
        self.external_services = ExternalServicesRepository(self.conn, msg_aggregator)
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
        return self.settings.get(cursor, name)

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
        self.settings.set(write_cursor, name, value)

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

    def export_unencrypted(self, tempdbfile: 'tempfile._TemporaryFileWrapper[bytes]') -> Path:
        """Export the unencrypted DB to the temppath as plaintext DB

        The critical section is absolutely needed as a context switch
        from inside this execute script can result in:
        1. coming into this code again from another greenlet which can result
        to DB plaintext already in use
        2. Having a DB transaction open between the attach and detach and not
        closed when we detach which will result in DB plaintext locked.

        Returns the Path of the new temp DB file
        """
        tempdbpath = Path(tempdbfile.name)
        tempdbfile.close()  # close the file to allow re-opening by export_unencrypted in windows https://github.com/rotki/rotki/issues/5051  # noqa: E501
        return self.database_management.export_unencrypted(self.conn, tempdbpath)

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
        return self.settings.get_all_settings(cursor, self.msg_aggregator, have_premium)

    def set_settings(self, write_cursor: 'DBCursor', settings: ModifiableDBSettings) -> None:
        self.settings.set_all_settings(write_cursor, settings)

    def get_cache_for_api(self, cursor: 'DBCursor') -> dict[str, int]:
        """Returns a few key-value pairs that are used in the API
        from the `key_value_cache` table of the DB. Defaults to `Timestamp(0)` if not found"""
        return self.cache.get_cache_for_api(cursor)

    def get_static_cache(
            self,
            cursor: 'DBCursor',
            name: DBCacheStatic,
    ) -> Timestamp | None:
        """Returns the cache value from the `key_value_cache` table of the DB
        according to the given `name`. Defaults to `None` if not found"""
        return self.cache.get_static(cursor, name)

    def set_static_cache(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheStatic,
            value: Timestamp,
    ) -> None:
        """Save the name-value pair of the cache with constant name
        to the `key_value_cache` table of the DB"""
        self.cache.set_static(write_cursor, name, value)

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
        return self.cache.get_dynamic(cursor, name, **kwargs)

    def delete_dynamic_cache(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheDynamic,
            **kwargs: str,
    ) -> None:
        """Delete the cache value from the `key_value_cache` table of the DB
        according to the given `name` and `kwargs` if it exists"""
        self.cache.delete_dynamic(write_cursor, name, **kwargs)

    @staticmethod
    def delete_dynamic_caches(
            write_cursor: 'DBCursor',
            key_parts: Sequence[str],
    ) -> None:
        """Delete cache entries whose names start with any of the given `key_parts`"""
        CacheRepository.delete_dynamic_caches(write_cursor, key_parts)

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
        self.cache.set_dynamic(write_cursor, name, value, **kwargs)

    def add_external_service_credentials(
            self,
            write_cursor: 'DBCursor',
            credentials: list[ExternalServiceApiCredentials],
    ) -> None:
        self.external_services.add_credentials(write_cursor, credentials)

    def delete_external_service_credentials(self, services: list[ExternalService]) -> None:
        with self.user_write() as cursor:
            self.external_services.delete_credentials(cursor, services)

    def get_all_external_service_credentials(self) -> list[ExternalServiceApiCredentials]:
        """Returns a list with all the external service credentials saved in the DB"""
        with self.conn.read_ctx() as cursor:
            return self.external_services.get_all_credentials(cursor)

    def get_external_service_credentials(
            self,
            service_name: ExternalService,
    ) -> ExternalServiceApiCredentials | None:
        """If existing it returns the external service credentials for the given service"""
        with self.conn.read_ctx() as cursor:
            return self.external_services.get_credentials(cursor, service_name)

    def add_to_ignored_assets(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        """Add a new asset to the set of ignored assets. If the asset was already marked as
        ignored then we don't do anything. Also ignore history events with this asset.
        """
        self.assets.add_to_ignored(write_cursor, asset)

    def ignore_multiple_assets(self, write_cursor: 'DBCursor', assets: list[str]) -> None:
        """Add the provided identifiers to the list of ignored assets. If any asset was already
        marked as ignored then we don't do anything. Also ignore history events with these assets.
        """
        self.assets.ignore_multiple(write_cursor, assets)

    def remove_from_ignored_assets(self, write_cursor: 'DBCursor', asset: Asset) -> None:
        """Remove an asset from the ignored assets and un-ignore history events with this asset."""
        self.assets.remove_from_ignored(write_cursor, asset)

    def get_ignored_asset_ids(self, cursor: 'DBCursor', only_nfts: bool = False) -> set[str]:
        """Gets the ignored asset ids without converting each one of them to an asset object

        We used to have a heavier version which converted them to an asset but removed
        it due to unnecessary roundtrips to the global DB for each asset initialization
        """
        return self.assets.get_ignored_ids(cursor, only_nfts)

    def add_to_ignored_action_ids(
            self,
            write_cursor: 'DBCursor',
            identifiers: list[str],
    ) -> None:
        """Adds a list of identifiers to be ignored.

        Raises InputError in case of adding already existing ignored action
        """
        self.ignored_actions.add(write_cursor, identifiers)

    def remove_from_ignored_action_ids(
            self,
            write_cursor: 'DBCursor',
            identifiers: list[str],
    ) -> None:
        """Removes a list of identifiers to be ignored.

        Raises InputError in case of removing an action that is not in the DB
        """
        self.ignored_actions.remove(write_cursor, identifiers)

    def get_ignored_action_ids(
            self,
            cursor: 'DBCursor',
    ) -> set[str]:
        return self.ignored_actions.get_all(cursor)

    def add_multiple_balances(self, write_cursor: 'DBCursor', balances: list[DBAssetBalance]) -> None:  # noqa: E501
        """Execute addition of multiple balances in the DB"""
        self.balances.add_multiple_balances(write_cursor, balances)

    def delete_eth2_daily_stats(self, write_cursor: 'DBCursor') -> None:
        """Delete all historical ETH2 eth2_daily_staking_details data"""
        self.module_data.delete_eth2_daily_stats(write_cursor)

    def delete_cowswap_trade_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all cowswap trade/orders data from the DB"""
        self.module_data.delete_cowswap_trade_data(write_cursor)

    def delete_gnosispay_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all saved gnosispay merchant data from the DB"""
        self.module_data.delete_gnosispay_data(write_cursor)

    def purge_module_data(self, module_name: PurgeableModuleName | None) -> None:
        with self.user_write() as cursor:
            self.module_data.purge_module_data(cursor, module_name)

    def delete_loopring_data(self, write_cursor: 'DBCursor') -> None:
        """Delete all loopring related data"""
        self.module_data.delete_loopring_data(write_cursor)

    def get_used_query_range(self, cursor: 'DBCursor', name: str) -> tuple[Timestamp, Timestamp] | None:  # noqa: E501
        """Get the last start/end timestamp range that has been queried for name

        Currently possible names are:
        - {exchange_location_name}_margins_{exchange_name}
        - {location}_history_events_{optional_label}
        - {exchange_location_name}_lending_history_{exchange_name}
        - gnosisbridge_{address}
        """
        return self.query_ranges.get(cursor, name)

    def delete_used_query_range_for_exchange(
            self,
            write_cursor: 'DBCursor',
            location: Location,
            exchange_name: str | None = None,
    ) -> None:
        """Delete the query ranges for the given exchange name"""
        self.query_ranges.delete_for_exchange(write_cursor, location, exchange_name)

    def purge_exchange_data(self, write_cursor: 'DBCursor', location: Location) -> None:
        self.exchanges.purge_exchange_data(write_cursor, location)

    def update_used_query_range(self, write_cursor: 'DBCursor', name: str, start_ts: Timestamp, end_ts: Timestamp) -> None:  # noqa: E501
        self.query_ranges.update(write_cursor, name, start_ts, end_ts)

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
        self.balances.add_multiple_location_data(write_cursor, location_data)

    def add_blockchain_accounts(
            self,
            write_cursor: 'DBCursor',
            account_data: list[BlockchainAccountData],
    ) -> None:
        self.accounts.add(write_cursor, account_data)

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
        self.accounts.edit(write_cursor, account_data)

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

        self.accounts.remove_single_blockchain(write_cursor, blockchain, accounts)

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
        return self.accounts.get_tokens_for_address(cursor, address, blockchain, token_exceptions)

    def save_tokens_for_address(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            blockchain: SupportedBlockchain,
            tokens: Sequence[Asset],
    ) -> None:
        """Saves detected tokens for an address"""
        self.accounts.save_tokens_for_address(write_cursor, address, blockchain, tokens)

    def _deserialize_account_blockchain_from_db(
            self,
            chain_str: str,
            account: str,
    ) -> SupportedBlockchain | None:
        return self.accounts._deserialize_account_blockchain_from_db(chain_str, account)

    def get_blockchains_for_accounts(
            self,
            cursor: 'DBCursor',
            accounts: list[BlockchainAddress],
    ) -> list[tuple[BlockchainAddress, SupportedBlockchain]]:
        """Gets all blockchains for the specified accounts.
        Returns a list of tuples containing the address and blockchain entries.
        """
        return self.accounts.get_blockchains_for_accounts(cursor, accounts)

    def get_evm_accounts(self, cursor: 'DBCursor') -> list[ChecksumEvmAddress]:
        """Returns a list of unique EVM accounts from all EVM chains."""
        return self.accounts.get_evm_accounts(cursor)

    def get_blockchain_accounts(self, cursor: 'DBCursor') -> BlockchainAccounts:
        """Returns a Blockchain accounts instance containing all blockchain account addresses"""
        return self.accounts.get_all(cursor)

    def get_blockchain_account_data(
            self,
            cursor: 'DBCursor',
            blockchain: SupportedBlockchain,
    ) -> list[SingleBlockchainAccountData]:
        """Returns account data for a particular blockchain.

        Each account entry contains address and potentially label and tags
        """
        return self.accounts.get_account_data(cursor, blockchain)

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
        return self.accounts.get_single_addresses(cursor, blockchain)

    def get_manually_tracked_balances(
            self,
            cursor: 'DBCursor',
            balance_type: BalanceType | None = BalanceType.ASSET,
            include_entries_with_missing_assets: bool = False,
    ) -> list[ManuallyTrackedBalance]:
        """Returns the manually tracked balances from the DB"""
        return self.manual_balances.get_all(
            cursor, balance_type, include_entries_with_missing_assets,
        )

    def add_manually_tracked_balances(self, write_cursor: 'DBCursor', data: list[ManuallyTrackedBalance]) -> None:  # noqa: E501
        """Adds manually tracked balances in the DB

        May raise:
        - InputError if one of the given balance entries already exist in the DB
        """
        self.manual_balances.add(write_cursor, data)

    def edit_manually_tracked_balances(self, write_cursor: 'DBCursor', data: list[ManuallyTrackedBalance]) -> None:  # noqa: E501
        """Edits manually tracked balances

        Edits the manually tracked balances for each of the given balance labels.

        At this point in the calling chain we should already know that:
        - All tags exist in the DB

        May raise:
        - InputError if any of the manually tracked balance labels to edit do not
        exist in the DB
        """
        self.manual_balances.edit(write_cursor, data)

    def remove_manually_tracked_balances(self, write_cursor: 'DBCursor', ids: list[int]) -> None:
        """
        Removes manually tracked balances for the given ids

        May raise:
        - InputError if any of the given manually tracked balance labels
        to delete did not exist
        """
        self.manual_balances.remove(write_cursor, ids)

    def save_balances_data(self, write_cursor: 'DBCursor', data: dict[str, Any], timestamp: Timestamp) -> None:  # noqa: E501
        """The keys of the data dictionary can be any kind of asset plus 'location'
        and 'net_usd'. This gives us the balance data per assets, the balance data
        per location and finally the total balance

        The balances are saved in the DB at the given timestamp
        """
        self.balances.save_balances_data(write_cursor, data, timestamp)

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
        with self.user_write() as cursor:
            self.exchanges.add(
                cursor,
                name,
                location,
                api_key,
                api_secret,
                passphrase,
                kraken_account_type,
                binance_selected_trade_pairs,
            )

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
        self.exchanges.edit(
            write_cursor,
            name,
            location,
            new_name,
            api_key,
            api_secret,
            passphrase,
            kraken_account_type,
            binance_selected_trade_pairs,
        )

    def remove_exchange(self, write_cursor: 'DBCursor', name: str, location: Location) -> None:
        """
        Removes the exchange location from user_credentials and from
        `the non_syncing_exchanges`setting.
        """
        self.exchanges.remove(write_cursor, name, location)

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
        return self.exchanges.get_credentials(cursor, location, name)

    def get_exchange_credentials_extras(self, name: str, location: Location) -> dict[str, Any]:
        """Returns any extra settings for a particular exchange key credentials"""
        with self.conn.read_ctx() as cursor:
            return self.exchanges.get_credentials_extras(cursor, name, location)

    def set_binance_pairs(self, write_cursor: 'DBCursor', name: str, pairs: list[str], location: Location) -> None:  # noqa: E501
        """Sets the market pairs used by the user on a specific binance exchange"""
        self.exchanges.set_binance_pairs(write_cursor, name, pairs, location)

    def get_binance_pairs(self, name: str, location: Location) -> list[str]:
        """Gets the market pairs used by the user on a specific binance exchange"""
        with self.conn.read_ctx() as cursor:
            return self.exchanges.get_binance_pairs(cursor, name, location)

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
                    tx_hash_idx, chain_id_idx = 6, 7
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
                self.write_single_tuple(
                    write_cursor=write_cursor,
                    tuple_type=tuple_type,
                    query=query,
                    entry=entry,
                    relevant_address=relevant_address,
                )
        except OverflowError:
            self.msg_aggregator.add_error(
                f'Failed to add "{tuple_type}" to the DB with overflow error. '
                f'Check the logs for more details',
            )
            log.error(
                f'Overflow error while trying to add "{tuple_type}" tuples to the'
                f' DB. Tuples: {tuples} with query: {query}',
            )

    @staticmethod
    def write_single_tuple(
            write_cursor: 'DBCursor',
            tuple_type: DBTupleType,
            query: str,
            entry: tuple[Any, ...],
            relevant_address: ChecksumEvmAddress | None,
    ) -> int | None:
        """Helper to write an entry of a tuple type and handle address mapping"""
        try:
            write_cursor.execute(query, entry)
            if tuple_type == 'evm_transaction':
                tx_id = write_cursor.execute(
                    'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                    (entry[0], entry[1]),
                ).fetchone()[0]

                # add address mapping if relevant_address is provided and transaction exists
                if relevant_address is not None and tx_id is not None:
                    write_cursor.execute(
                        'INSERT OR IGNORE INTO evmtx_address_mappings(tx_id, address) VALUES (?, ?)',  # noqa: E501
                        (tx_id, relevant_address),
                    )

                return tx_id  # return the transaction id (new or existing)
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            string_repr = db_tuple_to_str(entry, tuple_type)
            log.warning(
                f'Did not add "{string_repr}" to the DB due to "{e!s}".'
                f'Some other constraint was hit.',
            )
        except sqlcipher.InterfaceError:  # pylint: disable=no-member
            log.critical(f'Interface error with tuple: {entry}')

        return None

    def add_margin_positions(self, write_cursor: 'DBCursor', margin_positions: list[MarginPosition]) -> None:  # noqa: E501
        self.history_events.add_margin_positions(write_cursor, margin_positions)

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
        return self.balances.get_margin_positions(cursor, from_ts, to_ts, location)

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
                'DELETE FROM multisettings WHERE name LIKE ? ESCAPE ? AND value = ?',
                ('queried\\_address\\_%', '\\', address),
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
            'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ? AND value = ?',
            (f'{EXTRAINTERNALTXPREFIX}\\_{blockchain.to_chain_id().value}%', '\\', address),
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
        self.external_services.set_rotkehlchen_premium(credentials)

    def delete_premium_credentials(self) -> bool:
        """Delete the rotki premium credentials in the DB for the logged-in user"""
        with self.user_write() as cursor:
            return self.external_services.delete_premium_credentials(cursor)

    def get_rotkehlchen_premium(self, cursor: 'DBCursor') -> PremiumCredentials | None:
        return self.external_services.get_rotkehlchen_premium(cursor)

    def get_netvalue_data(
            self,
            from_ts: Timestamp,
            include_nfts: bool = True,
    ) -> tuple[list[str], list[str]]:
        """Get all entries of net value data from the DB"""
        with self.conn.read_ctx() as cursor:
            return self.history_events.get_netvalue_data(cursor, from_ts, include_nfts)

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
        settings = self.get_settings(cursor)
        balances = self.balances.query_timed_balances(
            cursor, asset, balance_type, from_ts, to_ts, settings,
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
        return self.assets.query_owned(cursor)

    def update_owned_assets_in_globaldb(self, cursor: 'DBCursor') -> None:
        """Makes sure all owned assets of the user are in the Global DB"""
        self.assets.update_owned_in_globaldb(cursor)

    def add_asset_identifiers(self, write_cursor: 'DBCursor', asset_identifiers: list[str]) -> None:  # noqa: E501
        """Adds an asset to the user db asset identifier table"""
        self.assets.add_identifiers(write_cursor, asset_identifiers)

    def sync_globaldb_assets(self, write_cursor: 'DBCursor') -> None:
        """Makes sure that:
        - all the GlobalDB asset identifiers are mirrored in the user DB
        - all the assets set to have the SPAM_PROTOCOL in the global DB
        are set to be part of the user's ignored list
        """
        self.assets.sync_globaldb(write_cursor)

    def delete_asset_identifier(self, write_cursor: 'DBCursor', asset_id: str) -> None:
        """Deletes an asset identifier from the user db asset identifier table

        May raise:
        - InputError if a foreign key error is encountered during deletion
        """
        self.assets.delete_identifier(write_cursor, asset_id)

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
                # First merge any timed_balances entries
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
                # Now replace in assets table and other tables
                self.assets.replace_identifier(write_cursor, source_identifier, target_asset)

    def get_latest_location_value_distribution(self) -> list[LocationData]:
        """Gets the latest location data

        Returns a list of `LocationData` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all locations
        """
        with self.conn.read_ctx() as cursor:
            return self.history_events.get_latest_location_value_distribution(cursor)

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
            return self.history_events.get_latest_asset_value_distribution(
                cursor,
                ignored_asset_ids,
                treat_eth2_as_eth,
            )

    def get_tags(self, cursor: 'DBCursor') -> dict[str, Tag]:
        return self.tags.get_all(cursor)

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
        self.tags.add(write_cursor, name, description, background_color, foreground_color)

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
        self.tags.edit(write_cursor, name, description, background_color, foreground_color)

    def delete_tag(self, write_cursor: 'DBCursor', name: str) -> None:
        """Deletes a tag already existing in the DB

        Raises:
        - TagConstraintError: If the tag name to delete does not exist in the DB
        """
        self.tags.delete(write_cursor, name)

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
        self.tags.ensure_tags_exist(cursor, given_data, action, data_type)

    def add_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
    ) -> None:
        """Add the xpub to the DB

        May raise:
        - InputError if the xpub data already exist
        """
        self.xpub.add(write_cursor, xpub_data)

    def delete_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
    ) -> None:
        """Deletes an xpub from the DB. Also deletes all derived addresses and mappings

        May raise:
        - InputError if the xpub does not exist in the DB
        """
        self.xpub.delete(write_cursor, xpub_data)

    def edit_bitcoin_xpub(self, write_cursor: 'DBCursor', xpub_data: XpubData) -> None:
        """Edit the xpub tags and label

        May raise:
        - InputError if the xpub data already exist
        """
        self.xpub.edit(write_cursor, xpub_data)

    def get_bitcoin_xpub_data(
            self,
            cursor: 'DBCursor',
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> list[XpubData]:
        return self.xpub.get_all(cursor, blockchain)

    def get_last_consecutive_xpub_derived_indices(self, cursor: 'DBCursor', xpub_data: XpubData) -> tuple[int, int]:  # noqa: E501
        """
        Get the last known receiving and change derived indices from the given
        xpub that are consecutive since the beginning.

        For example if we have derived indices 0, 1, 4, 5 then this will return 1.

        This tells us from where to start deriving again safely
        """
        return self.xpub.get_last_consecutive_derived_indices(cursor, xpub_data)

    def get_addresses_to_xpub_mapping(
            self,
            cursor: 'DBCursor',
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
            addresses: Sequence[BTCAddress],
    ) -> dict[BTCAddress, XpubData]:
        return self.xpub.get_addresses_to_xpub_mapping(cursor, blockchain, addresses)

    def ensure_xpub_mappings_exist(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
            derived_addresses_data: list[XpubDerivedAddressData],
    ) -> None:
        """Create if not existing the mappings between the addresses and the xpub"""
        self.xpub.ensure_mappings_exist(write_cursor, xpub_data, derived_addresses_data)

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
        return self.database_management.create_db_backup(self.conn, version)

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
            return self.rpc_nodes.get_rpc_nodes(cursor, blockchain, only_active)

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
        self.rpc_nodes.rebalance_weights(
            write_cursor,
            proportion_to_share,
            exclude_identifier,
            blockchain,
        )

    def add_rpc_node(self, node: WeightedNode) -> None:
        """
        Adds a new rpc node.
        """
        with self.user_write() as write_cursor:
            self.rpc_nodes.add_rpc_node(write_cursor, node)

    def update_rpc_node(self, node: WeightedNode) -> None:
        """
        Edits an existing rpc node.
        Note: we don't allow editing the blockchain field.
        May raise:
        - InputError if no entry with such
        """
        with self.user_write() as cursor:
            self.rpc_nodes.update_rpc_node(cursor, node)

    def delete_rpc_node(self, identifier: int, blockchain: SupportedBlockchain) -> None:
        """Delete a rpc node by identifier and blockchain.
        May raise:
        - InputError if no entry with such identifier is in the database.
        """
        with self.user_write() as cursor:
            self.rpc_nodes.delete_rpc_node(cursor, identifier, blockchain)

    def get_user_notes(
            self,
            filter_query: UserNotesFilterQuery,
            cursor: 'DBCursor',
            has_premium: bool,
    ) -> list[UserNote]:
        """Returns all the notes created by a user filtered by the given filter"""
        return self.user_notes.get_notes(cursor, filter_query, has_premium)

    def get_user_notes_and_limit_info(
            self,
            filter_query: UserNotesFilterQuery,
            cursor: 'DBCursor',
            has_premium: bool,
    ) -> tuple[list[UserNote], int]:
        """Gets all user_notes for the query from the DB

        Also returns how many are the total found for the filter
        """
        return self.user_notes.get_notes_and_limit_info(cursor, filter_query, has_premium)

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
            return self.user_notes.add(
                write_cursor, title, content, location, is_pinned, has_premium,
            )

    def edit_user_note(self, user_note: UserNote) -> None:
        """Edit an already existing user_note entry's content.
        May raise:
        - InputError if editing a user note that does not exist.
        """
        with self.user_write() as write_cursor:
            self.user_notes.update(write_cursor, user_note)

    def delete_user_note(self, identifier: int) -> None:
        """Delete user note entry from the DB.
        May raise:
        - InputError if identifier not present in DB.
        """
        with self.user_write() as write_cursor:
            self.user_notes.delete(write_cursor, identifier)

    def get_nft_mappings(self, identifiers: list[str]) -> dict[str, dict]:
        """
        Given a list of nft identifiers, return a list of nft info (id, name, collection_name)
        for those identifiers.
        """
        with self.conn.read_ctx() as cursor:
            return self.nfts.get_nft_mappings(cursor, identifiers)

    def add_skipped_external_event(
            self,
            write_cursor: 'DBCursor',
            location: Location,
            data: dict[str, Any],
            extra_data: dict[str, Any] | None,
    ) -> None:
        """Add a skipped external event to the DB. Duplicates are ignored."""
        self.database_management.add_skipped_external_event(
            write_cursor,
            location,
            data,
            extra_data,
        )

    def get_chains_to_detect_evm_accounts(self) -> list[SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE]:
        """Reads the DB for the excluding chains and calculate which chains to
        perform EVM account detection on"""
        with self.conn.read_ctx() as cursor:
            excluded_chains = self.get_settings(cursor).evmchains_to_skip_detection
        return list(set(SUPPORTED_EVM_EVMLIKE_CHAINS) - set(excluded_chains))
