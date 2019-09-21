import os
import time
from copy import deepcopy
from shutil import copyfile
from unittest.mock import patch

import pytest
from eth_utils.address import to_checksum_address
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants import YEAR_IN_SECONDS
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD, FIAT_CURRENCIES, S_CNY, S_EUR
from rotkehlchen.data_handler import DataHandler, verify_otctrade_data
from rotkehlchen.db.dbhandler import (
    DBINFO_FILENAME,
    DEFAULT_ANONYMIZED_LOGS,
    DEFAULT_BALANCE_SAVE_FREQUENCY,
    DEFAULT_DATE_DISPLAY_FORMAT,
    DEFAULT_INCLUDE_CRYPTO2CRYPTO,
    DEFAULT_INCLUDE_GAS_COSTS,
    DEFAULT_MAIN_CURRENCY,
    DEFAULT_START_DATE,
    DEFAULT_UI_FLOATING_PRECISION,
    DBHandler,
    detect_sqlcipher_version,
)
from rotkehlchen.db.trades import hash_id, hashable_string_for_external_trade
from rotkehlchen.db.utils import (
    ROTKEHLCHEN_DB_VERSION,
    AssetBalance,
    BlockchainAccounts,
    LocationData,
)
from rotkehlchen.errors import AuthenticationError, InputError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_CNY, A_DAO, A_DOGE, A_GNO, A_RDN, A_XMR
from rotkehlchen.tests.utils.rotkehlchen import add_starting_balances
from rotkehlchen.typing import SupportedBlockchain, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps

TABLES_AT_INIT = [
    'timed_balances',
    'timed_location_data',
    'user_credentials',
    'blockchain_accounts',
    'multisettings',
    'current_balances',
    'trades',
    'trade_type',
    'settings',
    'last_timestamps',
    'margin_positions',
    'asset_movements',
]


def test_data_init_and_password(data_dir, username):
    """DB Creation logic and tables at start testing"""
    msg_aggregator = MessagesAggregator()
    # Creating a new data dir should work
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    assert os.path.exists(os.path.join(data_dir, username))

    # Trying to re-create it should throw
    with pytest.raises(AuthenticationError):
        data.unlock(username, '123', create_new=True)

    # Trying to unlock a non-existing user without create_new should throw
    with pytest.raises(AuthenticationError):
        data.unlock('otheruser', '123', create_new=False)

    # now relogin and check all tables are there
    del data
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=False)
    cursor = data.db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    results = cursor.fetchall()
    results = [result[0] for result in results]
    assert set(results) == set(TABLES_AT_INIT)

    # finally logging in with wrong password should also fail
    del data
    data = DataHandler(data_dir, msg_aggregator)
    with pytest.raises(AuthenticationError):
        data.unlock(username, '1234', create_new=False)


def test_export_import_db(data_dir, username):
    """Create a DB, write some data and then after export/import confirm it's there"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    data.set_fiat_balance('EUR', '10')

    encoded_data, _ = data.compress_and_encrypt_db('123')

    # The server would return them decoded
    encoded_data = encoded_data.decode()
    data.decompress_and_decrypt_db('123', encoded_data)
    fiat_balances = data.get_fiat_balances()
    assert len(fiat_balances) == 1
    assert int(fiat_balances[A_EUR]) == 10


def test_writting_fetching_data(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    tokens = [A_GNO, A_RDN]
    data.write_owned_eth_tokens(tokens)
    result = data.db.get_owned_tokens()
    assert set(tokens) == set(result)

    data.add_blockchain_account(SupportedBlockchain.BITCOIN, '1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS')
    data.add_blockchain_account(
        SupportedBlockchain.ETHEREUM,
        '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
    )
    # Add a non checksummed address
    data.add_blockchain_account(
        SupportedBlockchain.ETHEREUM,
        '0x80b369799104a47e98a553f3329812a44a7facdc',
    )
    accounts = data.db.get_blockchain_accounts()
    assert isinstance(accounts, BlockchainAccounts)
    assert accounts.btc == ['1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS']
    # See that after addition the address has been checksummed
    assert set(accounts.eth) == set([
        '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
        to_checksum_address('0x80b369799104a47e98a553f3329812a44a7facdc'),

    ])
    # Add existing account should fail
    with pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member
        data.add_blockchain_account(
            SupportedBlockchain.ETHEREUM,
            '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
        )
    # Remove non-existing account
    with pytest.raises(InputError):
        data.remove_blockchain_account(
            SupportedBlockchain.ETHEREUM,
            '0x136029d76af6fE4A356528e4Dc66B2C18123597D',
        )
    # Remove existing account
    data.remove_blockchain_account(
        SupportedBlockchain.ETHEREUM,
        '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
    )
    accounts = data.db.get_blockchain_accounts()
    assert accounts.eth == [to_checksum_address('0x80b369799104a47e98a553f3329812a44a7facdc')]

    result, _ = data.add_ignored_asset('DAO')
    assert result
    result, _ = data.add_ignored_asset('DOGE')
    assert result
    result, _ = data.add_ignored_asset('DOGE')
    assert not result
    # Test adding non existing asset
    result, msg = data.add_ignored_asset('dsajdhskajdad')
    assert not result
    assert 'for ignoring is not known/supported' in msg

    ignored_assets = data.db.get_ignored_assets()
    assert all([isinstance(asset, Asset) for asset in ignored_assets])
    assert set(ignored_assets) == set([A_DAO, A_DOGE])
    # Test removing asset that is not in the list
    result, msg = data.remove_ignored_asset('RDN')
    assert 'not in ignored assets' in msg
    # Test removing non existing asset
    result, msg = data.remove_ignored_asset('dshajdhsjkahdjssad')
    assert 'is not known/supported' in msg
    assert not result
    result, _ = data.remove_ignored_asset('DOGE')
    assert result
    assert data.db.get_ignored_assets() == ['DAO']

    # With nothing inserted in settings make sure default values are returned
    result = data.db.get_settings()
    last_write_diff = ts_now() - result['last_write_ts']
    # make sure last_write was within 3 secs
    assert last_write_diff >= 0 and last_write_diff < 3
    del result['last_write_ts']
    assert result == {
        'historical_data_start': DEFAULT_START_DATE,
        'eth_rpc_endpoint': 'http://localhost:8545',
        'ui_floating_precision': DEFAULT_UI_FLOATING_PRECISION,
        'db_version': ROTKEHLCHEN_DB_VERSION,
        'include_crypto2crypto': DEFAULT_INCLUDE_CRYPTO2CRYPTO,
        'include_gas_costs': DEFAULT_INCLUDE_GAS_COSTS,
        'taxfree_after_period': YEAR_IN_SECONDS,
        'balance_save_frequency': DEFAULT_BALANCE_SAVE_FREQUENCY,
        'last_balance_save': 0,
        'main_currency': DEFAULT_MAIN_CURRENCY,
        'anonymized_logs': DEFAULT_ANONYMIZED_LOGS,
        'date_display_format': DEFAULT_DATE_DISPLAY_FORMAT,
        'last_data_upload_ts': 0,
        'premium_should_sync': False,
    }

    # Check setting non-existing settings. Should be ignored
    success, msg = data.set_settings({'nonexisting_setting': 1}, accountant=None)
    assert success
    assert msg != '' and 'nonexisting_setting' in msg
    _, msg = data.set_settings({
        'nonexisting_setting': 1,
        'eth_rpc_endpoint': 'http://localhost:8555',
        'ui_floating_precision': 3,
    }, accountant=None)
    assert msg != '' and 'nonexisting_setting' in msg

    # Now check nothing funny made it in the db
    result = data.db.get_settings()
    assert result['eth_rpc_endpoint'] == 'http://localhost:8555'
    assert result['ui_floating_precision'] == 3
    assert 'nonexisting_setting' not in result


def test_writting_fetching_external_trades(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    # add 2 trades and check they are in the DB
    otc_trade1 = {
        'otc_timestamp': '10/03/2018 23:30',
        'otc_pair': 'ETH_EUR',
        'otc_type': 'buy',
        'otc_amount': '10',
        'otc_rate': '100',
        'otc_fee': '0.001',
        'otc_fee_currency': 'ETH',
        'otc_link': 'a link',
        'otc_notes': 'a note',
    }
    otc_trade2 = {
        'otc_timestamp': '15/03/2018 23:35',
        'otc_pair': 'ETH_EUR',
        'otc_type': 'buy',
        'otc_amount': '5',
        'otc_rate': '100',
        'otc_fee': '0.001',
        'otc_fee_currency': 'ETH',
        'otc_link': 'a link 2',
        'otc_notes': 'a note 2',
    }
    trade1, _ = verify_otctrade_data(otc_trade1)
    trade2, _ = verify_otctrade_data(otc_trade2)

    result, _, = data.add_external_trade(otc_trade1)
    assert result
    result, _ = data.add_external_trade(otc_trade2)
    assert result
    result = data.get_external_trades()
    assert result[0] == trade1
    assert result[1] == trade2

    # query trades in period
    result = data.get_external_trades(
        from_ts=1520553600,  # 09/03/2018
        to_ts=1520726400,  # 11/03/2018
    )
    assert len(result) == 1
    # make sure id is there but do not compare it
    assert result[0] == trade1

    # query trades only with to_ts
    result = data.get_external_trades(
        to_ts=1520726400,  # 11/03/2018
    )
    assert len(result) == 1
    # make sure id is there but do not compare it
    assert result[0] == trade1

    # edit a trade and check the edit made it in the DB
    otc_trade1['otc_rate'] = '120'
    hashable_string = hashable_string_for_external_trade(
        timestamp=trade1.timestamp,
        trade_type=otc_trade1['otc_type'],
        pair=otc_trade1['otc_pair'],
    )
    trade1_id = hash_id(hashable_string)
    otc_trade1['otc_id'] = trade1_id
    result, _ = data.edit_external_trade(otc_trade1)
    assert result
    result = data.get_external_trades()
    edited_trade1 = trade1._replace(rate=FVal(120))
    assert result[0] == edited_trade1
    assert result[1] == trade2

    # try to edit a non-existing trade
    otc_trade1['otc_rate'] = '160'
    otc_trade1['otc_id'] = '5'
    result, _ = data.edit_external_trade(otc_trade1)
    assert not result
    otc_trade1['otc_rate'] = '120'
    otc_trade1['otc_id'] = trade1_id
    result = data.get_external_trades()
    assert result[0] == edited_trade1
    assert result[1] == trade2

    # # try to delete non-existing trade
    result, _ = data.delete_external_trade('dasdasd')
    assert not result

    # # delete an external trade
    result, _ = data.delete_external_trade(trade1_id)
    result = data.get_external_trades()
    assert result[0] == trade2


def test_settings_entry_types(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    success, msg = data.set_settings({
        'last_write_ts': 1,
        'premium_should_sync': True,
        'include_crypto2crypto': True,
        'last_data_upload_ts': 1,
        'ui_floating_precision': 1,
        'taxfree_after_period': 1,
        'historical_data_start': '01/08/2015',
        'eth_rpc_endpoint': 'http://localhost:8545',
        'balance_save_frequency': 24,
        'anonymized_logs': True,
        'date_display_format': '%d/%m/%Y %H:%M:%S %z',
    })
    assert success
    assert msg == '', f'set settings returned error: "{msg}"'

    res = data.db.get_settings()
    assert isinstance(res['db_version'], int)
    assert res['db_version'] == ROTKEHLCHEN_DB_VERSION
    assert isinstance(res['last_write_ts'], int)
    assert isinstance(res['premium_should_sync'], bool)
    assert res['premium_should_sync'] is True
    assert isinstance(res['include_crypto2crypto'], bool)
    assert res['include_crypto2crypto'] is True
    assert isinstance(res['ui_floating_precision'], int)
    assert res['ui_floating_precision'] == 1
    assert isinstance(res['taxfree_after_period'], int)
    assert res['taxfree_after_period'] == 1
    assert isinstance(res['historical_data_start'], str)
    assert res['historical_data_start'] == '01/08/2015'
    assert isinstance(res['eth_rpc_endpoint'], str)
    assert res['eth_rpc_endpoint'] == 'http://localhost:8545'
    assert isinstance(res['balance_save_frequency'], int)
    assert res['balance_save_frequency'] == 24
    assert isinstance(res['last_balance_save'], int)
    assert res['last_balance_save'] == 0
    assert isinstance(res['main_currency'], str)
    assert res['main_currency'] == 'USD'
    assert isinstance(res['anonymized_logs'], bool)
    assert res['anonymized_logs'] is True
    assert isinstance(res['date_display_format'], str)
    assert res['date_display_format'] == '%d/%m/%Y %H:%M:%S %z'


def test_balance_save_frequency_check(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    now = int(time.time())
    data_save_ts = now - 24 * 60 * 60 + 20
    data.db.add_multiple_location_data([LocationData(
        time=data_save_ts, location='kraken', usd_value='1500',
    )])

    assert not data.should_save_balances()
    success, msg = data.set_settings({'balance_save_frequency': 5})
    assert success
    assert msg == '', f'set settings returned error: "{msg}"'
    assert data.should_save_balances()

    last_save_ts = data.db.get_last_balance_save_time()
    assert last_save_ts == data_save_ts


def test_upgrade_sqlcipher_v3_to_v4_without_dbinfo(data_dir):
    """Test that we can upgrade from an sqlcipher v3 to v4 rotkehlchen database
    Issue: https://github.com/rotkehlchenio/rotkehlchen/issues/229
    """
    sqlcipher_version = detect_sqlcipher_version()
    if sqlcipher_version != 4:
        # nothing to test
        return

    username = 'foo'
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    # get the v3 database file and copy it into the user's data directory
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'sqlcipher_v3_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )

    # the constructor should migrate it in-place and we should have a working DB
    msg_aggregator = MessagesAggregator()
    db = DBHandler(userdata_dir, '123', msg_aggregator)
    assert db.get_version() == ROTKEHLCHEN_DB_VERSION


def test_upgrade_sqlcipher_v3_to_v4_with_dbinfo(data_dir):
    sqlcipher_version = detect_sqlcipher_version()
    if sqlcipher_version != 4:
        # nothing to test
        return

    username = 'foo'
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    # get the v3 database file and copy it into the user's data directory
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'sqlcipher_v3_rotkehlchen.db'),
        os.path.join(userdata_dir, 'rotkehlchen.db'),
    )
    dbinfo = {'sqlcipher_version': 3, 'md5_hash': '20c910c28ca42370e4a5f24d6d4a73d2'}
    with open(os.path.join(userdata_dir, DBINFO_FILENAME), 'w') as f:
        f.write(rlk_jsondumps(dbinfo))

    # the constructor should migrate it in-place and we should have a working DB
    msg_aggregator = MessagesAggregator()
    db = DBHandler(userdata_dir, '123', msg_aggregator)
    assert db.get_version() == ROTKEHLCHEN_DB_VERSION


def test_sqlcipher_detect_version():
    class QueryMock():
        def __init__(self, version):
            self.version = version

        def fetchall(self):
            return [[self.version]]

    class ConnectionMock():
        def __init__(self, version):
            self.version = version

        def execute(self, command):  # pylint: disable=unused-argument
            return QueryMock(self.version)

        def close(self):
            pass

    with patch('pysqlcipher3.dbapi2.connect') as sql_mock:
        sql_mock.return_value = ConnectionMock('4.0.0 community')
        assert detect_sqlcipher_version() == 4
        sql_mock.return_value = ConnectionMock('4.0.1 something')
        assert detect_sqlcipher_version() == 4
        sql_mock.return_value = ConnectionMock('4.9.12 somethingelse')
        assert detect_sqlcipher_version() == 4

        sql_mock.return_value = ConnectionMock('5.10.13 somethingelse')
        assert detect_sqlcipher_version() == 5

        sql_mock.return_value = ConnectionMock('3.1.15 somethingelse')
        assert detect_sqlcipher_version() == 3

        with pytest.raises(ValueError):
            sql_mock.return_value = ConnectionMock('no version')
            detect_sqlcipher_version()


def test_data_set_fiat_balance(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    amount_eur = '100'
    amount_cny = '500'

    success, _ = data.set_fiat_balance(S_EUR, amount_eur)
    assert success
    success, _ = data.set_fiat_balance(S_CNY, amount_cny)
    assert success
    balances = data.get_fiat_balances()
    assert len(balances) == 2
    assert balances[A_EUR] == amount_eur
    assert balances[A_CNY] == amount_cny

    success, _ = data.set_fiat_balance(S_EUR, '')
    balances = data.get_fiat_balances()
    assert len(balances) == 1
    assert balances[A_CNY] == amount_cny

    # also check that all the fiat assets in the fiat table are in
    # all_assets.json
    for fiat in FIAT_CURRENCIES:
        success, _ = data.set_fiat_balance(fiat, '1')
        assert success


asset_balances = [
    AssetBalance(
        time=Timestamp(1451606400),
        asset=A_USD,
        amount='10',
        usd_value='10',
    ), AssetBalance(
        time=Timestamp(1451606401),
        asset=A_ETH,
        amount='2',
        usd_value='1.7068',
    ), AssetBalance(
        time=Timestamp(1465171200),
        asset=A_USD,
        amount='500',
        usd_value='500',
    ), AssetBalance(
        time=Timestamp(1465171201),
        asset=A_ETH,
        amount='10',
        usd_value='123',
    ), AssetBalance(
        time=Timestamp(1485907200),
        asset=A_USD,
        amount='350',
        usd_value='350',
    ), AssetBalance(
        time=Timestamp(1485907201),
        asset=A_ETH,
        amount='25',
        usd_value='249.5',
    ),
]


def test_get_fiat_balances_unhappy_path(data_dir, username):
    """Test that if somehow unsupported assets end up in the DB we don't crash"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT INTO current_balances(asset, amount) '
        ' VALUES(?, ?)',
        ('DSADASDSAD', '10.1'),
    )
    data.db.conn.commit()

    balances = data.get_fiat_balances()
    warnings = msg_aggregator.consume_warnings()
    errors = msg_aggregator.consume_errors()
    assert len(balances) == 0
    assert len(warnings) == 0
    assert len(errors) == 1
    assert 'Unknown FIAT asset' in errors[0]


def test_query_timed_balances(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    data.db.add_multiple_balances(asset_balances)

    result = data.db.query_timed_balances(
        from_ts=1451606401,
        to_ts=1485907100,
        asset=A_USD,
    )
    assert len(result) == 1
    assert result[0].time == 1465171200
    assert result[0].amount == '500'
    assert result[0].usd_value == '500'

    result = data.db.query_timed_balances(
        from_ts=1451606300,
        to_ts=1485907000,
        asset=A_ETH,
    )
    assert len(result) == 2
    assert result[0].time == 1451606401
    assert result[0].amount == '2'
    assert result[0].usd_value == '1.7068'
    assert result[1].time == 1465171201
    assert result[1].amount == '10'
    assert result[1].usd_value == '123'


def test_query_owned_assets(data_dir, username):
    """Test the get_owned_assets with also an unknown asset in the DB"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    balances = deepcopy(asset_balances)
    balances.extend([
        AssetBalance(
            time=Timestamp(1488326400),
            asset=A_BTC,
            amount='1',
            usd_value='1222.66',
        ),
        AssetBalance(
            time=Timestamp(1489326500),
            asset=A_XMR,
            amount='2',
            usd_value='33.8',
        ),
    ])
    data.db.add_multiple_balances(balances)
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT INTO timed_balances('
        '    time, currency, amount, usd_value) '
        ' VALUES(?, ?, ?, ?)',
        (1469326500, 'ADSADX', '10.1', '100.5'),
    )
    data.db.conn.commit()

    assets_list = data.db.query_owned_assets()
    assert assets_list == [A_USD, A_ETH, A_BTC, A_XMR]
    assert all([isinstance(x, Asset) for x in assets_list])
    warnings = data.db.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'Unknown/unsupported asset ADSADX' in warnings[0]


def test_get_latest_location_value_distribution(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    add_starting_balances(data)
    distribution = data.db.get_latest_location_value_distribution()
    assert len(distribution) == 5
    assert all(entry.time == Timestamp(1491607800) for entry in distribution)
    assert distribution[0].location == 'banks'
    assert distribution[0].usd_value == '10000'
    assert distribution[1].location == 'blockchain'
    assert distribution[1].usd_value == '200000'
    assert distribution[2].location == 'kraken'
    assert distribution[2].usd_value == '2000'
    assert distribution[3].location == 'poloniex'
    assert distribution[3].usd_value == '100'
    assert distribution[4].location == 'total'
    assert distribution[4].usd_value == '10700.5'


def test_get_latest_asset_value_distribution(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    balances = add_starting_balances(data)

    assets = data.db.get_latest_asset_value_distribution()
    assert len(assets) == 4
    # Make sure they are sorted by usd value
    assert assets[0] == balances[1]
    assert assets[1] == balances[0]
    assert FVal(assets[0].usd_value) > FVal(assets[1].usd_value)
    assert assets[2] == balances[3]
    assert FVal(assets[1].usd_value) > FVal(assets[2].usd_value)
    assert assets[3] == balances[2]
    assert FVal(assets[2].usd_value) > FVal(assets[3].usd_value)


def test_get_owned_tokens(data_dir, username):
    """Test the get_owned_tokens with also an unknown token in the DB"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    cursor = data.db.conn.cursor()
    tokens = ['RDN', 'GNO', 'DASDSADSAD']
    cursor.executemany(
        'INSERT INTO multisettings(name, value) VALUES(?, ?)',
        [('eth_token', t) for t in tokens],
    )
    data.db.conn.commit()

    tokens = data.db.get_owned_tokens()
    assert tokens == [EthereumToken('GNO'), EthereumToken('RDN')]
    warnings = data.db.msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'Unknown/unsupported asset DASDSADSAD' in warnings[0]


def test_get_netvalue_data(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    add_starting_balances(data)

    times, values = data.db.get_netvalue_data()
    assert len(times) == 3
    assert times[0] == 1451606400
    assert times[1] == 1461606500
    assert times[2] == 1491607800
    assert len(values) == 3
    assert values[0] == '1500'
    assert values[1] == '4500'
    assert values[2] == '10700.5'
