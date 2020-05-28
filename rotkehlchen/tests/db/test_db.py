import os
import time
from copy import deepcopy
from shutil import copyfile
from unittest.mock import patch

import pytest
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.constants import YEAR_IN_SECONDS
from rotkehlchen.constants.assets import A_BTC, A_CNY, A_ETH, A_EUR, A_USD, FIAT_CURRENCIES
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.dbhandler import DBINFO_FILENAME, DBHandler, detect_sqlcipher_version
from rotkehlchen.db.settings import (
    DEFAULT_ANONYMIZED_LOGS,
    DEFAULT_BALANCE_SAVE_FREQUENCY,
    DEFAULT_DATE_DISPLAY_FORMAT,
    DEFAULT_INCLUDE_CRYPTO2CRYPTO,
    DEFAULT_INCLUDE_GAS_COSTS,
    DEFAULT_KRAKEN_ACCOUNT_TYPE,
    DEFAULT_MAIN_CURRENCY,
    DEFAULT_START_DATE,
    DEFAULT_UI_FLOATING_PRECISION,
    ROTKEHLCHEN_DB_VERSION,
    DBSettings,
    ModifiableDBSettings,
)
from rotkehlchen.db.utils import AssetBalance, BlockchainAccounts, LocationData
from rotkehlchen.errors import AuthenticationError, InputError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.tests.utils.constants import (
    A_DAO,
    A_DOGE,
    A_GNO,
    A_RDN,
    A_XMR,
    DEFAULT_TESTS_MAIN_CURRENCY,
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA,
)
from rotkehlchen.tests.utils.rotkehlchen import add_starting_balances
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    BlockchainAccountData,
    EthereumTransaction,
    ExternalService,
    ExternalServiceApiCredentials,
    Fee,
    Location,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps

TABLES_AT_INIT = [
    'timed_balances',
    'timed_location_data',
    'asset_movement_category',
    'external_service_credentials',
    'user_credentials',
    'blockchain_accounts',
    'multisettings',
    'current_balances',
    'trades',
    'ethereum_transactions',
    'manually_tracked_balances',
    'trade_type',
    'location',
    'settings',
    'used_query_ranges',
    'margin_positions',
    'asset_movements',
    'tag_mappings',
    'tags',
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


def test_add_remove_exchange(data_dir, username):
    """Tests that adding and removing an exchange in the DB works.

    Also unknown exchanges should fail
    """
    msg_aggregator = MessagesAggregator()
    username = 'foo'
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    db = DBHandler(userdata_dir, '123', msg_aggregator)

    # Test that an unknown exchange fails
    with pytest.raises(InputError):
        db.add_exchange('non_existing_exchange', 'api_key', 'api_secret')
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 0

    kraken_api_key = ApiKey('kraken_api_key')
    kraken_api_secret = ApiSecret(b'kraken_api_secret')
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')

    # add mock kraken and binance
    db.add_exchange('kraken', kraken_api_key, kraken_api_secret)
    db.add_exchange('binance', binance_api_key, binance_api_secret)
    # and check the credentials can be retrieved
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 2
    assert credentials['kraken'].api_key == kraken_api_key
    assert credentials['kraken'].api_secret == kraken_api_secret
    assert credentials['binance'].api_key == binance_api_key
    assert credentials['binance'].api_secret == binance_api_secret

    # remove an exchange and see it works
    db.remove_exchange('kraken')
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 1


def test_export_import_db(data_dir, username):
    """Create a DB, write some data and then after export/import confirm it's there"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    data.set_fiat_balances({A_EUR: AssetAmount(FVal('10'))})

    encoded_data, _ = data.compress_and_encrypt_db('123')

    # The server would return them decoded
    encoded_data = encoded_data.decode()  # pylint: disable=no-member
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

    data.db.add_blockchain_accounts(
        SupportedBlockchain.BITCOIN,
        [BlockchainAccountData(address='1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS')],
    )
    data.db.add_blockchain_accounts(
        SupportedBlockchain.ETHEREUM,
        [
            BlockchainAccountData(address='0xd36029d76af6fE4A356528e4Dc66B2C18123597D'),
            BlockchainAccountData(address='0x80B369799104a47e98A553f3329812a44A7FaCDc'),
        ],
    )
    accounts = data.db.get_blockchain_accounts()
    assert isinstance(accounts, BlockchainAccounts)
    assert accounts.btc == ['1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS']
    # See that after addition the address has been checksummed
    assert set(accounts.eth) == {
        '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
        '0x80B369799104a47e98A553f3329812a44A7FaCDc',
    }
    # Add existing account should fail
    with pytest.raises(sqlcipher.IntegrityError):  # pylint: disable=no-member
        data.db.add_blockchain_accounts(
            SupportedBlockchain.ETHEREUM,
            [BlockchainAccountData(address='0xd36029d76af6fE4A356528e4Dc66B2C18123597D')],
        )
    # Remove non-existing account
    with pytest.raises(InputError):
        data.db.remove_blockchain_accounts(
            SupportedBlockchain.ETHEREUM,
            ['0x136029d76af6fE4A356528e4Dc66B2C18123597D'],
        )
    # Remove existing account
    data.db.remove_blockchain_accounts(
        SupportedBlockchain.ETHEREUM,
        ['0xd36029d76af6fE4A356528e4Dc66B2C18123597D'],
    )
    accounts = data.db.get_blockchain_accounts()
    assert accounts.eth == ['0x80B369799104a47e98A553f3329812a44A7FaCDc']

    result, _ = data.add_ignored_assets([A_DAO])
    assert result
    result, _ = data.add_ignored_assets([A_DOGE])
    assert result
    result, _ = data.add_ignored_assets([A_DOGE])
    assert not result

    ignored_assets = data.db.get_ignored_assets()
    assert all(isinstance(asset, Asset) for asset in ignored_assets)
    assert set(ignored_assets) == {A_DAO, A_DOGE}
    # Test removing asset that is not in the list
    result, msg = data.remove_ignored_assets([A_RDN])
    assert 'not in ignored assets' in msg
    assert not result
    result, _ = data.remove_ignored_assets([A_DOGE])
    assert result
    assert data.db.get_ignored_assets() == [A_DAO]

    # With nothing inserted in settings make sure default values are returned
    result = data.db.get_settings()
    last_write_diff = ts_now() - result.last_write_ts
    # make sure last_write was within 3 secs
    assert last_write_diff >= 0 and last_write_diff < 3
    expected_dict = {
        'have_premium': False,
        'historical_data_start': DEFAULT_START_DATE,
        'eth_rpc_endpoint': 'http://localhost:8545',
        'ui_floating_precision': DEFAULT_UI_FLOATING_PRECISION,
        'version': ROTKEHLCHEN_DB_VERSION,
        'include_crypto2crypto': DEFAULT_INCLUDE_CRYPTO2CRYPTO,
        'include_gas_costs': DEFAULT_INCLUDE_GAS_COSTS,
        'taxfree_after_period': YEAR_IN_SECONDS,
        'balance_save_frequency': DEFAULT_BALANCE_SAVE_FREQUENCY,
        'last_balance_save': 0,
        'main_currency': DEFAULT_MAIN_CURRENCY.identifier,
        'anonymized_logs': DEFAULT_ANONYMIZED_LOGS,
        'date_display_format': DEFAULT_DATE_DISPLAY_FORMAT,
        'last_data_upload_ts': 0,
        'premium_should_sync': False,
        'submit_usage_analytics': True,
        'last_write_ts': 0,
        'kraken_account_type': DEFAULT_KRAKEN_ACCOUNT_TYPE,
    }
    assert len(expected_dict) == len(DBSettings()), 'One or more settings are missing'

    # Make sure that results are the same. Comparing like this since we ignore last
    # write ts check
    result_dict = result._asdict()
    for key, value in expected_dict.items():
        assert key in result_dict
        if key != 'last_write_ts':
            assert value == result_dict[key]


def test_settings_entry_types(database):
    database.set_settings(ModifiableDBSettings(
        premium_should_sync=True,
        include_crypto2crypto=True,
        anonymized_logs=True,
        ui_floating_precision=1,
        taxfree_after_period=1,
        include_gas_costs=True,
        historical_data_start='01/08/2015',
        eth_rpc_endpoint='http://localhost:8545',
        balance_save_frequency=24,
        date_display_format='%d/%m/%Y %H:%M:%S %z',
        submit_usage_analytics=False,
    ))

    res = database.get_settings()
    assert isinstance(res.version, int)
    assert res.version == ROTKEHLCHEN_DB_VERSION
    assert isinstance(res.last_write_ts, int)
    assert isinstance(res.premium_should_sync, bool)
    # assert res.premium_should_sync is DEFAULT_PREMIUM_SHOULD_SYNC
    assert res.premium_should_sync is True
    assert isinstance(res.include_crypto2crypto, bool)
    assert res.include_crypto2crypto is True
    assert isinstance(res.ui_floating_precision, int)
    assert res.ui_floating_precision == 1
    assert isinstance(res.taxfree_after_period, int)
    assert res.taxfree_after_period == 1
    assert isinstance(res.historical_data_start, str)
    assert res.historical_data_start == '01/08/2015'
    assert isinstance(res.eth_rpc_endpoint, str)
    assert res.eth_rpc_endpoint == 'http://localhost:8545'
    assert isinstance(res.balance_save_frequency, int)
    assert res.balance_save_frequency == 24
    assert isinstance(res.last_balance_save, int)
    assert res.last_balance_save == 0
    assert isinstance(res.main_currency, Asset)
    assert res.main_currency == DEFAULT_TESTS_MAIN_CURRENCY
    assert isinstance(res.anonymized_logs, bool)
    assert res.anonymized_logs is True
    assert isinstance(res.date_display_format, str)
    assert res.date_display_format == '%d/%m/%Y %H:%M:%S %z'
    assert isinstance(res.submit_usage_analytics, bool)
    assert res.submit_usage_analytics is False


def test_balance_save_frequency_check(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    now = int(time.time())
    data_save_ts = now - 24 * 60 * 60 + 20
    data.db.add_multiple_location_data([LocationData(
        time=data_save_ts, location=Location.KRAKEN.serialize_for_db(), usd_value='1500',
    )])

    assert not data.should_save_balances()
    data.db.set_settings(ModifiableDBSettings(balance_save_frequency=5))
    assert data.should_save_balances()

    last_save_ts = data.db.get_last_balance_save_time()
    assert last_save_ts == data_save_ts


def test_upgrade_sqlcipher_v3_to_v4_without_dbinfo(data_dir):
    """Test that we can upgrade from an sqlcipher v3 to v4 rotkehlchen database
    Issue: https://github.com/rotki/rotki/issues/229
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


def test_data_set_fiat_balances(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    amount_eur = AssetAmount(FVal('100'))
    amount_cny = AssetAmount(FVal('500'))

    data.set_fiat_balances({A_EUR: amount_eur})
    data.set_fiat_balances({A_CNY: amount_cny})
    balances = data.get_fiat_balances()
    assert len(balances) == 2
    assert FVal(balances[A_EUR]) == amount_eur
    assert FVal(balances[A_CNY]) == amount_cny

    data.set_fiat_balances({A_EUR: ZERO})
    balances = data.get_fiat_balances()
    assert len(balances) == 1
    assert FVal(balances[A_CNY]) == amount_cny

    # also check that all the fiat assets in the fiat table are in
    # all_assets.json
    for fiat_asset in FIAT_CURRENCIES:
        assert fiat_asset.is_fiat()


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
    assert all(isinstance(x, Asset) for x in assets_list)
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
    assert distribution[0].location == 'B'  # kraken location serialized for DB enum
    assert distribution[0].usd_value == '2000'
    assert distribution[1].location == 'C'  # poloniex location serialized for DB enum
    assert distribution[1].usd_value == '100'
    assert distribution[2].location == 'H'  # total location serialized for DB enum
    assert distribution[2].usd_value == '10700.5'
    assert distribution[3].location == 'I'  # banks location serialized for DB enum
    assert distribution[3].usd_value == '10000'
    assert distribution[4].location == 'J'  # blockchain location serialized for DB enum
    assert distribution[4].usd_value == '200000'


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


def test_add_trades(data_dir, username):
    """Test that adding and retrieving trades from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    trade1 = Trade(
        timestamp=1451606400,
        location=Location.KRAKEN,
        pair='ETH_EUR',
        trade_type=TradeType.BUY,
        amount=FVal('1.1'),
        rate=FVal('10'),
        fee=Fee(FVal('0.01')),
        fee_currency=A_EUR,
        link='',
        notes='',
    )
    trade2 = Trade(
        timestamp=1451607500,
        location=Location.BINANCE,
        pair='BTC_ETH',
        trade_type=TradeType.BUY,
        amount=FVal('0.00120'),
        rate=FVal('10'),
        fee=Fee(FVal('0.001')),
        fee_currency=A_ETH,
        link='',
        notes='',
    )
    trade3 = Trade(
        timestamp=1451608600,
        location=Location.COINBASE,
        pair='BTC_ETH',
        trade_type=TradeType.SELL,
        amount=FVal('0.00120'),
        rate=FVal('1'),
        fee=Fee(FVal('0.001')),
        fee_currency=A_ETH,
        link='',
        notes='',
    )

    # Add and retrieve the first 2 trades. All should be fine.
    data.db.add_trades([trade1, trade2])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    returned_trades = data.db.get_trades()
    assert returned_trades == [trade1, trade2]

    # Add the last 2 trades. Since trade2 already exists in the DB it should be
    # ignored and a warning should be shown
    data.db.add_trades([trade2, trade3])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 1
    returned_trades = data.db.get_trades()
    assert returned_trades == [trade1, trade2, trade3]


def test_add_margin_positions(data_dir, username):
    """Test that adding and retrieving margin positions from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    margin1 = MarginPosition(
        location=Location.BITMEX,
        open_time=1451606400,
        close_time=1451616500,
        profit_loss=FVal('1.0'),
        pl_currency=A_BTC,
        fee=Fee(FVal('0.01')),
        fee_currency=A_EUR,
        link='',
        notes='',
    )
    margin2 = MarginPosition(
        location=Location.BITMEX,
        open_time=1451626500,
        close_time=1451636500,
        profit_loss=FVal('0.5'),
        pl_currency=A_BTC,
        fee=Fee(FVal('0.01')),
        fee_currency=A_EUR,
        link='',
        notes='',
    )
    margin3 = MarginPosition(
        location=Location.POLONIEX,
        open_time=1452636501,
        close_time=1459836501,
        profit_loss=FVal('2.5'),
        pl_currency=A_BTC,
        fee=Fee(FVal('0.01')),
        fee_currency=A_EUR,
        link='',
        notes='',
    )

    # Add and retrieve the first 2 margins. All should be fine.
    data.db.add_margin_positions([margin1, margin2])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    returned_margins = data.db.get_margin_positions()
    assert returned_margins == [margin1, margin2]

    # Add the last 2 margins. Since margin2 already exists in the DB it should be
    # ignored and a warning should be shown
    data.db.add_margin_positions([margin2, margin3])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 1
    returned_margins = data.db.get_margin_positions()
    assert returned_margins == [margin1, margin2, margin3]


def test_add_asset_movements(data_dir, username):
    """Test that adding and retrieving asset movements from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    movement1 = AssetMovement(
        location=Location.BITMEX,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=1451606400,
        asset=A_BTC,
        amount=FVal('1.0'),
        fee_asset=A_EUR,
        fee=Fee(FVal('0')),
        link='',
    )
    movement2 = AssetMovement(
        location=Location.POLONIEX,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=1451608501,
        asset=A_ETH,
        amount=FVal('1.0'),
        fee_asset=A_EUR,
        fee=Fee(FVal('0.01')),
        link='',
    )
    movement3 = AssetMovement(
        location=Location.BITTREX,
        category=AssetMovementCategory.WITHDRAWAL,
        timestamp=1461708501,
        asset=A_ETH,
        amount=FVal('1.0'),
        fee_asset=A_EUR,
        fee=Fee(FVal('0.01')),
        link='',
    )

    # Add and retrieve the first 2 margins. All should be fine.
    data.db.add_asset_movements([movement1, movement2])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    returned_movements = data.db.get_asset_movements()
    assert returned_movements == [movement1, movement2]

    # Add the last 2 movements. Since movement2 already exists in the DB it should be
    # ignored and a warning should be shown
    data.db.add_asset_movements([movement2, movement3])
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 1
    returned_movements = data.db.get_asset_movements()
    assert returned_movements == [movement1, movement2, movement3]


def test_add_ethereum_transactions(data_dir, username):
    """Test that adding and retrieving ethereum transactions from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    tx1 = EthereumTransaction(
        tx_hash=b'1',
        timestamp=Timestamp(1451606400),
        block_number=1,
        from_address=ETH_ADDRESS1,
        to_address=ETH_ADDRESS3,
        value=FVal('2000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )
    tx2 = EthereumTransaction(
        tx_hash=b'2',
        timestamp=Timestamp(1451706400),
        block_number=3,
        from_address=ETH_ADDRESS2,
        to_address=ETH_ADDRESS3,
        value=FVal('4000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=1,
    )
    tx3 = EthereumTransaction(
        tx_hash=b'3',
        timestamp=Timestamp(1452806400),
        block_number=5,
        from_address=ETH_ADDRESS3,
        to_address=ETH_ADDRESS1,
        value=FVal('1000000'),
        gas=FVal('5000000'),
        gas_price=FVal('2000000000'),
        gas_used=FVal('25000000'),
        input_data=MOCK_INPUT_DATA,
        nonce=3,
    )

    # Add and retrieve the first 2 margins. All should be fine.
    data.db.add_ethereum_transactions([tx1, tx2], from_etherscan=True)
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    returned_transactions = data.db.get_ethereum_transactions()
    assert returned_transactions == [tx1, tx2]

    # Add the last 2 transactions. Since tx2 already exists in the DB it should be
    # ignored (no errors shown for attempting to add already existing transaction)
    data.db.add_ethereum_transactions([tx2, tx3], from_etherscan=True)
    errors = msg_aggregator.consume_errors()
    warnings = msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0
    returned_transactions = data.db.get_ethereum_transactions()
    assert returned_transactions == [tx1, tx2, tx3]


@pytest.mark.parametrize('ethereum_accounts', [[]])
def test_non_checksummed_eth_account_in_db(database):
    """
    Regression test for  https://github.com/rotki/rotki/issues/519

    This is a test for an occasion that should not happen in a normal run.
    Only if the user manually edits the DB and modifies a blockchain account
    to be non-checksummed then this scenario will happen.

    This test verifies that the user is warned and the address is skipped.
    """
    # Manually enter three blockchain ETH accounts one of which is only valid
    cursor = database.conn.cursor()
    valid_address = '0x9531C059098e3d194fF87FebB587aB07B30B1306'
    non_checksummed_address = '0xe7302e6d805656cf37bd6839a977fe070184bf45'
    invalid_address = 'dsads'
    cursor.executemany(
        'INSERT INTO blockchain_accounts(blockchain, account) VALUES (?, ?)',
        (
            ('ETH', non_checksummed_address),
            ('ETH', valid_address),
            ('ETH', invalid_address)),
    )
    database.conn.commit()

    blockchain_accounts = database.get_blockchain_accounts()
    eth_accounts = blockchain_accounts.eth
    assert len(eth_accounts) == 1
    assert eth_accounts[0] == valid_address
    errors = database.msg_aggregator.consume_errors()
    warnings = database.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 2
    assert f'Non-checksummed eth address {non_checksummed_address}' in warnings[0]
    assert f'Non-checksummed eth address {invalid_address}' in warnings[1]


def test_can_unlock_db_with_disabled_taxfree_after_period(data_dir, username):
    """Test that with taxfree_after_period being empty the DB can be opened

    Regression test for https://github.com/rotki/rotki/issues/587
    """
    # Set the setting
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    data.db.set_settings(ModifiableDBSettings(taxfree_after_period=-1))

    # now relogin and check that no exception is thrown
    del data
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=False)
    settings = data.db.get_settings()
    assert settings.taxfree_after_period is None


def test_multiple_location_data_and_balances_same_timestamp(data_dir, username):
    """Test that adding location and balance data with same timestamp does not crash.

    Regression test for https://github.com/rotki/rotki/issues/1043
    """
    msg_aggregator = MessagesAggregator()
    username = 'foo'
    userdata_dir = os.path.join(data_dir, username)
    os.mkdir(userdata_dir)
    db = DBHandler(userdata_dir, '123', msg_aggregator)

    balances = [
        AssetBalance(
            time=1590676728,
            asset=A_BTC,
            amount='1.0',
            usd_value='8500',
        ), AssetBalance(
            time=1590676728,
            asset=A_BTC,
            amount='1.1',
            usd_value='9100',
        ),
    ]
    db.add_multiple_balances(balances)
    balances = db.query_timed_balances(from_ts=0, to_ts=1590676728, asset=A_BTC)
    assert len(balances) == 1

    locations = [
        LocationData(
            time=1590676728,
            location='H',
            usd_value='55',
        ), LocationData(
            time=1590676728,
            location='H',
            usd_value='56',
        ),
    ]
    db.add_multiple_location_data(locations)
    locations = db.get_latest_location_value_distribution()
    assert len(locations) == 1
    assert locations[0].usd_value == '55'


def test_set_get_rotkehlchen_premium_credentials(data_dir, username):
    """Test that setting the premium credentials and getting them back from the DB works
    """
    api_key = (
        'kWT/MaPHwM2W1KUEl2aXtkKG6wJfMW9KxI7SSerI6/QzchC45/GebPV9xYZy7f+VKBeh5nDRBJBCYn7WofMO4Q=='
    )
    secret = (
        'TEF5dFFrOFcwSXNrM2p1aDdHZmlndFRoMTZQRWJhU2dacTdscUZSeHZTRmJLRm5ZaVRlV2NYU'
        'llYR1lxMjlEdUtRdFptelpCYmlXSUZGRTVDNWx3NDNYbjIx'
    )
    credentials = PremiumCredentials(
        given_api_key=api_key,
        given_api_secret=secret,
    )

    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    data.db.set_rotkehlchen_premium(credentials)
    returned_credentials = data.db.get_rotkehlchen_premium()
    assert returned_credentials == credentials
    assert returned_credentials.serialize_key() == api_key
    assert returned_credentials.serialize_secret() == secret


def test_unlock_with_invalid_premium_data(data_dir, username):
    """Test that invalid premium credentials unlock still works
    """
    # First manually write invalid data to the DB
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO user_credentials(name, api_key, api_secret) VALUES (?, ?, ?)',
        ('rotkehlchen', 'foo', 'boo'),
    )
    data.db.conn.commit()

    # now relogin and check that no exception is thrown
    del data
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=False)

    # and that an error is logged when trying to get premium
    assert not data.db.get_rotkehlchen_premium()
    warnings = msg_aggregator.consume_warnings()
    errors = msg_aggregator.consume_errors()

    assert len(warnings) == 0
    assert len(errors) == 1
    assert 'Incorrect Rotki API Key/Secret format found in the DB' in errors[0]


@pytest.mark.parametrize('include_etherscan_key', [False])
@pytest.mark.parametrize('include_cryptocompare_key', [False])
def test_get_external_service_credentials(database):
    # Test that if the service is not in DB 'None' is returned
    for service in ExternalService:
        assert not database.get_external_service_credentials(service)

    # add entries for all services
    database.add_external_service_credentials(
        [ExternalServiceApiCredentials(s, f'{s.name.lower()}_key') for s in ExternalService],
    )

    # now make sure that they are returned individually
    for service in ExternalService:
        credentials = database.get_external_service_credentials(service)
        assert credentials.service == service
        assert credentials.api_key == f'{service.name.lower()}_key'
