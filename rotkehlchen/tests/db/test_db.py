import logging
import os
import time
from copy import deepcopy
from shutil import copyfile
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures import ActionType, BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.constants import YEAR_IN_SECONDS
from rotkehlchen.constants.assets import A_1INCH, A_BTC, A_DAI, A_ETH, A_USD
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.dbhandler import DBINFO_FILENAME, DBHandler, detect_sqlcipher_version
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.settings import (
    DEFAULT_ACCOUNT_FOR_ASSETS_MOVEMENTS,
    DEFAULT_ACTIVE_MODULES,
    DEFAULT_BALANCE_SAVE_FREQUENCY,
    DEFAULT_BTC_DERIVATION_GAP_LIMIT,
    DEFAULT_CALCULATE_PAST_COST_BASIS,
    DEFAULT_CURRENT_PRICE_ORACLES,
    DEFAULT_DATE_DISPLAY_FORMAT,
    DEFAULT_DISPLAY_DATE_IN_LOCALTIME,
    DEFAULT_HISTORICAL_PRICE_ORACLES,
    DEFAULT_INCLUDE_CRYPTO2CRYPTO,
    DEFAULT_INCLUDE_GAS_COSTS,
    DEFAULT_MAIN_CURRENCY,
    DEFAULT_TAXABLE_LEDGER_ACTIONS,
    DEFAULT_UI_FLOATING_PRECISION,
    ROTKEHLCHEN_DB_VERSION,
    DBSettings,
    ModifiableDBSettings,
)
from rotkehlchen.db.utils import BlockchainAccounts, DBAssetBalance, LocationData
from rotkehlchen.errors import AuthenticationError, InputError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.serialization.deserialize import (
    deserialize_action_type,
    deserialize_action_type_from_db,
    deserialize_asset_movement_category,
    deserialize_asset_movement_category_from_db,
    deserialize_trade_type,
    deserialize_trade_type_from_db,
)
from rotkehlchen.tests.utils.constants import (
    A_DAO,
    A_DOGE,
    A_EUR,
    A_RDN,
    A_SDC,
    A_SDT2,
    A_SUSHI,
    A_XMR,
    DEFAULT_TESTS_MAIN_CURRENCY,
    ETH_ADDRESS1,
    ETH_ADDRESS2,
    ETH_ADDRESS3,
    MOCK_INPUT_DATA,
)
from rotkehlchen.tests.utils.database import mock_dbhandler_update_owned_assets
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
    Price,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps

TABLES_AT_INIT = [
    'assets',
    'aave_events',
    'yearn_vaults_events',
    'timed_balances',
    'timed_location_data',
    'asset_movement_category',
    'balance_category',
    'external_service_credentials',
    'user_credentials',
    'user_credentials_mappings',
    'blockchain_accounts',
    'ethereum_accounts_details',
    'multisettings',
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
    'xpubs',
    'xpub_mappings',
    'amm_swaps',
    'uniswap_events',
    'eth2_deposits',
    'eth2_daily_staking_details',
    'adex_events',
    'ledger_actions',
    'ledger_action_type',
    'ignored_actions',
    'action_type',
    'balancer_events',
    'ledger_actions_gitcoin_data',
    'gitcoin_tx_type',
    'gitcoin_grant_metadata',
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


def test_add_remove_exchange(user_data_dir):
    """Tests that adding and removing an exchange in the DB works.

    Also unknown exchanges should fail
    """
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir, '123', msg_aggregator, None)

    # Test that an unknown exchange fails
    with pytest.raises(InputError):
        db.add_exchange('foo', Location.EXTERNAL, 'api_key', 'api_secret')
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 0

    kraken_api_key1 = ApiKey('kraken_api_key')
    kraken_api_secret1 = ApiSecret(b'kraken_api_secret')
    kraken_api_key2 = ApiKey('kraken_api_key2')
    kraken_api_secret2 = ApiSecret(b'kraken_api_secret2')
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')

    # add mock kraken and binance
    db.add_exchange('kraken1', Location.KRAKEN, kraken_api_key1, kraken_api_secret1)
    db.add_exchange('kraken2', Location.KRAKEN, kraken_api_key2, kraken_api_secret2)
    db.add_exchange('binance', Location.BINANCE, binance_api_key, binance_api_secret)
    # and check the credentials can be retrieved
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 2
    assert len(credentials[Location.KRAKEN]) == 2
    kraken1 = credentials[Location.KRAKEN][0]
    assert kraken1.name == 'kraken1'
    assert kraken1.api_key == kraken_api_key1
    assert kraken1.api_secret == kraken_api_secret1
    kraken2 = credentials[Location.KRAKEN][1]
    assert kraken2.name == 'kraken2'
    assert kraken2.api_key == kraken_api_key2
    assert kraken2.api_secret == kraken_api_secret2
    assert len(credentials[Location.BINANCE]) == 1
    binance = credentials[Location.BINANCE][0]
    assert binance.name == 'binance'
    assert binance.api_key == binance_api_key
    assert binance.api_secret == binance_api_secret

    # remove an exchange and see it works
    db.remove_exchange('kraken1', Location.KRAKEN)
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 2
    assert len(credentials[Location.KRAKEN]) == 1
    kraken2 = credentials[Location.KRAKEN][0]
    assert kraken2.name == 'kraken2'
    assert kraken2.api_key == kraken_api_key2
    assert kraken2.api_secret == kraken_api_secret2
    assert len(credentials[Location.BINANCE]) == 1
    binance = credentials[Location.BINANCE][0]
    assert binance.name == 'binance'
    assert binance.api_key == binance_api_key
    assert binance.api_secret == binance_api_secret

    # remove last exchange of a location and see nothing is returned
    db.remove_exchange('kraken2', Location.KRAKEN)
    credentials = db.get_exchange_credentials()
    assert len(credentials) == 1
    assert len(credentials[Location.BINANCE]) == 1
    binance = credentials[Location.BINANCE][0]
    assert binance.name == 'binance'
    assert binance.api_key == binance_api_key
    assert binance.api_secret == binance_api_secret


def test_export_import_db(data_dir, username):
    """Create a DB, write some data and then after export/import confirm it's there"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    starting_balance = ManuallyTrackedBalance(
        asset=A_EUR,
        label='foo',
        amount=FVal(10),
        location=Location.BANKS,
        tags=None,
    )
    data.db.add_manually_tracked_balances([starting_balance])
    encoded_data, _ = data.compress_and_encrypt_db('123')

    # The server would return them decoded
    encoded_data = encoded_data.decode()  # pylint: disable=no-member
    data.decompress_and_decrypt_db('123', encoded_data)
    balances = data.db.get_manually_tracked_balances()
    assert balances == [starting_balance]


def test_writing_fetching_data(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

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
    with pytest.raises(InputError):  # pylint: disable=no-member
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
    assert 0 <= last_write_diff < 3
    expected_dict = {
        'have_premium': False,
        'eth_rpc_endpoint': 'http://localhost:8545',
        'ksm_rpc_endpoint': 'http://localhost:9933',
        'ui_floating_precision': DEFAULT_UI_FLOATING_PRECISION,
        'version': ROTKEHLCHEN_DB_VERSION,
        'include_crypto2crypto': DEFAULT_INCLUDE_CRYPTO2CRYPTO,
        'include_gas_costs': DEFAULT_INCLUDE_GAS_COSTS,
        'taxfree_after_period': YEAR_IN_SECONDS,
        'balance_save_frequency': DEFAULT_BALANCE_SAVE_FREQUENCY,
        'last_balance_save': 0,
        'main_currency': DEFAULT_MAIN_CURRENCY.identifier,
        'date_display_format': DEFAULT_DATE_DISPLAY_FORMAT,
        'last_data_upload_ts': 0,
        'premium_should_sync': False,
        'submit_usage_analytics': True,
        'last_write_ts': 0,
        'active_modules': DEFAULT_ACTIVE_MODULES,
        'frontend_settings': '',
        'account_for_assets_movements': DEFAULT_ACCOUNT_FOR_ASSETS_MOVEMENTS,
        'btc_derivation_gap_limit': DEFAULT_BTC_DERIVATION_GAP_LIMIT,
        'calculate_past_cost_basis': DEFAULT_CALCULATE_PAST_COST_BASIS,
        'display_date_in_localtime': DEFAULT_DISPLAY_DATE_IN_LOCALTIME,
        'current_price_oracles': DEFAULT_CURRENT_PRICE_ORACLES,
        'historical_price_oracles': DEFAULT_HISTORICAL_PRICE_ORACLES,
        'taxable_ledger_actions': DEFAULT_TAXABLE_LEDGER_ACTIONS,
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
        ui_floating_precision=1,
        taxfree_after_period=1,
        include_gas_costs=True,
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
    assert isinstance(res.eth_rpc_endpoint, str)
    assert res.eth_rpc_endpoint == 'http://localhost:8545'
    assert isinstance(res.balance_save_frequency, int)
    assert res.balance_save_frequency == 24
    assert isinstance(res.last_balance_save, int)
    assert res.last_balance_save == 0
    assert isinstance(res.main_currency, Asset)
    assert res.main_currency == DEFAULT_TESTS_MAIN_CURRENCY
    assert isinstance(res.date_display_format, str)
    assert res.date_display_format == '%d/%m/%Y %H:%M:%S %z'
    assert isinstance(res.submit_usage_analytics, bool)
    assert res.submit_usage_analytics is False
    assert isinstance(res.active_modules, list)
    assert res.active_modules == DEFAULT_ACTIVE_MODULES
    assert isinstance(res.frontend_settings, str)
    assert res.frontend_settings == ''


def test_balance_save_frequency_check(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    now = int(time.time())
    data_save_ts = now - 24 * 60 * 60 + 20
    data.db.add_multiple_location_data([LocationData(
        time=data_save_ts, location=Location.KRAKEN.serialize_for_db(), usd_value='1500',  # pylint: disable=no-member  # noqa: E501
    )])

    assert not data.should_save_balances()
    data.db.set_settings(ModifiableDBSettings(balance_save_frequency=5))
    assert data.should_save_balances()

    last_save_ts = data.db.get_last_balance_save_time()
    assert last_save_ts == data_save_ts


def test_upgrade_sqlcipher_v3_to_v4_without_dbinfo(user_data_dir):
    """Test that we can upgrade from an sqlcipher v3 to v4 rotkehlchen database
    Issue: https://github.com/rotki/rotki/issues/229
    """
    sqlcipher_version = detect_sqlcipher_version()
    if sqlcipher_version != 4:
        # nothing to test
        return

    # get the v3 database file and copy it into the user's data directory
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'sqlcipher_v3_rotkehlchen.db'),
        user_data_dir / 'rotkehlchen.db',
    )

    # the constructor should migrate it in-place and we should have a working DB
    msg_aggregator = MessagesAggregator()
    with mock_dbhandler_update_owned_assets():
        db = DBHandler(user_data_dir, '123', msg_aggregator, None)
        assert db.get_version() == ROTKEHLCHEN_DB_VERSION
        del db  # explicit delete the db so update_owned_assets still runs mocked


def test_upgrade_sqlcipher_v3_to_v4_with_dbinfo(user_data_dir):
    sqlcipher_version = detect_sqlcipher_version()
    if sqlcipher_version != 4:
        # nothing to test
        return

    # get the v3 database file and copy it into the user's data directory
    dir_path = os.path.dirname(os.path.realpath(__file__))
    copyfile(
        os.path.join(os.path.dirname(dir_path), 'data', 'sqlcipher_v3_rotkehlchen.db'),
        user_data_dir / 'rotkehlchen.db',
    )
    dbinfo = {'sqlcipher_version': 3, 'md5_hash': '20c910c28ca42370e4a5f24d6d4a73d2'}
    with open(os.path.join(user_data_dir, DBINFO_FILENAME), 'w') as f:
        f.write(rlk_jsondumps(dbinfo))

    # the constructor should migrate it in-place and we should have a working DB
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir, '123', msg_aggregator, None)
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


asset_balances = [
    DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1451606400),
        asset=A_USD,
        amount='10',
        usd_value='10',
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1451606401),
        asset=A_ETH,
        amount='2',
        usd_value='1.7068',
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1465171200),
        asset=A_USD,
        amount='500',
        usd_value='500',
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1465171201),
        asset=A_ETH,
        amount='10',
        usd_value='123',
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1485907200),
        asset=A_USD,
        amount='350',
        usd_value='350',
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1485907201),
        asset=A_ETH,
        amount='25',
        usd_value='249.5',
    ), DBAssetBalance(
        category=BalanceType.LIABILITY,
        time=Timestamp(1485907201),
        asset=A_ETH,
        amount='1',
        usd_value='9.98',
    ), DBAssetBalance(
        category=BalanceType.LIABILITY,
        time=Timestamp(1485907201),
        asset=A_DAI,
        amount='10',
        usd_value='10.11',
    ),
]


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
    assert result[0].category == BalanceType.ASSET
    assert result[0].amount == '500'
    assert result[0].usd_value == '500'

    result = data.db.query_timed_balances(
        from_ts=1451606300,
        to_ts=1485907000,
        asset=A_ETH,
    )
    assert len(result) == 2
    assert result[0].time == 1451606401
    assert result[0].category == BalanceType.ASSET
    assert result[0].amount == '2'
    assert result[0].usd_value == '1.7068'
    assert result[1].time == 1465171201
    assert result[1].category == BalanceType.ASSET
    assert result[1].amount == '10'
    assert result[1].usd_value == '123'

    result = data.db.query_timed_balances(A_ETH)
    assert len(result) == 4
    result = data.db.query_timed_balances(A_ETH, balance_type=BalanceType.LIABILITY)
    assert len(result) == 1
    assert result[0].time == 1485907201
    assert result[0].category == BalanceType.LIABILITY
    assert result[0].amount == '1'
    assert result[0].usd_value == '9.98'


def test_query_owned_assets(data_dir, username):
    """Test the get_owned_assets with also an unknown asset in the DB"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    balances = deepcopy(asset_balances)
    balances.extend([
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1488326400),
            asset=A_BTC,
            amount='1',
            usd_value='1222.66',
        ),
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1489326500),
            asset=A_XMR,
            amount='2',
            usd_value='33.8',
        ),
    ])
    data.db.add_multiple_balances(balances)
    data.db.conn.commit()

    # also make sure that assets from trades are included
    data.db.add_trades([
        Trade(
            timestamp=Timestamp(1),
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(1)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_BTC,
            link='',
            notes='',
        ), Trade(
            timestamp=Timestamp(99),
            location=Location.EXTERNAL,
            base_asset=A_ETH,
            quote_asset=A_BTC,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(2)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_BTC,
            link='',
            notes='',
        ), Trade(
            timestamp=Timestamp(1),
            location=Location.EXTERNAL,
            base_asset=A_SDC,
            quote_asset=A_SDT2,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(1)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_BTC,
            link='',
            notes='',
        ), Trade(
            timestamp=Timestamp(1),
            location=Location.EXTERNAL,
            base_asset=A_SUSHI,
            quote_asset=A_1INCH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(1)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_BTC,
            link='',
            notes='',
        ), Trade(
            timestamp=Timestamp(3),
            location=Location.EXTERNAL,
            base_asset=A_SUSHI,
            quote_asset=A_1INCH,
            trade_type=TradeType.BUY,
            amount=AssetAmount(FVal(2)),
            rate=Price(FVal(1)),
            fee=Fee(FVal('0.1')),
            fee_currency=A_BTC,
            link='',
            notes='',
        ),
    ])

    assets_list = data.db.query_owned_assets()
    assert set(assets_list) == {A_USD, A_ETH, A_DAI, A_BTC, A_XMR, A_SDC, A_SDT2, A_SUSHI, A_1INCH}  # noqa: E501
    assert all(isinstance(x, Asset) for x in assets_list)
    warnings = data.db.msg_aggregator.consume_warnings()
    assert len(warnings) == 0


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


def test_get_netvalue_data(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    add_starting_balances(data)

    times, values = data.db.get_netvalue_data(Timestamp(0))
    assert len(times) == 3
    assert times[0] == 1451606400
    assert times[1] == 1461606500
    assert times[2] == 1491607800
    assert len(values) == 3
    assert values[0] == '1500'
    assert values[1] == '4500'
    assert values[2] == '10700.5'


def test_get_netvalue_data_from_date(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)
    add_starting_balances(data)

    times, values = data.db.get_netvalue_data(Timestamp(1491607800))
    assert len(times) == 1
    assert times[0] == 1491607800
    assert len(values) == 1
    assert values[0] == '10700.5'


def test_add_trades(data_dir, username, caplog):
    """Test that adding and retrieving trades from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    trade1 = Trade(
        timestamp=1451606400,
        location=Location.KRAKEN,
        base_asset=A_ETH,
        quote_asset=A_EUR,
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
        base_asset=A_BTC,
        quote_asset=A_ETH,
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
        base_asset=A_BTC,
        quote_asset=A_ETH,
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
    # ignored and a warning should be logged
    data.db.add_trades([trade2, trade3])
    assert 'Did not add "buy trade with id a1ed19c8284940b4e59bdac941db2fd3c0ed004ddb10fdd3b9ef0a3a9b2c97bc' in caplog.text  # noqa: E501
    returned_trades = data.db.get_trades()
    assert returned_trades == [trade1, trade2, trade3]


def test_add_margin_positions(data_dir, username, caplog):
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
    # ignored and a warning should be logged
    data.db.add_margin_positions([margin2, margin3])
    assert (
        'Did not add "Margin position with id 0a57acc1f4c09da0f194c59c4cd240e6'
        '8e2d36e56c05b3f7115def9b8ee3943f'
    ) in caplog.text
    returned_margins = data.db.get_margin_positions()
    assert returned_margins == [margin1, margin2, margin3]


def test_add_asset_movements(data_dir, username, caplog):
    """Test that adding and retrieving asset movements from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    movement1 = AssetMovement(
        location=Location.BITMEX,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id=None,
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
        address='0xfoo',
        transaction_id='0xboo',
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
        address='0xcoo',
        transaction_id='0xdoo',
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
    # ignored and a warning should be logged
    data.db.add_asset_movements([movement2, movement3])
    assert (
        'Did not add "withdrawal of ETH with id 94405f38c7b86dd2e7943164d'
        '67ff44a32d56cef25840b3f5568e23c037fae0a'
    ) in caplog.text
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
    assert f'Invalid ETH account in DB: {non_checksummed_address}' in warnings[0]
    assert f'Invalid ETH account in DB: {invalid_address}' in warnings[1]


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


def test_timed_balances_primary_key_works(user_data_dir):
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir, '123', msg_aggregator, None)
    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            asset=A_BTC,
            amount='1.0',
            usd_value='8500',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            asset=A_BTC,
            amount='1.1',
            usd_value='9100',
        ),
    ]
    db.add_multiple_balances(balances)
    warnings = msg_aggregator.consume_warnings()
    errors = msg_aggregator.consume_errors()
    assert len(warnings) == 1
    assert len(errors) == 0
    balances = db.query_timed_balances(asset=A_BTC)
    assert len(balances) == 1

    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            asset=A_ETH,
            amount='1.0',
            usd_value='8500',
        ), DBAssetBalance(
            category=BalanceType.LIABILITY,
            time=1590676728,
            asset=A_ETH,
            amount='1.1',
            usd_value='9100',
        ),
    ]
    db.add_multiple_balances(balances)
    warnings = msg_aggregator.consume_warnings()
    errors = msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    balances = db.query_timed_balances(asset=A_ETH)
    assert len(balances) == 2


def test_multiple_location_data_and_balances_same_timestamp(user_data_dir):
    """Test that adding location and balance data with same timestamp does not crash.

    Regression test for https://github.com/rotki/rotki/issues/1043
    """
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir, '123', msg_aggregator, None)

    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            asset=A_BTC,
            amount='1.0',
            usd_value='8500',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
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
    assert 'Incorrect rotki API Key/Secret format found in the DB' in errors[0]


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


def test_remove_queried_address_on_account_remove(data_dir, username):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator)
    data.unlock(username, '123', create_new=True)

    data.db.add_blockchain_accounts(
        SupportedBlockchain.ETHEREUM,
        [
            BlockchainAccountData(address='0xd36029d76af6fE4A356528e4Dc66B2C18123597D'),
        ],
    )

    queried_addresses = QueriedAddresses(data.db)
    queried_addresses.add_queried_address_for_module(
        'makerdao_vaults',
        '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
    )
    addresses = queried_addresses.get_queried_addresses_for_module('makerdao_vaults')
    assert '0xd36029d76af6fE4A356528e4Dc66B2C18123597D' in addresses

    data.db.remove_blockchain_accounts(
        SupportedBlockchain.ETHEREUM,
        ['0xd36029d76af6fE4A356528e4Dc66B2C18123597D'],
    )
    addresses = queried_addresses.get_queried_addresses_for_module('makerdao_vaults')
    assert not addresses


def test_int_overflow_at_tuple_insertion(database, caplog):
    """Test that if somehow an int that will overflow makes it there we handle it

    Related: https://github.com/rotki/rotki/issues/2175
    """
    caplog.set_level(logging.INFO)
    database.add_asset_movements([AssetMovement(
        location=Location.BITTREX,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=177778,
        address='0xfoo',
        transaction_id=99999999999999999999999999999999999999999,
        asset=A_BTC,
        amount=FVal(1),
        fee_asset=A_BTC,
        fee=Fee(FVal('0.0001')),
        link='a link',
    )])

    errors = database.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Failed to add "asset_movement" to the DB with overflow error' in errors[0]
    assert 'Overflow error while trying to add "asset_movement" tuples to the DB. Tuples:' in caplog.text  # noqa: E501


@pytest.mark.parametrize('enum_class, query, deserialize_from_db, deserialize', [
    (Location, 'SELECT location, seq from location',
        Location.deserialize_from_db, Location.deserialize),
    (TradeType, 'SELECT type, seq from trade_type',
        deserialize_trade_type_from_db, deserialize_trade_type),
    (ActionType, 'SELECT type, seq from action_type',
        deserialize_action_type_from_db, deserialize_action_type),
    (LedgerActionType, 'SELECT type, seq from ledger_action_type',
        LedgerActionType.deserialize_from_db, LedgerActionType.deserialize),
    (AssetMovementCategory, 'SELECT category, seq from asset_movement_category',
        deserialize_asset_movement_category_from_db, deserialize_asset_movement_category),
])
def test_enum_in_db(database, enum_class, query, deserialize_from_db, deserialize):
    """
    Test that all enum represented in DB deserialize to a valid matching Enum class
    """
    # Query for all objects in the db table
    cursor = database.conn.cursor()
    query_result = cursor.execute(query)

    # We deserialize, then serialize and compare the result
    for letter, seq in query_result:
        deserialized = deserialize_from_db(letter)
        assert deserialized.value == seq
        assert enum_class(seq).serialize_for_db() == letter
        name = deserialize(str(deserialized))
        assert name == deserialized


def test_all_balance_types_in_db(database):
    """
    Test that all balance_category in DB deserialize to a valid BalanceType
    """
    # Query for all balace_category rows
    cursor = database.conn.cursor()
    balance_types = cursor.execute('SELECT category, seq from balance_category')

    # We deserialize, then serialize and compare the result
    for category, seq in balance_types:
        deserialized_balance_type = BalanceType.deserialize_from_db(category)
        assert deserialized_balance_type.value == seq
        balance_type_serialization = BalanceType(
            deserialized_balance_type.value,
        ).serialize_for_db()
        assert category == balance_type_serialization


@pytest.mark.parametrize('enum_class, table_name', [
    (Location, 'location'),
    (TradeType, 'trade_type'),
    (ActionType, 'action_type'),
    (LedgerActionType, 'ledger_action_type'),
    (BalanceType, 'balance_category'),
    (AssetMovementCategory, 'asset_movement_category'),
])
def test_values_are_present_in_db(database, enum_class, table_name):
    """
    Check that all enum classes have the same number of possible values
    in the class definition as in the database
    """
    cursor = database.conn.cursor()
    query = f'SELECT COUNT(*) FROM {table_name} WHERE seq=?'

    for enum_class_entry in enum_class:
        r = cursor.execute(query, (enum_class_entry.value,))
        assert r.fetchone() == (1,)


def test_binance_pairs(user_data_dir):
    msg_aggregator = MessagesAggregator()
    db = DBHandler(user_data_dir, '123', msg_aggregator, None)

    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')
    db.add_exchange('binance', Location.BINANCE, binance_api_key, binance_api_secret)

    db.set_binance_pairs('binance', ['ETHUSDC', 'ETHBTC', 'BNBBTC'], Location.BINANCE)
    query = db.get_binance_pairs('binance', Location.BINANCE)
    assert query == ['ETHUSDC', 'ETHBTC', 'BNBBTC']

    db.set_binance_pairs('binance', [], Location.BINANCE)
    query = db.get_binance_pairs('binance', Location.BINANCE)
    assert query == []
