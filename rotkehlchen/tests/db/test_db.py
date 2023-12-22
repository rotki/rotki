import dataclasses
import logging
import time
from contextlib import suppress
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.accounting.structures.types import ActionType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.accounts import BlockchainAccountData, BlockchainAccounts
from rotkehlchen.constants import ONE, YEAR_IN_SECONDS, ZERO
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_BTC,
    A_DAI,
    A_ETH,
    A_ETH2,
    A_POLYGON_POS_MATIC,
    A_USD,
    A_USDC,
)
from rotkehlchen.constants.misc import USERSDIR_NAME
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import AssetMovementsFilterQuery, TradesFilterQuery
from rotkehlchen.db.misc import detect_sqlcipher_version
from rotkehlchen.db.queried_addresses import QueriedAddresses
from rotkehlchen.db.schema import DB_CREATE_ETH2_DAILY_STAKING_DETAILS
from rotkehlchen.db.settings import (
    DEFAULT_ACCOUNT_FOR_ASSETS_MOVEMENTS,
    DEFAULT_ACTIVE_MODULES,
    DEFAULT_BALANCE_SAVE_FREQUENCY,
    DEFAULT_BTC_DERIVATION_GAP_LIMIT,
    DEFAULT_CALCULATE_PAST_COST_BASIS,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_CURRENT_PRICE_ORACLES,
    DEFAULT_DATE_DISPLAY_FORMAT,
    DEFAULT_DISPLAY_DATE_IN_LOCALTIME,
    DEFAULT_ETH_STAKING_TAXABLE_AFTER_WITHDRAWAL_ENABLED,
    DEFAULT_HISTORICAL_PRICE_ORACLES,
    DEFAULT_INCLUDE_CRYPTO2CRYPTO,
    DEFAULT_INCLUDE_FEES_IN_COST_BASIS,
    DEFAULT_INCLUDE_GAS_COSTS,
    DEFAULT_INFER_ZERO_TIMED_BALANCES,
    DEFAULT_LAST_DATA_MIGRATION,
    DEFAULT_MAIN_CURRENCY,
    DEFAULT_PNL_CSV_HAVE_SUMMARY,
    DEFAULT_PNL_CSV_WITH_FORMULAS,
    DEFAULT_QUERY_RETRY_LIMIT,
    DEFAULT_READ_TIMEOUT,
    DEFAULT_SSF_GRAPH_MULTIPLIER,
    DEFAULT_TREAT_ETH2_AS_ETH,
    DEFAULT_UI_FLOATING_PRECISION,
    ROTKEHLCHEN_DB_VERSION,
    DBSettings,
    ModifiableDBSettings,
)
from rotkehlchen.db.utils import DBAssetBalance, LocationData, SingleDBAssetBalance
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import DBSchemaError, InputError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import PremiumCredentials
from rotkehlchen.serialization.deserialize import deserialize_asset_movement_category
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
)
from rotkehlchen.tests.utils.rotkehlchen import add_starting_balances, add_starting_nfts
from rotkehlchen.types import (
    DEFAULT_ADDRESS_NAME_PRIORITY,
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    CostBasisMethod,
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

TABLES_AT_INIT = [
    'assets',
    'yearn_vaults_events',
    'timed_balances',
    'timed_location_data',
    'asset_movement_category',
    'balance_category',
    'external_service_credentials',
    'user_credentials',
    'user_credentials_mappings',
    'blockchain_accounts',
    'evm_accounts_details',
    'multisettings',
    'trades',
    'evm_transactions',
    'optimism_transactions',
    'evm_internal_transactions',
    'evmtx_receipts',
    'evmtx_receipt_logs',
    'evmtx_receipt_log_topics',
    'evmtx_address_mappings',
    'evm_tx_mappings',
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
    'eth2_daily_staking_details',
    'eth2_validators',
    'ignored_actions',
    'action_type',
    'balancer_events',
    'nfts',
    'history_events',
    'history_events_mappings',
    'ens_mappings',
    'address_book',
    'rpc_nodes',
    'user_notes',
    'evm_events_info',
    'eth_staking_events_info',
    'skipped_external_events',
    'accounting_rules',
    'linked_rules_properties',
    'unresolved_remote_conflicts',
    'key_value_cache',
]


def test_data_init_and_password(data_dir, username, sql_vm_instructions_cb):
    """DB Creation logic and tables at start testing"""
    msg_aggregator = MessagesAggregator()
    # Creating a new data dir should work
    users_dir = data_dir / USERSDIR_NAME
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    assert (users_dir / username).exists()

    # Trying to re-create it should throw
    with pytest.raises(AuthenticationError):
        data.unlock(username, '123', create_new=True, resume_from_backup=False)

    # Trying to unlock a non-existing user without create_new should throw
    with pytest.raises(AuthenticationError):
        data.unlock('otheruser', '123', create_new=False, resume_from_backup=False)

    # now relogin and check all tables are there
    del data
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=False, resume_from_backup=False)
    cursor = data.db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    results = cursor.fetchall()
    results = [result[0] for result in results]
    assert set(results) == set(TABLES_AT_INIT)

    # finally logging in with wrong password should also fail
    del data
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    with pytest.raises(AuthenticationError):
        data.unlock(username, '1234', create_new=False, resume_from_backup=False)


def test_add_remove_exchange(user_data_dir, sql_vm_instructions_cb):
    """Tests that adding and removing an exchange in the DB works.

    Also unknown exchanges should fail
    """
    msg_aggregator = MessagesAggregator()
    db = DBHandler(
        user_data_dir=user_data_dir,
        password='123',
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        resume_from_backup=False,
    )

    # Test that an unknown exchange fails
    with pytest.raises(InputError):
        db.add_exchange('foo', Location.EXTERNAL, 'api_key', 'api_secret')

    with db.conn.read_ctx() as cursor:
        credentials = db.get_exchange_credentials(cursor)
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
        credentials = db.get_exchange_credentials(cursor)

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
    with db.user_write() as cursor:
        db.remove_exchange(cursor, 'kraken1', Location.KRAKEN)
        credentials = db.get_exchange_credentials(cursor)
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
    with db.user_write() as cursor:
        db.remove_exchange(cursor, 'kraken2', Location.KRAKEN)
        credentials = db.get_exchange_credentials(cursor)
    assert len(credentials) == 1
    assert len(credentials[Location.BINANCE]) == 1
    binance = credentials[Location.BINANCE][0]
    assert binance.name == 'binance'
    assert binance.api_key == binance_api_key
    assert binance.api_secret == binance_api_secret


def test_export_import_db(data_dir: Path, username: str, sql_vm_instructions_cb: int) -> None:
    """Create a DB, write some data and then after export/import confirm it's there"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    starting_balance = ManuallyTrackedBalance(
        id=-1,
        asset=A_EUR,
        label='foo',
        amount=FVal(10),
        location=Location.BANKS,
        tags=None,
        balance_type=BalanceType.ASSET,
    )
    with data.db.user_write() as cursor:
        data.db.add_manually_tracked_balances(cursor, [starting_balance])

    encoded_data, _ = data.compress_and_encrypt_db()
    # The server would return them decoded
    data.decompress_and_decrypt_db(encoded_data)
    with data.db.user_write() as cursor:
        balances = data.db.get_manually_tracked_balances(cursor)
    assert balances == [starting_balance]


def test_writing_fetching_data(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    with data.db.user_write() as write_cursor:
        data.db.add_blockchain_accounts(
            write_cursor,
            [BlockchainAccountData(chain=SupportedBlockchain.BITCOIN, address='1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS')],  # noqa: E501
        )
        data.db.add_blockchain_accounts(
            write_cursor,
            [
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address='0xd36029d76af6fE4A356528e4Dc66B2C18123597D'),  # noqa: E501
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address='0x80B369799104a47e98A553f3329812a44A7FaCDc'),  # noqa: E501
                # Add this to 2 evm chains
                BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),  # noqa: E501
                BlockchainAccountData(chain=SupportedBlockchain.POLYGON_POS, address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),  # noqa: E501
            ],
        )

    # add some metadata for only the eth mainnet address
    queried_addresses = QueriedAddresses(data.db)
    queried_addresses.add_queried_address_for_module(
        'makerdao_vaults',
        '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    )  # now some for both
    with data.db.user_write() as write_cursor:
        data.db.save_tokens_for_address(
            write_cursor=write_cursor,
            address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
            blockchain=SupportedBlockchain.ETHEREUM,
            tokens=[A_DAI, A_USDC],
        )
        data.db.save_tokens_for_address(
            write_cursor=write_cursor,
            address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
            blockchain=SupportedBlockchain.POLYGON_POS,
            tokens=[A_POLYGON_POS_MATIC],
        )

    with data.db.conn.read_ctx() as cursor:
        accounts = data.db.get_blockchain_accounts(cursor)
        assert isinstance(accounts, BlockchainAccounts)
        assert accounts.btc == ('1CB7Pbji3tquDtMRp8mBkerimkFzWRkovS',)
        # See that after addition the address has been checksummed
        assert set(accounts.eth) == {
            '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
            '0x80B369799104a47e98A553f3329812a44A7FaCDc',
            '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        }
        assert set(accounts.polygon_pos) == {'0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'}

    with data.db.user_write() as write_cursor:
        # Add existing account should fail
        with pytest.raises(InputError):  # pylint: disable=no-member
            data.db.add_blockchain_accounts(
                write_cursor,
                [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address='0xd36029d76af6fE4A356528e4Dc66B2C18123597D')],  # noqa: E501
            )
        # Remove non-existing account
        with pytest.raises(InputError):
            data.db.remove_single_blockchain_accounts(
                write_cursor,
                SupportedBlockchain.ETHEREUM,
                ['0x136029d76af6fE4A356528e4Dc66B2C18123597D'],
            )
        # Remove existing account
        data.db.remove_single_blockchain_accounts(
            write_cursor,
            SupportedBlockchain.ETHEREUM,
            ['0xd36029d76af6fE4A356528e4Dc66B2C18123597D'],
        )
        accounts = data.db.get_blockchain_accounts(write_cursor)
        assert set(accounts.eth) == {
            '0x80B369799104a47e98A553f3329812a44A7FaCDc',
            '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        }
        # Remove only the polygon account
        data.db.remove_single_blockchain_accounts(
            write_cursor,
            SupportedBlockchain.POLYGON_POS,
            ['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'],
        )
        accounts = data.db.get_blockchain_accounts(write_cursor)
        assert set(accounts.eth) == {
            '0x80B369799104a47e98A553f3329812a44A7FaCDc',
            '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        }
        assert accounts.polygon_pos == ()
        # and also make sure that the relevant meta data of the mainnet account are still there
        assert queried_addresses.get_queried_addresses_for_module(write_cursor, 'makerdao_vaults') == ('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',)  # noqa: E501
        assert data.db.get_tokens_for_address(
            cursor=write_cursor,
            address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
            blockchain=SupportedBlockchain.POLYGON_POS,
        ) == (None, None)
        eth_tokens, _ = data.db.get_tokens_for_address(
            cursor=write_cursor,
            address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
            blockchain=SupportedBlockchain.ETHEREUM,
        )
        assert set(eth_tokens) == {A_DAI, A_USDC}

    with data.db.conn.read_ctx() as cursor:
        ignored_assets_before = data.db.get_ignored_asset_ids(cursor)

    result, _ = data.add_ignored_assets([A_DAO])
    assert result
    result, _ = data.add_ignored_assets([A_DOGE])
    assert result
    result, _ = data.add_ignored_assets([A_DOGE])
    assert result is None

    with data.db.conn.read_ctx() as cursor:
        ignored_asset_ids = data.db.get_ignored_asset_ids(cursor)
        assert ignored_asset_ids - ignored_assets_before == {A_DAO.identifier, A_DOGE.identifier}
        # Test removing asset that is not in the list
        result, msg = data.remove_ignored_assets([A_RDN])
        assert 'not in ignored assets' in msg
        assert result is None
        result, _ = data.remove_ignored_assets([A_DOGE])
        assert result
        assert data.db.get_ignored_asset_ids(cursor) - ignored_assets_before == {A_DAO.identifier}

        # With nothing inserted in settings make sure default values are returned
        result = data.db.get_settings(cursor)
        last_write_diff = ts_now() - result.last_write_ts

    # make sure last_write was within 3 secs
    assert 0 <= last_write_diff < 3
    expected_dict = {
        'have_premium': False,
        'ksm_rpc_endpoint': 'http://localhost:9933',
        'dot_rpc_endpoint': '',
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
        'pnl_csv_with_formulas': DEFAULT_PNL_CSV_WITH_FORMULAS,
        'pnl_csv_have_summary': DEFAULT_PNL_CSV_HAVE_SUMMARY,
        'ssf_graph_multiplier': DEFAULT_SSF_GRAPH_MULTIPLIER,
        'last_data_migration': DEFAULT_LAST_DATA_MIGRATION,
        'non_syncing_exchanges': [],
        'evmchains_to_skip_detection': [],
        'cost_basis_method': CostBasisMethod.FIFO,
        'treat_eth2_as_eth': DEFAULT_TREAT_ETH2_AS_ETH,
        'eth_staking_taxable_after_withdrawal_enabled': DEFAULT_ETH_STAKING_TAXABLE_AFTER_WITHDRAWAL_ENABLED,  # noqa: E501
        'address_name_priority': DEFAULT_ADDRESS_NAME_PRIORITY,
        'include_fees_in_cost_basis': DEFAULT_INCLUDE_FEES_IN_COST_BASIS,
        'infer_zero_timed_balances': DEFAULT_INFER_ZERO_TIMED_BALANCES,
        'query_retry_limit': DEFAULT_QUERY_RETRY_LIMIT,
        'connect_timeout': DEFAULT_CONNECT_TIMEOUT,
        'read_timeout': DEFAULT_READ_TIMEOUT,
    }
    assert len(expected_dict) == len(dataclasses.fields(DBSettings)), 'One or more settings are missing'  # noqa: E501

    # Make sure that results are the same. Comparing like this since we ignore last
    # write ts check
    for field in dataclasses.fields(result):
        assert field.name in expected_dict
        if field.name != 'last_write_ts':
            assert getattr(result, field.name) == expected_dict[field.name]


def test_settings_entry_types(database):
    with database.user_write() as cursor:
        database.set_settings(cursor, ModifiableDBSettings(
            premium_should_sync=True,
            include_crypto2crypto=True,
            ui_floating_precision=1,
            taxfree_after_period=1,
            include_gas_costs=True,
            balance_save_frequency=24,
            date_display_format='%d/%m/%Y %H:%M:%S %z',
            submit_usage_analytics=False,
        ))
        res = database.get_settings(cursor)

    assert isinstance(res.version, int)
    assert res.version == ROTKEHLCHEN_DB_VERSION
    assert isinstance(res.last_write_ts, int)
    assert isinstance(res.premium_should_sync, bool)
    assert res.premium_should_sync is True
    assert isinstance(res.include_crypto2crypto, bool)
    assert res.include_crypto2crypto is True
    assert isinstance(res.ui_floating_precision, int)
    assert res.ui_floating_precision == 1
    assert isinstance(res.taxfree_after_period, int)
    assert res.taxfree_after_period == 1
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
    assert isinstance(res.active_modules, tuple)
    assert res.active_modules == DEFAULT_ACTIVE_MODULES
    assert isinstance(res.frontend_settings, str)
    assert res.frontend_settings == ''


def test_balance_save_frequency_check(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    now = int(time.time())
    data_save_ts = now - 24 * 60 * 60 + 20
    with data.db.user_write() as cursor:
        data.db.add_multiple_location_data(cursor, [LocationData(
            time=data_save_ts, location=Location.KRAKEN.serialize_for_db(), usd_value='1500',  # pylint: disable=no-member
        )])

        assert not data.db.should_save_balances(cursor)
        data.db.set_settings(cursor, ModifiableDBSettings(balance_save_frequency=5))
        assert data.db.should_save_balances(cursor)

        last_save_ts = data.db.get_last_balance_save_time(cursor)
        assert last_save_ts == data_save_ts


def test_sqlcipher_detect_version():
    class QueryMock:
        def __init__(self, version):
            self.version = version

        def fetchall(self):
            return [[self.version]]

    class ConnectionMock:
        def __init__(self, version):
            self.version = version

        def execute(self, command):  # pylint: disable=unused-argument
            return QueryMock(self.version)

        def close(self):
            pass

        def set_progress_handler(self, a, b) -> None:
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

        sql_mock.return_value = ConnectionMock('no version')
        with pytest.raises(ValueError):
            detect_sqlcipher_version()


ASSET_BALANCES = [
    DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1451606400),
        asset=A_USD,
        amount=FVal('10'),
        usd_value=FVal('10'),
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1451606401),
        asset=A_ETH,
        amount=FVal('2'),
        usd_value=FVal('1.7068'),
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1465171200),
        asset=A_USD,
        amount=FVal('500'),
        usd_value=FVal('500'),
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1465171201),
        asset=A_ETH,
        amount=FVal('10'),
        usd_value=FVal('123'),
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1485907200),
        asset=A_USD,
        amount=FVal('350'),
        usd_value=FVal('350'),
    ), DBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1485907201),
        asset=A_ETH,
        amount=FVal('25'),
        usd_value=FVal('249.5'),
    ), DBAssetBalance(
        category=BalanceType.LIABILITY,
        time=Timestamp(1485907201),
        asset=A_ETH,
        amount=FVal('1'),
        usd_value=FVal('9.98'),
    ), DBAssetBalance(
        category=BalanceType.LIABILITY,
        time=Timestamp(1485907201),
        asset=A_DAI,
        amount=FVal('10'),
        usd_value=FVal('10.11'),
    ),
]


def test_query_timed_balances(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    with data.db.user_write() as cursor:
        data.db.set_settings(cursor, settings=ModifiableDBSettings(infer_zero_timed_balances=True))
        data.db.add_multiple_balances(cursor, ASSET_BALANCES)
        result = data.db.query_timed_balances(
            cursor=cursor,
            asset=A_USD,
            balance_type=BalanceType.ASSET,
            from_ts=1451606401,
            to_ts=1485907100,
        )
        assert len(result) == 2  # 1 from db + 1 inferred
        assert result[0].time == 1465171200
        assert result[0].category == BalanceType.ASSET
        assert result[0].amount == FVal('500')
        assert result[0].usd_value == FVal('500')

        all_data = data.db.query_timed_balances(
            cursor=cursor,
            asset=A_ETH,
            balance_type=BalanceType.ASSET,
            from_ts=1451606300,
            to_ts=1485907000,
        )
        assert len(all_data) == 3  # 2 from db + 1 inferred
        result = [x for x in all_data if x.amount != ZERO]
        assert len(result) == 2
        assert result[0].time == 1451606401
        assert result[0].category == BalanceType.ASSET
        assert result[0].amount == FVal('2')
        assert result[0].usd_value == FVal('1.7068')
        assert result[1].time == 1465171201
        assert result[1].category == BalanceType.ASSET
        assert result[1].amount == FVal('10')
        assert result[1].usd_value == FVal('123')

        all_data = data.db.query_timed_balances(cursor, A_ETH, balance_type=BalanceType.ASSET)
        assert len(all_data) == 5  # 3 from db + 2 inferred
        result = [x for x in all_data if x.amount != ZERO]
        assert len(result) == 3
        result = data.db.query_timed_balances(cursor, A_ETH, balance_type=BalanceType.LIABILITY)

    assert len(result) == 1
    assert result[0].time == 1485907201
    assert result[0].category == BalanceType.LIABILITY
    assert result[0].amount == FVal('1')
    assert result[0].usd_value == FVal('9.98')


def test_query_collection_timed_balances(data_dir, username, sql_vm_instructions_cb):
    """Make sure that the collection timed balances get combined and sorted properly"""
    msg_aggregator = MessagesAggregator()
    a_ousdc = Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607')
    asset_balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1451606400),
            asset=A_USDC,
            amount=FVal('10'),
            usd_value=FVal('10'),
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1451606400),
            asset=a_ousdc,
            amount=FVal('10'),
            usd_value=FVal('10'),
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1461606400),
            asset=A_USDC,
            amount=FVal('20'),
            usd_value=FVal('20'),
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=Timestamp(1461606400),
            asset=a_ousdc,
            amount=FVal('20'),
            usd_value=FVal('20'),
        ),
    ]
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    with data.db.user_write() as cursor:
        data.db.set_settings(cursor, settings=ModifiableDBSettings(infer_zero_timed_balances=True))
        data.db.add_multiple_balances(cursor, asset_balances)
        result = data.db.query_collection_timed_balances(
            cursor=cursor,
            collection_id=36,  # USDC collection
        )

    assert result == [SingleDBAssetBalance(
        time=Timestamp(1451606400),
        category=BalanceType.ASSET,
        usd_value=FVal(20),
        amount=FVal(20),
    ), SingleDBAssetBalance(
        category=BalanceType.ASSET,
        time=Timestamp(1461606400),
        amount=FVal(40),
        usd_value=FVal(40),
    )]


def test_timed_balances_inferred_zero_balances(data_dir, username, sql_vm_instructions_cb):
    """
    Test that zero balance entries are inferred properly. (So that the chart in the frontend
    can properly show zero balance periods: https://github.com/rotki/rotki/issues/2822)
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    asset = BalanceType.ASSET.serialize_for_db()
    liability = BalanceType.LIABILITY.serialize_for_db()

    timed_balance_entries = [
        (1514841100, 'ETH', '2', '0', asset),  #
        (1514851200, 'ETH', '2', '0', liability),  # 0
        (1514937600, 'BTC', '1', '0', asset),
        (1514937700, 'BTC', '1', '0', asset),
        (1514937800, 'BTC', '1', '0', asset),  # 0
        (1514937900, 'ETH', '3', '0', asset),  #
        (1514938000, 'BTC', '3', '0', asset),  # 0
        (1514938100, 'BTC', '1', '0', asset),  # 0
    ]

    with data.db.user_write() as write_cursor:
        data.db.set_settings(write_cursor, settings=ModifiableDBSettings(infer_zero_timed_balances=True))  # noqa: E501
        write_cursor.executemany(
            'INSERT INTO timed_balances(timestamp, currency, amount, usd_value, category) '
            'VALUES (?,?,?,?,?)',
            timed_balance_entries,
        )

        all_data = data.db.query_timed_balances(  # sorted by time in ascending order
            cursor=write_cursor,
            asset=A_ETH,
            balance_type=BalanceType.ASSET,
        )
        assert len(all_data) == 6  # 2 from db + 4 inferred zeros
        assert all_data[0].time == 1514841100
        assert all_data[0].amount == FVal('2')
        assert all_data[1].time == 1514851200
        assert all_data[1].amount == ZERO
        assert all_data[2].time == 1514937800
        assert all_data[2].amount == ZERO
        assert all_data[3].time == 1514937900
        assert all_data[3].amount == FVal('3')
        assert all_data[4].time == 1514938000
        assert all_data[4].amount == ZERO
        assert all_data[5].time == 1514938100
        assert all_data[5].amount == ZERO

        # Retest another case
        write_cursor.execute('DELETE FROM timed_balances')

        timed_balance_entries = [
            (1514841100, 'BTC', '1', '0', asset),
            (1514841100, 'ETC', '10', '0', asset),
            (1514842100, 'ETH', '2', '0', asset),  #
            (1514842100, 'BTC', '1', '0', asset),
            (1514843100, 'ETH', '2', '0', asset),  #
            (1514844100, 'BTC', '2', '0', asset),  # 0
            (1514845100, 'BTC', '2', '0', asset),
            (1514846100, 'BTC', '2', '0', asset),  # 0
            (1514847100, 'ETH', '2', '0', asset),  #
            (1514848100, 'BTC', '1', '0', asset),  # 0
            (1514848100, 'LTC', '5', '0', asset),
            (1514849100, 'BTC', '1', '0', asset),  # 0
        ]

        write_cursor.executemany(
            'INSERT INTO timed_balances(timestamp, currency, amount, usd_value, category) '
            'VALUES (?,?,?,?,?)',
            timed_balance_entries,
        )

        all_data = data.db.query_timed_balances(  # sorted by time in ascending order
            cursor=write_cursor,
            asset=A_ETH,
            balance_type=BalanceType.ASSET,
        )
        assert len(all_data) == 7  # 3 from db + 4 inferred zeros
        assert all_data[2].amount == ZERO
        assert all_data[2].time == 1514844100
        assert all_data[3].amount == ZERO
        assert all_data[3].time == 1514846100
        assert all_data[5].amount == ZERO
        assert all_data[5].time == 1514848100
        assert all_data[6].amount == ZERO
        assert all_data[6].time == 1514849100

        # Test a case with ssf_graph_multiplier on
        write_cursor.execute('DELETE FROM timed_balances')
        data.db.set_settings(write_cursor, settings=ModifiableDBSettings(treat_eth2_as_eth=True))
        data.db.set_settings(write_cursor, settings=ModifiableDBSettings(ssf_graph_multiplier=2))

        timed_balance_entries = [
            (1659748923, 'ETH', '2', '0', asset),  #
            (1659748923, 'ETH2', '10', '0', asset),
            # 312 timestamps with 0 balances will be added here due to the ssf_graph_multiplier
            (1686821381, 'ETH', '2', '0', asset),  #
            (1686821381, 'BTC', '1', '0', asset),
            (1686821381, 'LTC', '5', '0', asset),
            (1686822381, 'LTC', '5', '0', asset),  # inferred 0
            (1686823381, 'LTC', '5', '0', asset),
            (1686824381, 'LTC', '5', '0', asset),  # inferred 0
            (1686825013, 'ETH', '2', '0', asset),  #
            (1686825081, 'ETH', '2', '0', asset),  #
            (1686827028, 'ETH', '2', '0', asset),  #
        ]

        write_cursor.executemany(
            'INSERT INTO timed_balances(timestamp, currency, amount, usd_value, category) '
            'VALUES (?,?,?,?,?)',
            timed_balance_entries,
        )

        all_data = data.db.query_timed_balances(  # sorted by time in ascending order
            cursor=write_cursor,
            asset=A_ETH,
            balance_type=BalanceType.ASSET,
        )
    assert len(all_data) == 319  # 5 from db + 312 ssf_graph_multiplier zeros + 2 inferred zeros  # noqa: E501


def test_query_owned_assets(data_dir, username, sql_vm_instructions_cb):
    """Test the get_owned_assets with also an unknown asset in the DB"""
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    with data.db.user_write() as cursor:
        balances = deepcopy(ASSET_BALANCES)
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
        data.db.add_multiple_balances(cursor, balances)

        # also make sure that assets from trades are included
        data.db.add_trades(
            write_cursor=cursor,
            trades=[
                Trade(
                    timestamp=Timestamp(1),
                    location=Location.EXTERNAL,
                    base_asset=A_ETH,
                    quote_asset=A_BTC,
                    trade_type=TradeType.BUY,
                    amount=AssetAmount(ONE),
                    rate=Price(ONE),
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
                    rate=Price(ONE),
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
                    amount=AssetAmount(ONE),
                    rate=Price(ONE),
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
                    amount=AssetAmount(ONE),
                    rate=Price(ONE),
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
                    rate=Price(ONE),
                    fee=Fee(FVal('0.1')),
                    fee_currency=A_BTC,
                    link='',
                    notes='',
                ),
            ])

    with data.db.conn.read_ctx() as cursor:
        assets_list = data.db.query_owned_assets(cursor)
    assert set(assets_list) == {A_USD, A_ETH, A_BTC, A_XMR, A_SDC, A_SDT2, A_SUSHI, A_1INCH}
    assert all(isinstance(x, Asset) for x in assets_list)
    warnings = data.db.msg_aggregator.consume_warnings()
    assert len(warnings) == 0


def test_get_latest_location_value_distribution(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

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


def test_get_latest_asset_value_distribution(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

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

    # test that ignored assets are not ignored in the value distribution by location
    result, _ = data.add_ignored_assets([A_BTC])
    assert result
    assets = data.db.get_latest_asset_value_distribution()
    assert len(assets) == 3
    assert FVal(assets[0].usd_value) > FVal(assets[1].usd_value)
    assert FVal(assets[1].usd_value) > FVal(assets[2].usd_value)


def test_get_netvalue_data(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
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


def test_get_netvalue_data_from_date(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    add_starting_balances(data)

    times, values = data.db.get_netvalue_data(Timestamp(1491607800))
    assert len(times) == 1
    assert times[0] == 1491607800
    assert len(values) == 1
    assert values[0] == '10700.5'


def test_get_netvalue_without_nfts(data_dir, username, sql_vm_instructions_cb):
    """
    Test that the netvalue in a range of time is correctly queried with and without NFTs
    counted in the total.
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    add_starting_nfts(data)
    start_ts = Timestamp(1488326400)

    times, values = data.db.get_netvalue_data(start_ts)
    assert len(times) == 4
    assert len(values) == 4
    assert values[0] == '3000'
    assert values[3] == '5500'

    times, values = data.db.get_netvalue_data(
        from_ts=start_ts,
        include_nfts=False,
    )
    assert len(times) == 4
    assert len(values) == 4
    assert values[0] == '2000'
    assert values[2] == '3000'
    assert values[3] == '4500'


def test_add_trades(data_dir, username, sql_vm_instructions_cb):
    """Test that adding and retrieving trades from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

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
    with data.db.user_write() as cursor:
        data.db.add_trades(cursor, [trade1, trade2])
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        returned_trades = data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501
        assert returned_trades == [trade1, trade2]

        # Add the last 2 trades. Since trade2 already exists in the DB it should be
        # ignored
        data.db.add_trades(cursor, [trade2, trade3])
        returned_trades = data.db.get_trades(cursor, filter_query=TradesFilterQuery.make(), has_premium=True)  # noqa: E501

    assert returned_trades == [trade1, trade2, trade3]


def test_add_margin_positions(data_dir, username, caplog, sql_vm_instructions_cb):
    """Test that adding and retrieving margin positions from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

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
    with data.db.user_write() as cursor:
        data.db.add_margin_positions(cursor, [margin1, margin2])
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        returned_margins = data.db.get_margin_positions(cursor)
        assert returned_margins == [margin1, margin2]

        # Add the last 2 margins. Since margin2 already exists in the DB it should be
        # ignored and a warning should be logged
        data.db.add_margin_positions(cursor, [margin2, margin3])
        assert (
            'Did not add "Margin position with id 0a57acc1f4c09da0f194c59c4cd240e6'
            '8e2d36e56c05b3f7115def9b8ee3943f'
        ) in caplog.text
        returned_margins = data.db.get_margin_positions(cursor)
        assert returned_margins == [margin1, margin2, margin3]


def test_add_asset_movements(data_dir, username, sql_vm_instructions_cb):
    """Test that adding and retrieving asset movements from the DB works fine.

    Also duplicates should be ignored and an error returned
    """
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

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
        location=Location.KRAKEN,
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
    with data.db.user_write() as cursor:
        data.db.add_asset_movements(cursor, [movement1, movement2])
        errors = msg_aggregator.consume_errors()
        warnings = msg_aggregator.consume_warnings()
        assert len(errors) == 0
        assert len(warnings) == 0
        returned_movements = data.db.get_asset_movements(
            cursor=cursor,
            filter_query=AssetMovementsFilterQuery.make(),
            has_premium=True,
        )
        assert returned_movements == [movement1, movement2]

        # Add the last 2 movements. Since movement2 already exists in the DB it should be ignored
        data.db.add_asset_movements(cursor, [movement2, movement3])
        returned_movements = data.db.get_asset_movements(
            cursor=cursor,
            filter_query=AssetMovementsFilterQuery.make(),
            has_premium=True,
        )
    assert returned_movements == [movement1, movement2, movement3]


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

    blockchain_accounts = database.get_blockchain_accounts(cursor)
    eth_accounts = blockchain_accounts.eth
    assert len(eth_accounts) == 1
    assert eth_accounts[0] == valid_address
    errors = database.msg_aggregator.consume_errors()
    warnings = database.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 2
    assert f'Invalid ETH account in DB: {non_checksummed_address}' in warnings[0]
    assert f'Invalid ETH account in DB: {invalid_address}' in warnings[1]


def test_can_unlock_db_with_disabled_taxfree_after_period(data_dir, username, sql_vm_instructions_cb):  # noqa: E501
    """Test that with taxfree_after_period being empty the DB can be opened

    Regression test for https://github.com/rotki/rotki/issues/587
    """
    # Set the setting
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    with data.db.user_write() as cursor:
        data.db.set_settings(cursor, ModifiableDBSettings(taxfree_after_period=-1))

    # now relogin and check that no exception is thrown
    del data
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=False, resume_from_backup=False)
    with data.db.conn.read_ctx() as cursor:
        settings = data.db.get_settings(cursor)
    assert settings.taxfree_after_period is None


def test_timed_balances_primary_key_works(user_data_dir, sql_vm_instructions_cb):
    """
    Test that adding two timed_balances with the same primary key
    i.e (time, currency, category) fails.
    """
    msg_aggregator = MessagesAggregator()
    db = DBHandler(
        user_data_dir=user_data_dir,
        password='123',
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        resume_from_backup=False,
    )
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

    with pytest.raises(InputError) as exc_info, db.user_write() as cursor:
        db.add_multiple_balances(cursor, balances)
    assert exc_info.errisinstance(InputError)
    assert 'Adding timed_balance failed' in str(exc_info.value)

    with db.user_write() as cursor:
        balances = db.query_timed_balances(cursor, asset=A_BTC, balance_type=BalanceType.ASSET)
        assert len(balances) == 0
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
        db.add_multiple_balances(cursor, balances)
    assert len(balances) == 2


@pytest.mark.parametrize('db_settings', [{'treat_eth2_as_eth': True}])
def test_timed_balances_treat_eth2_as_eth(database):
    """
    Test that the setting to treat eth2 as eth calculates correctly the
    ETH2 + ETH values for graphs
    """
    balances = [
        DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            asset=A_ETH,
            amount='1.0',
            usd_value='4000',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            asset=A_ETH2,
            amount='0.4',
            usd_value='5000',
        ), DBAssetBalance(
            category=BalanceType.LIABILITY,
            time=1590676729,
            asset=A_ETH2,
            amount='0.3',
            usd_value='2000',
        ), DBAssetBalance(
            category=BalanceType.LIABILITY,
            time=1590676829,
            asset=A_ETH,
            amount='0.3',
            usd_value='2001',
        ), DBAssetBalance(
            category=BalanceType.LIABILITY,
            time=1590677829,
            asset=A_ETH,
            amount='0.8',
            usd_value='1000',
        ), DBAssetBalance(
            category=BalanceType.LIABILITY,
            time=1590677829,
            asset=A_ETH2,
            amount='0.5',
            usd_value='2000',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590777829,
            asset=A_ETH2,
            amount='0.5',
            usd_value='2000',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590877829,
            asset=A_BTC,
            amount='0.3',
            usd_value='500',
        ), DBAssetBalance(
            category=BalanceType.ASSET,
            time=1590877829,
            asset=A_ETH,
            amount='0.5',
            usd_value='2000',
        ), DBAssetBalance(
            category=BalanceType.LIABILITY,
            time=1590877829,
            asset=A_ETH,
            amount='0.5',
            usd_value='2000',
        ),
    ]

    with database.user_write() as cursor:
        database.set_settings(cursor, ModifiableDBSettings(infer_zero_timed_balances=True))
        database.add_multiple_balances(cursor, balances)
        balances = database.query_timed_balances(cursor, asset=A_BTC, balance_type=BalanceType.ASSET)  # noqa: E501
    assert len(balances) == 1
    expected_balances = [
        SingleDBAssetBalance(
            time=1590877829,
            amount=FVal('0.3'),
            usd_value=FVal('500'),
            category=BalanceType.ASSET,
        ),
    ]
    assert balances == expected_balances

    with database.conn.read_ctx() as cursor:
        balances = database.query_timed_balances(cursor, asset=A_ETH, balance_type=BalanceType.ASSET)  # noqa: E501
    expected_balances = [
        SingleDBAssetBalance(
            category=BalanceType.ASSET,
            time=1590676728,
            amount=FVal('1.4'),
            usd_value=FVal('9000'),
        ), SingleDBAssetBalance(  # start of zero balance period
            category=BalanceType.ASSET,
            time=1590676729,
            amount=ZERO,
            usd_value=ZERO,
        ), SingleDBAssetBalance(  # end of zero balance period
            category=BalanceType.ASSET,
            time=1590677829,
            amount=ZERO,
            usd_value=ZERO,
        ), SingleDBAssetBalance(
            time=1590777829,
            amount=FVal('0.5'),
            usd_value=FVal('2000'),
            category=BalanceType.ASSET,
        ), SingleDBAssetBalance(
            time=1590877829,
            amount=FVal('0.5'),
            usd_value=FVal('2000'),
            category=BalanceType.ASSET,
        ),
    ]
    assert len(balances) == len(expected_balances)
    assert balances == expected_balances


def test_multiple_location_data_and_balances_same_timestamp(user_data_dir, sql_vm_instructions_cb):
    """
    Test that adding location and balance data with same timestamp raises an error
    and no balance/location is added.
    Regression test for https://github.com/rotki/rotki/issues/1043
    """
    msg_aggregator = MessagesAggregator()
    db = DBHandler(
        user_data_dir=user_data_dir,
        password='123',
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        resume_from_backup=False,
    )

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

    with pytest.raises(InputError) as exc_info, db.user_write() as cursor:
        db.add_multiple_balances(cursor, balances)
    assert 'Adding timed_balance failed.' in str(exc_info.value)
    assert exc_info.errisinstance(InputError)

    with db.conn.read_ctx() as cursor:
        balances = db.query_timed_balances(cursor=cursor, from_ts=0, to_ts=1590676728, asset=A_BTC, balance_type=BalanceType.ASSET)  # noqa: E501
    assert len(balances) == 0

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
    with pytest.raises(InputError) as exc_info, db.user_write() as cursor:
        db.add_multiple_location_data(cursor, locations)
    assert 'Tried to add a timed_location_data for' in str(exc_info.value)
    assert exc_info.errisinstance(InputError)

    locations = db.get_latest_location_value_distribution()
    assert len(locations) == 0


def test_set_get_rotkehlchen_premium_credentials(data_dir, username, sql_vm_instructions_cb):
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
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    data.db.set_rotkehlchen_premium(credentials)
    with data.db.conn.read_ctx() as cursor:
        returned_credentials = data.db.get_rotkehlchen_premium(cursor)
    assert returned_credentials == credentials
    assert returned_credentials.serialize_key() == api_key
    assert returned_credentials.serialize_secret() == secret


def test_unlock_with_invalid_premium_data(data_dir, username, sql_vm_instructions_cb):
    """Test that invalid premium credentials unlock still works
    """
    # First manually write invalid data to the DB
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)
    cursor = data.db.conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO user_credentials(name, api_key, api_secret) VALUES (?, ?, ?)',
        ('rotkehlchen', 'foo', 'boo'),
    )
    data.db.conn.commit()

    # now relogin and check that no exception is thrown
    del data
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=False, resume_from_backup=False)

    # and that an error is logged when trying to get premium
    with data.db.conn.read_ctx() as cursor:
        assert not data.db.get_rotkehlchen_premium(cursor)
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


def test_remove_queried_address_on_account_remove(data_dir, username, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    data = DataHandler(data_dir, msg_aggregator, sql_vm_instructions_cb)
    data.unlock(username, '123', create_new=True, resume_from_backup=False)

    with data.db.user_write() as write_cursor:
        data.db.add_blockchain_accounts(
            write_cursor,
            [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address='0xd36029d76af6fE4A356528e4Dc66B2C18123597D')],  # noqa: E501
        )

    with data.db.conn.read_ctx() as cursor:
        queried_addresses = QueriedAddresses(data.db)
        queried_addresses.add_queried_address_for_module(
            'makerdao_vaults',
            '0xd36029d76af6fE4A356528e4Dc66B2C18123597D',
        )
        addresses = queried_addresses.get_queried_addresses_for_module(cursor, 'makerdao_vaults')
        assert '0xd36029d76af6fE4A356528e4Dc66B2C18123597D' in addresses

    with data.db.user_write() as write_cursor:
        data.db.remove_single_blockchain_accounts(
            write_cursor,
            SupportedBlockchain.ETHEREUM,
            ['0xd36029d76af6fE4A356528e4Dc66B2C18123597D'],
        )

    with data.db.conn.read_ctx() as cursor:
        addresses = queried_addresses.get_queried_addresses_for_module(cursor, 'makerdao_vaults')
    assert addresses is None


def test_int_overflow_at_tuple_insertion(database, caplog):
    """Test that if somehow an int that will overflow makes it there we handle it

    Related: https://github.com/rotki/rotki/issues/2175
    """
    caplog.set_level(logging.INFO)
    with database.user_write() as cursor:
        database.add_asset_movements(cursor, [AssetMovement(
            location=Location.KRAKEN,
            category=AssetMovementCategory.DEPOSIT,
            timestamp=177778,
            address='0xfoo',
            transaction_id=99999999999999999999999999999999999999999,
            asset=A_BTC,
            amount=ONE,
            fee_asset=A_BTC,
            fee=Fee(FVal('0.0001')),
            link='a link',
        )])

    errors = database.msg_aggregator.consume_errors()
    assert len(errors) == 1
    assert 'Failed to add "asset_movement" to the DB with overflow error' in errors[0]
    assert 'Overflow error while trying to add "asset_movement" tuples to the DB. Tuples:' in caplog.text  # noqa: E501


@pytest.mark.parametrize(('enum_class', 'query', 'deserialize_from_db', 'deserialize'), [
    (Location, 'SELECT location, seq from location',
        Location.deserialize_from_db, Location.deserialize),
    (TradeType, 'SELECT type, seq from trade_type',
        TradeType.deserialize_from_db, TradeType.deserialize),
    (ActionType, 'SELECT type, seq from action_type',
        ActionType.deserialize_from_db, ActionType.deserialize),
    (AssetMovementCategory, 'SELECT category, seq from asset_movement_category',
        AssetMovementCategory.deserialize_from_db, deserialize_asset_movement_category),
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
        name = deserialize(deserialized.serialize())
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


@pytest.mark.parametrize(('enum_class', 'table_name'), [
    (Location, 'location'),
    (TradeType, 'trade_type'),
    (ActionType, 'action_type'),
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


def test_binance_pairs(user_data_dir, sql_vm_instructions_cb):
    msg_aggregator = MessagesAggregator()
    db = DBHandler(
        user_data_dir=user_data_dir,
        password='123',
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        resume_from_backup=False,
    )

    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')
    db.add_exchange('binance', Location.BINANCE, binance_api_key, binance_api_secret)

    with db.user_write() as write_cursor:
        db.set_binance_pairs(write_cursor, 'binance', ['ETHUSDC', 'ETHBTC', 'BNBBTC'], Location.BINANCE)  # noqa: E501
        query = db.get_binance_pairs('binance', Location.BINANCE)
        assert query == ['ETHUSDC', 'ETHBTC', 'BNBBTC']

        db.set_binance_pairs(write_cursor, 'binance', [], Location.BINANCE)
        query = db.get_binance_pairs('binance', Location.BINANCE)
    assert query == []


def test_fresh_db_adds_version(user_data_dir, sql_vm_instructions_cb):
    """Test that the DB version gets committed to a fresh DB.

    Regression test for https://github.com/rotki/rotki/issues/3744"""
    msg_aggregator = MessagesAggregator()
    db = DBHandler(
        user_data_dir=user_data_dir,
        password='123',
        msg_aggregator=msg_aggregator,
        initial_settings=None,
        sql_vm_instructions_cb=sql_vm_instructions_cb,
        resume_from_backup=False,
    )
    cursor = db.conn.cursor()
    query = cursor.execute(
        'SELECT value FROM settings WHERE name=?;', ('version',),
    )
    query = query.fetchall()
    assert len(query) != 0
    assert int(query[0][0]) == ROTKEHLCHEN_DB_VERSION


def test_db_schema_sanity_check(database: 'DBHandler', caplog) -> None:
    connection = database.conn
    # by default should run without problems
    connection.schema_sanity_check()
    # verify that a the difference in text being upper or lower case doesn't affect the check
    with database.user_write() as write_cursor:
        write_cursor.execute('DROP TABLE eth2_daily_staking_details')
        write_cursor.execute(DB_CREATE_ETH2_DAILY_STAKING_DETAILS.lower())
    connection.schema_sanity_check()

    assert 'Your user database has the following unexpected tables' not in caplog.text, 'Found unexpected table in clean DB'  # noqa: E501
    with suppress(ValueError), database.user_write() as cursor:
        cursor.execute('DROP TABLE rpc_nodes')
        cursor.execute('CREATE TABLE rpc_nodes(column1 INTEGER)')
        cursor.execute('DROP TABLE ens_mappings')
        cursor.execute('CREATE TABLE ens_mappings(column2 TEXT)')
        with pytest.raises(DBSchemaError) as exception_info:
            connection.schema_sanity_check()
        raise ValueError('Do not persist any of the changes')

    assert 'in your user database differ' in str(exception_info.value)
    # Make sure that having an extra table does not break the sanity check
    with database.user_write() as cursor:
        cursor.execute('CREATE TABLE new_table(some_column integer)')
        connection.schema_sanity_check()
        assert "Your user database has the following unexpected tables: {'new_table'}" in caplog.text  # noqa: E501

    with database.user_write() as cursor:
        cursor.execute('DROP TABLE user_notes;')
        with pytest.raises(DBSchemaError) as exception_info:
            connection.schema_sanity_check()
    assert "Tables {'user_notes'} are missing" in str(exception_info.value)


def test_db_add_skipped_external_event_twice(database: 'DBHandler') -> None:
    """Test that adding same skipped event twice in the DB does not duplicate it"""
    data = {'event': 'someid', 'time': 'atime'}
    with database.user_write() as write_cursor:
        for _ in range(2):
            database.add_skipped_external_event(
                write_cursor=write_cursor,
                location=Location.KRAKEN,
                data=data,
                extra_data=None,
            )
            assert write_cursor.execute('SELECT COUNT(*) FROM skipped_external_events').fetchone()[0] == 1  # noqa: E501
