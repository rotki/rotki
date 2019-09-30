import hashlib
import logging
import os
import re
import shutil
import tempfile
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from pysqlcipher3 import dbapi2 as sqlcipher
from typing_extensions import Literal

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants.assets import A_USD, S_BTC, S_ETH, S_USD
from rotkehlchen.constants.timing import YEAR_IN_SECONDS
from rotkehlchen.datatyping import BalancesData, DBSettings
from rotkehlchen.db.upgrade_manager import DBUpgradeManager
from rotkehlchen.db.utils import (
    DB_SCRIPT_CREATE_TABLES,
    DB_SCRIPT_REIMPORT_DATA,
    ROTKEHLCHEN_DB_VERSION,
    AssetBalance,
    BlockchainAccounts,
    DBStartupAction,
    LocationData,
    SingleAssetBalance,
)
from rotkehlchen.errors import AuthenticationError, DeserializationError, InputError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_movement_category_from_db,
    deserialize_fee,
    deserialize_fval,
    deserialize_location,
    deserialize_location_from_db,
    deserialize_price,
    deserialize_timestamp,
    deserialize_trade_type_from_db,
)
from rotkehlchen.typing import (
    ApiCredentials,
    ApiKey,
    ApiSecret,
    BlockchainAddress,
    ChecksumAddress,
    EthereumTransaction,
    FiatAsset,
    FilePath,
    Location,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


DEFAULT_TAXFREE_AFTER_PERIOD = YEAR_IN_SECONDS
DEFAULT_INCLUDE_CRYPTO2CRYPTO = True
DEFAULT_INCLUDE_GAS_COSTS = True
DEFAULT_ANONYMIZED_LOGS = False
DEFAULT_PREMIUM_SHOULD_SYNC = False
DEFAULT_START_DATE = "01/08/2015"
DEFAULT_UI_FLOATING_PRECISION = 2
DEFAULT_BALANCE_SAVE_FREQUENCY = 24
DEFAULT_MAIN_CURRENCY = S_USD
DEFAULT_DATE_DISPLAY_FORMAT = '%d/%m/%Y %H:%M:%S %Z'
KDF_ITER = 64000
DBINFO_FILENAME = 'dbinfo.json'

DBTupleType = Literal['trade', 'asset_movement', 'margin_position', 'ethereum_transaction']


def str_to_bool(s):
    return True if s == 'True' else False


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
            f'{deserialize_trade_type_from_db(data[4])} trade with id {data[0]} '
            f'in {deserialize_location_from_db(data[2])} and pair {data[3]} '
            f'at timestamp {data[1]}'
        )
    elif tuple_type == 'asset_movement':
        return (
            f'{deserialize_asset_movement_category_from_db(data[2])} of '
            f' {data[4]} with id {data[0]} '
            f'in {deserialize_location_from_db(data[1])} at timestamp {data[3]}'
        )
    elif tuple_type == 'margin_position':
        return (
            f'Margin position with id {data[0]} in  {deserialize_location_from_db(data[1])} '
            f'for {data[5]} closed at timestamp {data[3]}'
        )
    elif tuple_type == 'ethereum_transaction':
        return f'Ethereum transaction with hash "{data[0].hex()}"'

    raise AssertionError('db_tuple_to_str() called with invalid tuple_type {tuple_type}')


# https://stackoverflow.com/questions/4814167/storing-time-series-data-relational-or-non
# http://www.sql-join.com/sql-join-types
class DBHandler():

    def __init__(self, user_data_dir: FilePath, password: str, msg_aggregator: MessagesAggregator):
        self.msg_aggregator = msg_aggregator
        self.user_data_dir = user_data_dir
        self.sqlcipher_version = detect_sqlcipher_version()
        action = self.read_info_at_start()
        if action == DBStartupAction.UPGRADE_3_4:
            result, msg = self.upgrade_db_sqlcipher_3_to_4(password)
            if not result:
                log.error(
                    'dbinfo determined we need an upgrade from sqlcipher version '
                    '3 to version 4 but the upgrade failed.',
                    error=msg,
                )
                raise AuthenticationError(msg)
        elif action == DBStartupAction.STUCK_4_3:
            msg = (
                'dbinfo determined we are using sqlcipher version 3 but the '
                'database has already been upgraded to version 4. Please find a '
                'rotkehlchen binary that uses sqlcipher version 4 to open the '
                'database'
            )
            log.error(msg)
            raise AuthenticationError(msg)
        else:
            self.connect(password)

        try:
            self.conn.executescript(DB_SCRIPT_CREATE_TABLES)
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            migrated = False
            errstr = str(e)
            if self.sqlcipher_version == 4:
                migrated, errstr = self.upgrade_db_sqlcipher_3_to_4(password)

            if self.sqlcipher_version != 4 or not migrated:
                errstr = (
                    'Wrong password while decrypting the database or not a database. Perhaps '
                    'trying to use an sqlcipher 4 version DB with sqlciper 3?'
                )
                raise AuthenticationError(
                    f'SQLCipher version: {self.sqlcipher_version} - {errstr}',
                )

        # Run upgrades if needed
        DBUpgradeManager(self).run_upgrades()

    def __del__(self):
        self.disconnect()
        dbinfo = {'sqlcipher_version': self.sqlcipher_version, 'md5_hash': self.get_md5hash()}
        with open(os.path.join(self.user_data_dir, DBINFO_FILENAME), 'w') as f:
            f.write(rlk_jsondumps(dbinfo))

    def get_md5hash(self) -> str:
        no_active_connection = not hasattr(self, 'conn') or not self.conn
        assert no_active_connection, 'md5hash should be taken only with a closed DB'
        filename = os.path.join(self.user_data_dir, 'rotkehlchen.db')
        md5_hash = hashlib.md5()
        with open(filename, 'rb') as f:
            # Read and update hash in chunks of 4K
            for byte_block in iter(lambda: f.read(4096), b''):
                md5_hash.update(byte_block)

        return md5_hash.hexdigest()

    def read_info_at_start(self) -> DBStartupAction:
        dbinfo = None
        action = DBStartupAction.NOTHING
        filepath = os.path.join(self.user_data_dir, DBINFO_FILENAME)

        if not os.path.exists(filepath):
            return action

        with open(filepath, 'r') as f:
            try:
                dbinfo = rlk_jsonloads_dict(f.read())
            except JSONDecodeError:
                log.warning('dbinfo.json file is corrupt. Does not contain expected keys')
                return action
        current_md5_hash = self.get_md5hash()

        if not dbinfo:
            return action

        if 'sqlcipher_version' not in dbinfo or 'md5_hash' not in dbinfo:
            log.warning('dbinfo.json file is corrupt. Does not contain expected keys')
            return action

        if dbinfo['md5_hash'] != current_md5_hash:
            log.warning(
                'dbinfo.json contains an outdated hash. Was data changed outside the program?',
            )
            return action

        if dbinfo['sqlcipher_version'] == 3 and self.sqlcipher_version == 3:
            return DBStartupAction.NOTHING

        if dbinfo['sqlcipher_version'] == 4 and self.sqlcipher_version == 4:
            return DBStartupAction.NOTHING

        if dbinfo['sqlcipher_version'] == 3 and self.sqlcipher_version == 4:
            return DBStartupAction.UPGRADE_3_4

        if dbinfo['sqlcipher_version'] == 4 and self.sqlcipher_version == 3:
            return DBStartupAction.STUCK_4_3

        raise ValueError('Unexpected values at dbinfo.json')

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

    def connect(self, password: str) -> None:
        self.conn = sqlcipher.connect(  # pylint: disable=no-member
            os.path.join(self.user_data_dir, 'rotkehlchen.db'),
        )
        self.conn.text_factory = str
        self.conn.executescript('PRAGMA key="{}";'.format(password))
        if self.sqlcipher_version == 3:
            script = f'PRAGMA key="{password}"; PRAGMA kdf_iter={KDF_ITER};'
            self.conn.executescript(script)
        self.conn.execute('PRAGMA foreign_keys=ON')

    def upgrade_db_sqlcipher_3_to_4(self, password):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            self.conn = None

        self.connect(password)
        success = True
        msg = ''
        self.conn.text_factory = str
        script = f'PRAGMA KEY="{password}";PRAGMA cipher_migrate;'
        try:
            self.conn.executescript(script)
            self.conn.executescript(DB_SCRIPT_CREATE_TABLES)
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            msg = str(e)
            success = False

        return success, msg

    def disconnect(self):
        self.conn.close()
        self.conn = None

    def reimport_all_tables(self) -> None:
        """Useful only when some table's column data type was modified and you
        need to re-import all data. Should only be used if you know what you are
        doing. For normal database upgrades the proper scripts should be used"""
        self.conn.executescript(DB_SCRIPT_REIMPORT_DATA)

    def export_unencrypted(self, temppath: FilePath):
        self.conn.executescript(
            'ATTACH DATABASE "{}" AS plaintext KEY "";'
            'SELECT sqlcipher_export("plaintext");'
            'DETACH DATABASE plaintext;'.format(temppath),
        )

    def import_unencrypted(self, unencrypted_db_data: bytes, password: str) -> None:
        self.disconnect()
        rdbpath = os.path.join(self.user_data_dir, 'rotkehlchen.db')
        # Make copy of existing encrypted DB before removing it
        shutil.copy2(
            rdbpath,
            os.path.join(self.user_data_dir, 'rotkehlchen_temp_backup.db'),
        )
        os.remove(rdbpath)

        # dump the unencrypted data into a temporary file
        with tempfile.TemporaryDirectory() as tmpdirname:
            tempdbpath = os.path.join(tmpdirname, 'temp.db')
            with open(tempdbpath, 'wb') as f:
                f.write(unencrypted_db_data)

            # Now attach to the unencrypted DB and copy it to our DB and encrypt it
            self.conn = sqlcipher.connect(tempdbpath)  # pylint: disable=no-member
            script = f'ATTACH DATABASE "{rdbpath}" AS encrypted KEY "{password}";'
            if self.sqlcipher_version == 3:
                script += f'PRAGMA encrypted.kdf_iter={KDF_ITER};'
            script += 'SELECT sqlcipher_export("encrypted");DETACH DATABASE encrypted;'
            self.conn.executescript(script)
            self.disconnect()

        self.connect(password)
        # all went okay, remove the original temp backup
        os.remove(os.path.join(self.user_data_dir, 'rotkehlchen_temp_backup.db'))

    def update_last_write(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('last_write_ts', str(ts_now())),
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
        self.conn.commit()

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
        self.conn.commit()

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

    def get_settings(self) -> DBSettings:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT name, value FROM settings;',
        )
        query = query.fetchall()

        settings: DBSettings = {}
        for q in query:
            if q[0] == 'version':
                settings['db_version'] = int(q[1])
            elif q[0] == 'last_write_ts':
                settings['last_write_ts'] = int(q[1])
            elif q[0] == 'premium_should_sync':
                settings['premium_should_sync'] = str_to_bool(q[1])
            elif q[0] == 'include_crypto2crypto':
                settings['include_crypto2crypto'] = str_to_bool(q[1])
            elif q[0] == 'anonymized_logs':
                settings['anonymized_logs'] = str_to_bool(q[1])
            elif q[0] == 'last_data_upload_ts':
                settings['last_data_upload_ts'] = int(q[1])
            elif q[0] == 'ui_floating_precision':
                settings['ui_floating_precision'] = int(q[1])
            elif q[0] == 'taxfree_after_period':
                settings['taxfree_after_period'] = int(q[1]) if q[1] else None
            elif q[0] == 'balance_save_frequency':
                settings['balance_save_frequency'] = int(q[1])
            elif q[0] == 'include_gas_costs':
                settings['include_gas_costs'] = str_to_bool(q[1])
            else:
                settings[q[0]] = q[1]

        # populate defaults for values not in the DB yet
        if 'historical_data_start' not in settings:
            settings['historical_data_start'] = DEFAULT_START_DATE
        if 'eth_rpc_endpoint' not in settings:
            settings['eth_rpc_endpoint'] = 'http://localhost:8545'
        if 'ui_floating_precision' not in settings:
            settings['ui_floating_precision'] = DEFAULT_UI_FLOATING_PRECISION
        if 'include_crypto2crypto' not in settings:
            settings['include_crypto2crypto'] = DEFAULT_INCLUDE_CRYPTO2CRYPTO
        if 'taxfree_after_period' not in settings:
            settings['taxfree_after_period'] = DEFAULT_TAXFREE_AFTER_PERIOD
        if 'balance_save_frequency' not in settings:
            settings['balance_save_frequency'] = DEFAULT_BALANCE_SAVE_FREQUENCY
        if 'main_currency' not in settings:
            settings['main_currency'] = DEFAULT_MAIN_CURRENCY
        if 'anonymized_logs' not in settings:
            settings['anonymized_logs'] = DEFAULT_ANONYMIZED_LOGS
        if 'include_gas_costs' not in settings:
            settings['include_gas_costs'] = DEFAULT_INCLUDE_GAS_COSTS
        if 'date_display_format' not in settings:
            settings['date_display_format'] = DEFAULT_DATE_DISPLAY_FORMAT
        if 'premium_should_sync' not in settings:
            settings['premium_should_sync'] = DEFAULT_PREMIUM_SHOULD_SYNC
        if 'last_write_ts' not in settings:
            settings['last_write_ts'] = 0
        if 'last_data_upload_ts' not in settings:
            settings['last_data_upload_ts'] = 0

        # populate values that are not saved in the setting but computed and returned
        # as part of the get_settings call
        settings['last_balance_save'] = self.get_last_balance_save_time()

        return settings

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

    def set_main_currency(self, currency: FiatAsset) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('main_currency', currency),
        )
        self.conn.commit()
        self.update_last_write()

    def set_settings(self, settings: DBSettings) -> None:
        cursor = self.conn.cursor()
        cursor.executemany(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            [setting for setting in list(settings.items())],
        )
        self.conn.commit()
        self.update_last_write()

    def add_to_ignored_assets(self, asset: Asset) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO multisettings(name, value) VALUES(?, ?)',
            ('ignored_asset', asset.identifier),
        )
        self.conn.commit()

    def remove_from_ignored_assets(self, asset: Asset) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM multisettings WHERE name="ignored_asset" AND value=?;',
            (asset.identifier,),
        )
        self.conn.commit()

    def get_ignored_assets(self) -> List[Asset]:
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT value FROM multisettings WHERE name="ignored_asset";',
        )
        return [Asset(q[0]) for q in cursor]

    def add_multiple_balances(self, balances: List[AssetBalance]) -> None:
        """Execute addition of multiple balances in the DB"""
        cursor = self.conn.cursor()

        for entry in balances:
            cursor.execute(
                'INSERT INTO timed_balances('
                '    time, currency, amount, usd_value) '
                ' VALUES(?, ?, ?, ?)',
                (entry.time, entry.asset.identifier, entry.amount, entry.usd_value),
            )
        self.conn.commit()
        self.update_last_write()

    def get_last_query_time(self, name: str) -> Timestamp:
        cursor = self.conn.cursor()
        query = cursor.execute(f'SELECT value from last_timestamps WHERE name="{name}";')
        query = query.fetchall()
        if len(query) == 0 or query[0][0] is None:
            return Timestamp(0)

        return Timestamp(int(query[0][0]))

    def update_last_query_time(self, name: str, ts: Timestamp) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO last_timestamps(name, value) VALUES (?, ?)',
            (name, str(ts)),
        )
        self.conn.commit()
        self.update_last_write()

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
            cursor.execute(
                'INSERT INTO timed_location_data('
                '    time, location, usd_value) '
                ' VALUES(?, ?, ?)',
                (entry.time, entry.location, entry.usd_value),
            )
        self.conn.commit()
        self.update_last_write()

    def write_owned_tokens(self, tokens: List[EthereumToken]) -> None:
        """Execute addition of multiple tokens in the DB

        tokens should be a list of token symbols"""
        cursor = self.conn.cursor()
        # Delete previous list and write the new one
        cursor.execute(
            'DELETE FROM multisettings WHERE name="eth_token";',
        )
        cursor.executemany(
            'INSERT INTO multisettings(name,value) VALUES (?, ?)',
            [('eth_token', t.identifier) for t in tokens],
        )
        self.conn.commit()
        self.update_last_write()

    def get_owned_tokens(self) -> List[EthereumToken]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT value FROM multisettings WHERE name="eth_token";',
        )
        result = []
        for q in query:
            try:
                result.append(EthereumToken(q[0]))
            except UnknownAsset:
                self.msg_aggregator.add_warning(
                    f'Unknown/unsupported asset {q[0]} found in the database. '
                    f'If you believe this should be supported open an issue in github',
                )
                continue
            except DeserializationError:
                self.msg_aggregator.add_error(
                    f'Non-string type asset: {type(q[0])} found in the database. Ignoring it.',
                )
                continue

        return result

    def add_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
            (blockchain.value, account),
        )
        self.conn.commit()
        self.update_last_write()

    def remove_blockchain_account(
            self,
            blockchain: SupportedBlockchain,
            account: BlockchainAddress,
    ) -> None:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT COUNT(*) from blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', (blockchain.value, account),
        )
        query = query.fetchall()
        if query[0][0] == 0:
            raise InputError(
                'Tried to remove non-existing {} account {}'.format(blockchain, account),
            )

        cursor.execute(
            'DELETE FROM blockchain_accounts WHERE '
            'blockchain = ? and account = ?;', (blockchain.value, account),
        )
        self.conn.commit()
        self.update_last_write()

    def add_fiat_balance(self, currency: Asset, amount: FVal) -> None:
        assert currency.is_fiat()
        cursor = self.conn.cursor()
        # We don't care about previous value so this simple insert or replace should work
        cursor.execute(
            'INSERT OR REPLACE INTO current_balances(asset, amount) VALUES (?, ?)',
            (currency.identifier, str(amount)),
        )
        self.conn.commit()
        self.update_last_write()

    def remove_fiat_balance(self, currency: Asset) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM current_balances WHERE asset = ?;', (currency.identifier,),
        )
        self.conn.commit()
        self.update_last_write()

    def get_fiat_balances(self) -> Dict[Asset, str]:
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT asset, amount FROM current_balances;',
        )

        result = {}
        for entry in query:
            try:
                result[Asset(entry[0])] = entry[1]
            except UnknownAsset:
                self.msg_aggregator.add_error(
                    f'Unknown FIAT asset {entry[0]} found in the DB. Skipping it ...',
                )
                continue
            except DeserializationError:
                # This can't really happen. DB always returns a string. Should I have this here?
                self.msg_aggregator.add_error(
                    f'FIAT asset with non-string type {type(entry[0])} '
                    f'found in the DB. Skipping it ...',
                )
                continue

        return result

    def get_blockchain_accounts(self) -> BlockchainAccounts:
        """Returns a Blockchain accounts instance"""
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT blockchain, account FROM blockchain_accounts;',
        )
        query = query.fetchall()

        eth_list = list()
        btc_list = list()

        for entry in query:
            if entry[0] == S_ETH:
                eth_list.append(entry[1])
            elif entry[0] == S_BTC:
                btc_list.append(entry[1])
            else:
                log.warning(
                    f'unknown blockchain type {entry[0]} found in DB. Ignoring...',
                )

        return BlockchainAccounts(eth=eth_list, btc=btc_list)

    def remove(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS timed_balances')
        cursor.execute('DROP TABLE IF EXISTS timed_location_data')
        cursor.execute('DROP TABLE IF EXISTS timed_unique_data')
        self.conn.commit()

    def write_balances_data(self, data: BalancesData, timestamp: Timestamp) -> None:
        """ The keys of the data dictionary can be any kind of asset plus 'location'
        and 'net_usd'. This gives us the balance data per assets, the balance data
        per location and finally the total balance

        The balances are saved in the DB at the given timestamp
        """
        balances = []
        locations = []

        for key, val in data.items():
            if key in ('location', 'net_usd'):
                continue

            assert isinstance(key, Asset), 'at this point the key should only be Asset type'
            balances.append(AssetBalance(
                time=timestamp,
                asset=key,
                amount=str(val['amount']),
                usd_value=str(val['usd_value']),
            ))

        for key2, val2 in data['location'].items():
            # Here we know val2 is just a Dict since the key to data is 'location'
            val2 = cast(Dict, val2)
            location = deserialize_location(key2).serialize_for_db()
            locations.append(LocationData(
                time=timestamp, location=location, usd_value=str(val2['usd_value']),
            ))
        locations.append(LocationData(
            time=timestamp,
            location=Location.TOTAL.serialize_for_db(),
            usd_value=str(data['net_usd']),
        ))

        self.add_multiple_balances(balances)
        self.add_multiple_location_data(locations)

    def add_exchange(
            self,
            name: str,
            api_key: str,
            api_secret: str,
    ) -> None:
        if name not in SUPPORTED_EXCHANGES:
            raise InputError('Unsupported exchange {}'.format(name))

        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO user_credentials (name, api_key, api_secret) VALUES (?, ?, ?)',
            (name, api_key, api_secret),
        )
        self.conn.commit()
        self.update_last_write()

    def remove_exchange(self, name: str) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            'DELETE FROM user_credentials WHERE name =?', (name,),
        )
        self.conn.commit()
        self.update_last_write()

    def get_exchange_credentials(self) -> Dict[str, ApiCredentials]:
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT name, api_key, api_secret FROM user_credentials;',
        )
        result = result.fetchall()
        credentials = {}

        for entry in result:
            if entry[0] == 'rotkehlchen':
                continue
            name = entry[0]
            credentials[name] = ApiCredentials.serialize(
                api_key=str(entry[1]),
                api_secret=str(entry[2]),
            )

        return credentials

    def write_tuples(
            self,
            tuple_type: DBTupleType,
            query: str,
            tuples: List[Tuple[Any, ...]],
            **kwargs,
    ) -> None:
        cursor = self.conn.cursor()
        try:
            cursor.executemany(query, tuples)
        except sqlcipher.IntegrityError:  # pylint: disable=no-member
            # That means that one of the tuples hit a constraint, most probably
            # already existing in the DB, in which case we resort to writting them
            # one by one to only reject the duplicates

            nonces_set: Set[int] = set()
            if tuple_type == 'ethereum_transaction':
                nonces_set = set(range(len([t for t in tuples if t[10] == -1])))

            for entry in tuples:
                try:
                    cursor.execute(query, entry)
                except sqlcipher.IntegrityError:  # pylint: disable=no-member
                    if tuple_type == 'ethereum_transaction':
                        nonce = entry[10]
                        # If it's not an internal transaction with the same hash
                        # ignore it. That is since it's indeed a duplicate because
                        # when we query etherscan we get all transactions where
                        # the given address is either the from or the to.
                        if nonce != -1:
                            continue

                        if 'from_etherscan' in kwargs and kwargs['from_etherscan'] is True:
                            # If it's an internal transaction with the same hash then
                            # still input it as there is no way to distinguish between
                            # multiple etherscan internal transactions with the same
                            # original transaction hash. Here we trust the data source.
                            # To differentiate between them in Rotkehlchen we use a
                            # more negative nonce
                            entry_list = list(entry)
                            # Make sure that the internal etherscan transaction nonce
                            # is increasingly negative (> -1)
                            # If a key error is thrown here due to popping from an empty
                            # set then something is really wrong so not catching it
                            entry_list[10] = -1 - nonces_set.pop() - 1
                            entry = tuple(entry_list)
                            try:
                                cursor.execute(query, entry)
                                # Success so just go to the next entry
                                continue
                            except sqlcipher.IntegrityError:  # pylint: disable=no-member
                                # the error is logged right below
                                pass

                        # if we reach here it means the transaction is already in the DB
                        # But this can't be avoided with the way we query etherscan
                        # right now since we don't query transactions in a specific
                        # time range, so duplicate addition attempts can happen.
                        string_repr = db_tuple_to_str(entry, tuple_type)
                        logger.debug(
                            f'Did not add "{string_repr}" to the DB since'
                            f'it already exists.',
                        )
                        continue

                    string_repr = db_tuple_to_str(entry, tuple_type)
                    self.msg_aggregator.add_error(
                        f'Error adding "{string_repr}" to the DB. It already exists.',
                    )
                except sqlcipher.InterfaceError:  # pylint: disable=no-member
                    log.critical(f'Interface error with tuple: {entry}')

        self.conn.commit()
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
            location: Optional[str] = None,
    ) -> List[MarginPosition]:
        """Returns a list of margin positions optionally filtered by time and location

        The returned list is ordered from oldest to newest
        """
        cursor = self.conn.cursor()
        query = (
            'SELECT id,'
            '  location,'
            '  open_time,'
            '  close_time,'
            '  profit_loss,'
            '  pl_currency,'
            '  fee,'
            '  fee_currency,'
            '  link,'
            '  notes FROM margin_positions '
        )
        if location is not None:
            query += f'WHERE location="{location}" '
        bindings: Union[
            Tuple,
            Tuple[Timestamp],
            Tuple[Timestamp, Timestamp],
        ] = ()
        if from_ts:
            query += 'AND close_time >= ? '
            bindings = (from_ts,)
            if to_ts:
                query += 'AND close_time <= ? '
                bindings = (from_ts, to_ts)
        elif to_ts:
            query += 'AND close_time <= ? '
            bindings = (to_ts,)
        query += 'ORDER BY close_time ASC;'
        results = cursor.execute(query, bindings)

        margin_positions = []
        for result in results:
            try:
                if result[2] == '0':
                    open_time = None
                else:
                    open_time = deserialize_timestamp(result[2])
                margin = MarginPosition(
                    location=deserialize_location_from_db(result[1]),
                    open_time=open_time,
                    close_time=deserialize_timestamp(result[3]),
                    profit_loss=deserialize_asset_amount(result[4]),
                    pl_currency=Asset(result[5]),
                    fee=deserialize_fee(result[6]),
                    fee_currency=Asset(result[7]),
                    link=result[8],
                    notes=result[9],
                )
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
              link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.write_tuples(tuple_type='asset_movement', query=query, tuples=movement_tuples)

    def get_asset_movements(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[str] = None,
    ) -> List[AssetMovement]:
        """Returns a list of asset movements optionally filtered by time and location

        The returned list is ordered from oldest to newest
        """
        cursor = self.conn.cursor()
        query = (
            'SELECT id,'
            '  location,'
            '  category,'
            '  time,'
            '  asset,'
            '  amount,'
            '  fee_asset,'
            '  fee,'
            '  link FROM asset_movements '
        )
        if location is not None:
            query += f'WHERE location="{location}" '
        bindings: Union[
            Tuple,
            Tuple[Timestamp],
            Tuple[Timestamp, Timestamp],
        ] = ()
        if from_ts:
            query += 'AND time >= ? '
            bindings = (from_ts,)
            if to_ts:
                query += 'AND time <= ? '
                bindings = (from_ts, to_ts)
        elif to_ts:
            query += 'AND time <= ? '
            bindings = (to_ts,)
        query += 'ORDER BY time ASC;'
        results = cursor.execute(query, bindings)

        asset_movements = []
        for result in results:
            try:
                movement = AssetMovement(
                    location=deserialize_location_from_db(result[1]),
                    category=deserialize_asset_movement_category_from_db(result[2]),
                    timestamp=result[3],
                    asset=Asset(result[4]),
                    amount=deserialize_asset_amount(result[5]),
                    fee_asset=Asset(result[6]),
                    fee=deserialize_fee(result[7]),
                    link=result[8],
                )
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

    def add_ethereum_transactions(
            self,
            ethereum_transactions: List[EthereumTransaction],
            from_etherscan: bool,
    ) -> None:
        """Adds ethereum transactions to the database

        If from_etherscan is True then this means that the source of the transactions
        is an etherscan query. This is used to determine how we should handle the
        transactions with nonce "-1" as this is how we currently identify internal
        ethereum transactions from etherscan.
        """
        tx_tuples: List[Tuple[Any, ...]] = []
        for tx in ethereum_transactions:
            tx_tuples.append((
                tx.tx_hash,
                tx.timestamp,
                tx.block_number,
                tx.from_address,
                tx.to_address,
                str(tx.value),
                str(tx.gas),
                str(tx.gas_price),
                str(tx.gas_used),
                tx.input_data,
                tx.nonce,
            ))

        query = """
            INSERT INTO ethereum_transactions(
              tx_hash,
              timestamp,
              block_number,
              from_address,
              to_address,
              value,
              gas,
              gas_price,
              gas_used,
              input_data,
              nonce)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.write_tuples(
            tuple_type='ethereum_transaction',
            query=query,
            tuples=tx_tuples,
            from_etherscan=from_etherscan,
        )

    def get_ethereum_transactions(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            address: Optional[ChecksumAddress] = None,
    ) -> List[EthereumTransaction]:
        """Returns a list of ethereum transactions optionally filtered by time and/or from address

        The returned list is ordered from oldest to newest
        """
        cursor = self.conn.cursor()
        query = """
            SELECT tx_hash,
              timestamp,
              block_number,
              from_address,
              to_address,
              value,
              gas,
              gas_price,
              gas_used,
              input_data,
              nonce FROM ethereum_transactions
        """
        bindings: Union[
            Tuple,
            Tuple[Timestamp],
            Tuple[Timestamp, Timestamp],
        ] = ()
        if address is not None:
            query += f'WHERE from_address="{address}" '
        if from_ts:
            query += 'AND timestamp >= ? '
            bindings = (from_ts,)
            if to_ts:
                query += 'AND timestatmp <= ? '
                bindings = (from_ts, to_ts)
        elif to_ts:
            query += 'AND timestamp <= ? '
            bindings = (to_ts,)
        query += 'ORDER BY timestamp ASC;'
        results = cursor.execute(query, bindings)

        ethereum_transactions = []
        for result in results:
            try:
                tx = EthereumTransaction(
                    tx_hash=result[0],
                    timestamp=deserialize_timestamp(result[1]),
                    block_number=result[2],
                    from_address=result[3],
                    to_address=result[4],
                    value=deserialize_fval(result[5]),
                    gas=deserialize_fval(result[6]),
                    gas_price=deserialize_fval(result[7]),
                    gas_used=deserialize_fval(result[8]),
                    input_data=result[9],
                    nonce=result[10],
                )
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing ethereum transaction from the DB. '
                    f'Skipping it. Error was: {str(e)}',
                )
                continue

            ethereum_transactions.append(tx)

        return ethereum_transactions

    def add_trades(self, trades: List[Trade]) -> None:
        trade_tuples: List[Tuple[Any, ...]] = []
        for trade in trades:
            trade_tuples.append((
                trade.identifier,
                trade.timestamp,
                trade.location.serialize_for_db(),
                trade.pair,
                trade.trade_type.serialize_for_db(),
                str(trade.amount),
                str(trade.rate),
                str(trade.fee),
                trade.fee_currency.identifier,
                trade.link,
                trade.notes,
            ))

        query = """
            INSERT INTO trades(
              id,
              time,
              location,
              pair,
              type,
              amount,
              rate,
              fee,
              fee_currency,
              link,
              notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            '  pair=?,'
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
                trade.pair,
                trade.trade_type.serialize_for_db(),
                str(trade.amount),
                str(trade.rate),
                str(trade.fee),
                trade.fee_currency.identifier,
                trade.link,
                trade.notes,
                old_trade_id,
            ),
        )
        if cursor.rowcount == 0:
            return False, 'Tried to edit non existing trade id'

        self.conn.commit()
        return True, ''

    def get_trades(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[Location] = None,
    ) -> List[Trade]:
        """Returns a list of trades optionally filtered by time and location

        The returned list is ordered from oldest to newest
        """
        cursor = self.conn.cursor()
        query = (
            'SELECT id,'
            '  time,'
            '  location,'
            '  pair,'
            '  type,'
            '  amount,'
            '  rate,'
            '  fee,'
            '  fee_currency,'
            '  link,'
            '  notes FROM trades '
        )
        if location is not None:
            query += f'WHERE location="{location.serialize_for_db()}" '
        bindings: Union[
            Tuple,
            Tuple[Timestamp],
            Tuple[Timestamp, Timestamp],
        ] = ()
        if from_ts:
            query += 'AND time >= ? '
            bindings = (from_ts,)
            if to_ts:
                query += 'AND time <= ? '
                bindings = (from_ts, to_ts)
        elif to_ts:
            query += 'AND time <= ? '
            bindings = (to_ts,)
        query += 'ORDER BY time ASC;'
        results = cursor.execute(query, bindings)

        trades = []
        for result in results:
            try:
                trade = Trade(
                    timestamp=deserialize_timestamp(result[1]),
                    location=deserialize_location_from_db(result[2]),
                    pair=result[3],
                    trade_type=deserialize_trade_type_from_db(result[4]),
                    amount=deserialize_asset_amount(result[5]),
                    rate=deserialize_price(result[6]),
                    fee=deserialize_fee(result[7]),
                    fee_currency=Asset(result[8]),
                    link=result[9],
                    notes=result[10],
                )
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

    def delete_external_trade(self, trade_id: str) -> Tuple[bool, str]:
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM trades WHERE id=?', (trade_id,))
        if cursor.rowcount == 0:
            return False, 'Tried to delete non-existing external trade'
        self.conn.commit()
        return True, ''

    def set_rotkehlchen_premium(
            self,
            api_key: ApiKey,
            api_secret: ApiSecret,
    ) -> None:
        cursor = self.conn.cursor()
        # We don't care about previous value so this simple insert or replace should work
        cursor.execute(
            'INSERT OR REPLACE INTO user_credentials(name, api_key, api_secret) VALUES (?, ?, ?)',
            ('rotkehlchen', api_key, api_secret),
        )
        self.conn.commit()
        # Do not update the last write here. If we are starting in a new machine
        # then this write is mandatory and to sync with data from server we need
        # an empty last write ts in that case
        # self.update_last_write()

    def get_rotkehlchen_premium(self) -> Optional[Tuple[str, str]]:
        cursor = self.conn.cursor()
        result = cursor.execute(
            'SELECT api_key, api_secret FROM user_credentials where name="rotkehlchen";',
        )
        result = result.fetchall()
        if len(result) == 1:
            return result[0]
        else:
            return None

    def get_netvalue_data(self) -> Tuple[List[str], List[str]]:
        """Get all entries of net value data from the DB"""
        cursor = self.conn.cursor()
        # Get the total location ("H") entries in ascending time
        query = cursor.execute(
            'SELECT time, usd_value FROM timed_location_data '
            'WHERE location="H" ORDER BY time ASC;',
        )

        data = []
        times_int = []
        for entry in query:
            times_int.append(entry[0])
            data.append(entry[1])

        return times_int, data

    def query_timed_balances(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
            asset: Asset,
    ) -> List[SingleAssetBalance]:
        """Query all balance entries for an asset within a range of timestamps"""
        cursor = self.conn.cursor()
        results = cursor.execute(
            f'SELECT time, amount, usd_value FROM timed_balances '
            f'WHERE time BETWEEN {from_ts} AND {to_ts} AND currency="{asset.identifier}" '
            f'ORDER BY time ASC;',
        )
        results = results.fetchall()
        balances = []
        for result in results:
            balances.append(
                SingleAssetBalance(
                    time=result[0],
                    amount=result[1],
                    usd_value=result[2],
                ),
            )

        return balances

    def query_owned_assets(self) -> List[Asset]:
        """Query the DB for a list of all assets ever owned"""
        cursor = self.conn.cursor()
        query = cursor.execute(
            'SELECT DISTINCT currency FROM timed_balances ORDER BY time ASC;',
        )

        results = []
        for result in query:
            try:
                results.append(Asset(result[0]))
            except UnknownAsset:
                self.msg_aggregator.add_warning(
                    f'Unknown/unsupported asset {result[0]} found in the database. '
                    f'If you believe this should be supported open an issue in github',
                )
                continue
            except DeserializationError:
                self.msg_aggregator.add_error(
                    f'Asset with non-string type {type(result[0])} found in the '
                    f'database. Skipping it.',
                )
                continue

        return results

    def get_latest_location_value_distribution(self) -> List[LocationData]:
        """Gets the latest location data

        Returns a list of `LocationData` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all locations
        """
        cursor = self.conn.cursor()
        results = cursor.execute(
            'SELECT time, location, usd_value FROM timed_location_data WHERE '
            'time=(SELECT MAX(time) FROM timed_location_data);',
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

    def get_latest_asset_value_distribution(self) -> List[AssetBalance]:
        """Gets the latest asset distribution data

        Returns a list of `AssetBalance` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all assets

        The list is sorted by usd value going from higher to lower
        """
        cursor = self.conn.cursor()
        results = cursor.execute(
            'SELECT time, currency, amount, usd_value FROM timed_balances WHERE '
            'time=(SELECT MAX(time) from timed_balances) ORDER BY '
            'CAST(usd_value AS REAL) DESC;',
        )
        results = results.fetchall()
        assets = []
        for result in results:
            assets.append(
                AssetBalance(
                    time=result[0],
                    asset=Asset(result[1]),
                    amount=result[2],
                    usd_value=result[3],
                ),
            )

        return assets
