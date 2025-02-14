import warnings as test_warnings
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_1INCH, A_BTC, A_ETH, A_EUR, A_SOL, A_USD, A_USDC
from rotkehlchen.db.filtering import HistoryEventFilterQuery, TradesFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.exchanges.coinbase import Coinbase
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import AssetMovement
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_XTZ
from rotkehlchen.tests.utils.exchanges import TRANSACTIONS_RESPONSE, mock_normal_coinbase_query
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Location, TimestampMS, TradeType
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.fixture(name='mock_coinbase')
def fixture_mock_coinbase(messages_aggregator) -> Coinbase:
    return Coinbase('coinbase1', 'a', b'a', object(), messages_aggregator)  # type: ignore


def test_name(mock_coinbase):
    assert mock_coinbase.location == Location.COINBASE
    assert mock_coinbase.name == 'coinbase1'


def test_coinbase_query_balances(function_scope_coinbase):
    """Test that coinbase balance query works fine for the happy path"""
    coinbase = function_scope_coinbase

    def mock_coinbase_accounts(url, timeout):  # pylint: disable=unused-argument
        return MockResponse(
            200,
            """
{
  "pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
  },
  "data": [
    {
      "id": "58542935-67b5-56e1-a3f9-42686e07fa40",
      "name": "My Vault",
      "primary": false,
      "type": "vault",
      "currency": "BTC",
      "balance": {
        "amount": "4.00000000",
        "currency": "BTC"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/58542935-67b5-56e1-a3f9-42686e07fa40",
      "ready": true
    },
    {
      "id": "2bbf394c-193b-5b2a-9155-3b4732659ede",
      "name": "My Wallet",
      "primary": true,
      "type": "wallet",
      "currency": "ETH",
      "balance": {
        "amount": "39.59000000",
        "currency": "ETH"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede"
    },
    {
      "id": "68542935-67b5-56e1-a3f9-42686e07fa40",
      "name": "Another Wallet",
      "primary": false,
      "type": "vault",
      "currency": "BTC",
      "balance": {
        "amount": "1.230000000",
        "currency": "BTC"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/68542935-67b5-56e1-a3f9-42686e07fa40",
      "ready": true
    }
  ]
}
            """,
        )

    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_accounts):
        balances, msg = coinbase.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC].amount == FVal('5.23')
    assert balances[A_BTC].usd_value == FVal('7.8450000000')
    assert balances[A_ETH].amount == FVal('39.59')
    assert balances[A_ETH].usd_value == FVal('59.385000000')

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0


def test_coinbase_query_balances_unexpected_data(function_scope_coinbase):
    """Test that coinbase balance query works fine for the happy path"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0
    data = """{
    "data": [
    {
      "id": "58542935-67b5-56e1-a3f9-42686e07fa40",
      "name": "My Vault",
      "primary": false,
      "type": "vault",
      "currency": "BTC",
      "balance": {
        "amount": "4.00000000",
        "currency": "BTC"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-01-31T20:49:02Z",
      "resource": "account",
      "resource_path": "/v2/accounts/58542935-67b5-56e1-a3f9-42686e07fa40",
      "ready": true
    }]}"""

    def query_coinbase_and_test_local_mock(
            response_str,
            expected_warnings_num,
            expected_errors_num,
            expected_balances_for_no_warnings=1,
            contains_expected_msg=None,
    ):
        def mock_coinbase_accounts(url, timeout):  # pylint: disable=unused-argument
            return MockResponse(200, response_str)

        with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_accounts):
            balances, msg = coinbase.query_balances()

        warnings = coinbase.msg_aggregator.consume_warnings()
        errors = coinbase.msg_aggregator.consume_errors()
        if contains_expected_msg:
            assert balances is None
            assert contains_expected_msg in msg
        elif expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(warnings) == 0
            assert len(errors) == 0
            assert msg == ''
            assert len(balances) == expected_balances_for_no_warnings
            if len(balances) != 0:
                assert balances[A_BTC].amount == FVal('4')
                assert balances[A_BTC].usd_value == FVal('6')
        else:
            assert len(warnings) == expected_warnings_num
            assert len(errors) == expected_errors_num
            assert msg == ''
            assert len(balances) == 0

    # test that all is fine with normal data
    query_coinbase_and_test_local_mock(data, expected_warnings_num=0, expected_errors_num=0)

    # From now on unexpected data
    # no data key
    query_coinbase_and_test_local_mock(
        '{"foo": 1}',
        expected_warnings_num=0,
        expected_errors_num=0,
        contains_expected_msg='Coinbase API request failed. Check logs for more details',
    )
    # account entry without "balance" key
    input_data = data.replace('"balance"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=0, expected_balances_for_no_warnings=0)  # noqa: E501
    # account entry without amount in "balance"
    input_data = data.replace('"amount"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=0, expected_balances_for_no_warnings=0)  # noqa: E501
    # account entry without currency in "balance"
    input_data = data.replace('"currency"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=0, expected_balances_for_no_warnings=0)  # noqa: E501
    # account entry with invalid balance amount
    input_data = data.replace('"4.00000000"', '"csadasdsd"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=0, expected_balances_for_no_warnings=0)  # noqa: E501
    # account entry with unknown asset
    input_data = data.replace('"BTC"', '"DDSADSAD"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=0, expected_balances_for_no_warnings=0)  # noqa: E501
    # account entry with invalid asset
    input_data = data.replace('"BTC"', 'null')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=0, expected_balances_for_no_warnings=0)  # noqa: E501


def test_coinbase_query_trade_history(function_scope_coinbase):
    """Test that coinbase trade history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=ts_now(),
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 3
    expected_trades = [Trade(
        timestamp=1566687695,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=FVal('0.05772716'),
        rate=FVal('190.378324518302996371205512275331057339387560378858062651964863679418838550173'),
        fee=None,
        fee_currency=None,
        link='txid-1',
    ), Trade(
        timestamp=1569366095,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=FVal('0.05772715'),
        rate=FVal('190.205128782557254255579913437611245315245945798467445560711034582514466763040'),
        fee=None,
        fee_currency=None,
        link='txid-2',
    ), Trade(
        timestamp=1733150783,
        location=Location.COINBASE,
        base_asset=A_USDC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=FVal('10.482180'),
        rate=FVal('0.952092026658576746440148900324169209076737854148659916162477652549374271382480'),
        fee=FVal('0.099839'),
        fee_currency=A_USDC,
        link='id9',
    )]
    assert trades == expected_trades

    # and now try only a smaller time range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=1566689695,
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 1
    assert trades[0].trade_type == TradeType.BUY
    assert trades[0].timestamp == 1566687695


def _create_coinbase_mock(transactions_response):
    """Creates a mock function used for mocking Coinbase API responses.

    Mocks both the transactions and accounts endpoints with mock data.
    """
    def mock_coinbase_query(url, **kwargs):  # pylint: disable=unused-argument
        if 'transaction' in url:
            if 'next-page' in url:
                return MockResponse(200, TRANSACTIONS_RESPONSE)
            # else
            return MockResponse(200, transactions_response)
        if 'accounts' in url:
            # keep it simple just return a single ID and ignore the rest of the fields
            return MockResponse(200, '{"data": [{"id": "5fs23", "updated_at": "2020-06-08T02:32:16Z"}]}')  # noqa: E501
        # else
        raise AssertionError(f'Unexpected url {url} for test')

    return mock_coinbase_query


def query_coinbase_and_test(
        coinbase,
        transactions_response=TRANSACTIONS_RESPONSE,
        expected_warnings_num=0,
        expected_errors_num=0,
        # Since this test only mocks as breaking only one of the three actions by default
        expected_actions_num=2,
        expected_ws_messages_num=0,
):
    now = ts_now()

    mock_coinbase_query = _create_coinbase_mock(transactions_response)

    with coinbase.db.user_write() as write_cursor:  # clean saved ranges to try again
        coinbase.db.purge_exchange_data(write_cursor=write_cursor, location=Location.COINBASE)
    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_query):
        coinbase._query_transactions()

    filter_query = TradesFilterQuery.make(from_ts=0, to_ts=now, location=Location.COINBASE)
    with coinbase.db.conn.read_ctx() as cursor:
        actions = coinbase.db.get_trades(
            cursor=cursor,
            filter_query=filter_query,
            has_premium=True,
        )

    errors = coinbase.msg_aggregator.consume_errors()
    warnings = coinbase.msg_aggregator.consume_warnings()
    assert len(actions) == expected_actions_num
    assert len(errors) == expected_errors_num
    assert len(warnings) == expected_warnings_num
    if expected_ws_messages_num != 0:
        assert len(coinbase.msg_aggregator.rotki_notifier.messages) == expected_ws_messages_num


def test_coinbase_query_trade_history_unexpected_data(function_scope_coinbase):
    """Test that coinbase trade history query handles unexpected data properly"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    # first query with proper data and expect no errors
    query_coinbase_and_test(
        coinbase=coinbase,
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=3,
    )

    # invalid created_at timestamp
    broken_response = TRANSACTIONS_RESPONSE.replace('"2019-08-24T23:01:35Z"', '"dadssd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        transactions_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid asset format
    broken_response = TRANSACTIONS_RESPONSE.replace('"ETH"', '123')
    query_coinbase_and_test(
        coinbase=coinbase,
        transactions_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=4,
        expected_actions_num=1,
    )

    # invalid transaction type
    broken_response = TRANSACTIONS_RESPONSE.replace('"buy",', 'null,')
    query_coinbase_and_test(
        coinbase=coinbase,
        transactions_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=2,
    )

    # invalid amount
    broken_response = TRANSACTIONS_RESPONSE.replace('"0.05772716"', '"gfgfg"')
    query_coinbase_and_test(
        coinbase=coinbase,
        transactions_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid native amount
    broken_response = TRANSACTIONS_RESPONSE.replace('"10.99"', 'false')
    query_coinbase_and_test(
        coinbase=coinbase,
        transactions_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # missing key error
    broken_response = TRANSACTIONS_RESPONSE.replace('"status": "completed",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        transactions_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=3,
        expected_actions_num=0,
    )


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_query_trade_history_unknown_asset(function_scope_coinbase):
    """Test that coinbase trade history query handles unknown asset properly"""
    query_coinbase_and_test(
        coinbase=function_scope_coinbase,
        transactions_response=TRANSACTIONS_RESPONSE.replace('"ETH"', '"dsadsad"'),
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=1,
        expected_ws_messages_num=4,
    )


def test_coinbase_query_trade_history_paginated(function_scope_coinbase):
    """Test that coinbase trade history query can deal with paginated response"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    paginated_transactions_response = TRANSACTIONS_RESPONSE.replace(
        '"next_uri": null',
        '"next_uri": "/v2/transactions/?next-page"',
    )
    query_coinbase_and_test(
        coinbase=coinbase,
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=3,
        transactions_response=paginated_transactions_response,
    )


def test_coinbase_staking_events(
        database: 'DBHandler',
        function_scope_coinbase: 'Coinbase',
) -> None:
    """Regression test for a problem where staking events were shown twice."""
    coinbase = function_scope_coinbase
    original_api_query = coinbase._api_query

    def mock_api_query(endpoint: str, **kwargs: Any) -> list:
        """Mock coinbase api query to return some staking events for the transactions endpoint.
        Otherwise call the original query function so it uses mock_normal_coinbase_query.
        """
        if '/transactions' in endpoint:
            return [
                {'amount': {'amount': '5.5776172514', 'currency': 'DOT'}, 'created_at': '2024-01-01T16:19:24Z', 'id': 'tx_id_1', 'native_amount': {'amount': '46.68', 'currency': 'USD'}, 'resource': 'transaction', 'resource_path': '/v2/accounts/account_id_1/transactions/tx_id_1', 'status': 'completed', 'type': 'staking_transfer'},  # noqa: E501
                {'amount': {'amount': '-5.5776172514', 'currency': 'DOT'}, 'created_at': '2024-01-01T16:19:24Z', 'id': 'tx_id_2', 'native_amount': {'amount': '-46.68', 'currency': 'USD'}, 'resource': 'transaction', 'resource_path': '/v2/accounts/account_id_2/transactions/tx_id_2', 'status': 'completed', 'type': 'staking_transfer'},  # noqa: E501
            ]

        return original_api_query(endpoint, kwargs)

    with (
        patch.object(coinbase, '_api_query', side_effect=mock_api_query),
        patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query),
    ):
        coinbase.query_history_events()

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.COINBASE),
            has_premium=True,
        )

    assert events == [HistoryEvent(
        identifier=1,
        event_identifier='CBE_tx_id_1',
        sequence_index=0,
        timestamp=TimestampMS(1704125964000),
        location=Location.COINBASE,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=asset_from_coinbase('DOT'),
        location_label=coinbase.name,
        amount=FVal('5.5776172514'),
        notes='Stake 5.5776172514 DOT in Coinbase',
    )]


def test_coinbase_query_history_events(
        database,
        function_scope_coinbase,
        price_historian,    # pylint: disable=unused-argument
):
    """Test that coinbase deposit/withdrawals history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        coinbase.query_history_events()

    with database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(database).get_history_events(
            cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.COINBASE),
            has_premium=True,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(events) == 8
    expected_events = [AssetMovement(
        identifier=4,
        event_identifier='582c2b78e88052d879b203fd07b6fca15f90417da7f715dcda72275b8d290054',
        location=Location.COINBASE,
        location_label=coinbase.name,
        event_type=HistoryEventType.DEPOSIT,
        timestamp=TimestampMS(1502554304000),
        asset=A_BTC,
        amount=FVal('0.10181673'),
        extra_data={
            'transaction_id': 'ccc',
            'reference': 'id3',
        },
    ), AssetMovement(
        identifier=1,
        event_identifier='157b922cd6b7d3be91d0d3c2e197153dfb91dd9f8d2507eb83b9e3d477a5e6fd',
        location=Location.COINBASE,
        location_label=coinbase.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726126000),
        asset=A_ETH,
        amount=FVal('0.05749427'),
        extra_data={
            'address': '0x6dcD6449dbCa615e40d696328209686eA95327b2',
            'transaction_id': '0x558bfa4d2a4ef598ddb92233459c00eda9e6c14cda75e6773b90208cb6938169',
            'reference': 'id1',
        },
    ), AssetMovement(
        identifier=3,
        event_identifier='af84752f7e7bcdd99c91dd856a117086df6205e26f0c8f6e530dfd5f3ff5add1',
        location=Location.COINBASE,
        location_label=coinbase.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726126000),
        asset=A_ETH,
        amount=FVal('0.05770427'),
        extra_data={
            'address': '0x6dcD6449dbCa615e40d696328209686eA95327b2',
            'reference': 'id2',
        },
    ), AssetMovement(
        identifier=2,
        event_identifier='157b922cd6b7d3be91d0d3c2e197153dfb91dd9f8d2507eb83b9e3d477a5e6fd',
        location=Location.COINBASE,
        location_label=coinbase.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1566726126000),
        asset=A_ETH,
        amount=FVal('0.00021'),
        is_fee=True,
    ), HistoryEvent(
        identifier=5,
        event_identifier='CBE_id4',
        sequence_index=0,
        timestamp=TimestampMS(1609877514000),
        location=Location.COINBASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=asset_from_coinbase('NMR'),
        location_label=coinbase.name,
        amount=FVal('0.02762431'),
        notes='Received 0.02762431 NMR ($1.01) from coinbase earn',
    ), HistoryEvent(
        identifier=6,
        event_identifier='CBE_id5',
        sequence_index=0,
        timestamp=TimestampMS(1611426233000),
        location=Location.COINBASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=asset_from_coinbase('ALGO'),
        location_label=coinbase.name,
        amount=FVal('0.000076'),
        notes='Received 0.000076 ALGO ($0.00) as inflation_reward',
    ), HistoryEvent(
        identifier=8,
        event_identifier='CBE_id6',
        sequence_index=0,
        timestamp=TimestampMS(1611512633000),
        location=Location.COINBASE,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REWARD,
        asset=asset_from_coinbase('SOL'),
        location_label=coinbase.name,
        amount=FVal('0.025412'),
        notes='Receive 0.025412 SOL as Coinbase staking reward',
    ), AssetMovement(
        identifier=7,
        event_identifier='1181793af14ed42cb443d55ce50f68deef95b320c114025cb25a988f005a3a76',
        location=Location.COINBASE,
        location_label=coinbase.name,
        event_type=HistoryEventType.WITHDRAWAL,
        timestamp=TimestampMS(1615493615000),
        asset=A_BTC,
        amount=FVal('0.00100000'),
        extra_data={'reference': 'id6'},
    )]
    assert expected_events == events


def test_asset_conversion(mock_coinbase):
    tx_id = '77c5ad72-764e-414b-8bdb-b5aed20fb4b1'
    trade_b = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-1000.000000',
            'currency': 'USDC',
        },
        'native_amount': {
            'amount': '-1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:15Z',
        'updated_at': '2021-06-08T02:32:15Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted from USD Coin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 1,000.0000 USDC ($1,000.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_a = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '0.01694165',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '910.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted to Bitcoin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 0.01694165 BTC ($910.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_pairs = {tx_id: [trade_a, trade_b]}
    trades = mock_coinbase._process_trades_from_conversion(trade_pairs)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_USDC,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('1000.0'),
        rate=FVal('0.00001694165'),
        fee=FVal('90'),
        fee_currency=A_USDC,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trades == [expected_trade]


def test_conversion_with_fee(mock_coinbase):
    tx_id = '61258a99-7e8a-4ece-94cf-485b33d09319'
    trade_b = {'amount': {'amount': '-10.571942', 'currency': 'USDC'}, 'created_at': '2024-12-06T10:27:56Z', 'id': '39073929-386e-58a2-9ec4-d8371a395a9e', 'native_amount': {'amount': '-10.00', 'currency': 'EUR'}, 'resource': 'transaction', 'resource_path': '/v2/accounts/40e03599-5601-534c-95c2-0db5f5c5e652/transactions/39073929-386e-58a2-9ec4-d8371a395a9e', 'status': 'completed', 'trade': {'fee': {'amount': '0.109974', 'currency': 'USDC'}, 'id': '61258a99-7e8a-4ece-94cf-485b33d09319', 'payment_method_name': 'billetera de USDC'}, 'type': 'trade'}  # noqa: E501
    trade_a = {'amount': {'amount': '0.00266121', 'currency': 'ETH'}, 'created_at': '2024-12-06T10:27:57Z', 'id': 'e34548a2-4eec-54fc-a13f-6b48996e9ecf', 'native_amount': {'amount': '9.70', 'currency': 'EUR'}, 'resource': 'transaction', 'resource_path': '/v2/accounts/16ff1367-5834-5827-95f3-f503d891421c/transactions/e34548a2-4eec-54fc-a13f-6b48996e9ecf', 'status': 'completed', 'trade': {'fee': {'amount': '0.109974', 'currency': 'USDC'}, 'id': '61258a99-7e8a-4ece-94cf-485b33d09319', 'payment_method_name': 'billetera de USDC'}, 'type': 'trade'}  # noqa: E501

    trade_pairs = {tx_id: [trade_a, trade_b]}
    trades = mock_coinbase._process_trades_from_conversion(trade_pairs)

    assert len(trades) == 1
    assert [Trade(
        timestamp=1733480877,
        location=Location.COINBASE,
        base_asset=A_USDC,
        quote_asset=A_ETH,
        trade_type=TradeType.SELL,
        amount=FVal('10.571942'),
        rate=FVal('0.000251723855465722380996793209800053764956334418028400080136648498449953660358712'),
        fee=FVal('0.1162638749508'),
        fee_currency=A_USDC,
        link=tx_id,
    )] == trades


def test_asset_conversion_no_second_transaction(mock_coinbase):
    tx_id = '77c5ad72-764e-414b-8bdb-b5aed20fb4b1'
    trade_a = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '450',
            'currency': 'XTZ',
        },
        'native_amount': {
            'amount': '540',
            'currency': 'USD',
        },
        'created_at': '2020-06-08T02:32:15Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'trade': {
            'fee': {
                'amount': '1',
                'currency': 'XTZ',
            },
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'payment_method_name': 'ETH Wallet',
        },
    }

    trade_pairs, trades = {tx_id: [trade_a]}, []
    trades = mock_coinbase._process_trades_from_conversion(trade_pairs)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_XTZ,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal('450'),
        rate=FVal('1.2'),
        fee=ONE,
        fee_currency=A_XTZ,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trades == [expected_trade]


def test_asset_conversion_not_stable_coin(mock_coinbase):
    """Test a conversion using a from asset that is not a stable coin"""
    tx_id = '77c5ad72-764e-414b-8bdb-b5aed20fb4b1'
    trade_a = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-6000.000000',
            'currency': '1INCH',
        },
        'native_amount': {
            'amount': '-1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:15Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted from USD Coin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 1,000.0000 USDC ($1,000.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }
    trade_b = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '0.01694165',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '910.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2020-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted to Bitcoin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 0.01694165 BTC ($910.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_pairs = {tx_id: [trade_a, trade_b]}
    trades = mock_coinbase._process_trades_from_conversion(trade_pairs)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_1INCH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('6000.0'),
        rate=FVal('0.00000282360833333333333333333333333333333333333333333333333333333333333333333333333'),
        fee=FVal('540'),
        fee_currency=A_1INCH,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trades == [expected_trade]


def test_asset_conversion_zero_fee(mock_coinbase):
    """Test a conversion with 0 fee"""
    tx_id = '77c5ad72-764e-414b-8bdb-b5aed20fb4b1'
    trade_a = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-6000.000000',
            'currency': '1INCH',
        },
        'native_amount': {
            'amount': '-1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2021-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted from USD Coin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 1,000.0000 USDC ($1,000.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }
    trade_b = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '0.01694165',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '1000.00',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2020-06-08T02:32:16Z',
        'updated_at': '2020-06-08T02:32:16Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': '5dceef97-ef34-41e6-9171-3e60cd01639e',
            'resource': 'trade',
            'resource_path': '/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e',
        },
        'details': {
            'title': 'Converted to Bitcoin',
            'subtitle': 'Using USDC Wallet',
            'header': 'Converted 0.01694165 BTC ($910.00)',
            'health': 'positive',
            'payment_method_name': 'USDC Wallet',
        },
    }

    trade_pairs = {tx_id: [trade_a, trade_b]}
    trades = mock_coinbase._process_trades_from_conversion(trade_pairs)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_1INCH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('6000.0'),
        rate=FVal('0.00000282360833333333333333333333333333333333333333333333333333333333333333333333333'),
        fee=FVal(ZERO),
        fee_currency=A_1INCH,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trades == [expected_trade]


def test_asset_conversion_choosing_fee_asset(mock_coinbase):
    """Test that the fee asset is correctly chosen when the received asset transaction
    is created before the giving transaction.
    """
    tx_id = '77c5ad72-764e-414b-8bdb-b5aed20fb4b1'
    trade_a = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '-37734.034561',
            'currency': 'ETH',
        },
        'native_amount': {
            'amount': '-79362.22',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2021-10-12T13:23:56Z',
        'updated_at': '2021-10-12T13:23:56Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': 'id_of_trade',
            'resource': 'trade',
            'resource_path': '/v2/accounts/REDACTED/trades/id_of_trade',
        },
        'details': {
            'title': 'Converted from ETH',
            'subtitle': 'Using ETH Wallet',
            'header': 'Converted 37,734.034561 ETH ($79,362.22)',
            'health': 'positive',
            'payment_method_name': 'ETH Wallet',
        },
        'hide_native_amount': False,
    }
    trade_b = {
        'id': tx_id,
        'type': 'trade',
        'status': 'completed',
        'amount': {
            'amount': '552.315885836',
            'currency': 'BTC',
        },
        'native_amount': {
            'amount': '77827.94',
            'currency': 'USD',
        },
        'description': None,
        'created_at': '2021-10-12T13:23:55Z',
        'updated_at': '2021-10-12T13:23:57Z',
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/sd5af/transactions/{tx_id}',
        'instant_exchange': False,
        'trade': {
            'id': 'id_of_trade',
            'resource': 'trade',
            'resource_path': '/v2/accounts/REDACTED/trades/id_of_trade',
        },
        'details': {
            'title': 'Converted to BTC',
            'subtitle': 'Using ETH Wallet',
            'header': 'Converted 552.31588584 BTC ($77,827.94)',
            'health': 'positive',
            'payment_method_name': 'ETH Wallet',
        },
        'hide_native_amount': False,
    }

    trade_pairs = {tx_id: [trade_a, trade_b]}
    trades = mock_coinbase._process_trades_from_conversion(trade_pairs)
    expected_trade = Trade(
        timestamp=1634045036,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('37734.034561'),
        rate=FVal('0.0146370747857120456618961647110471039778724604004318678293903627614266338669133'),
        fee=FVal('10.8882133758192505159458158599598036386418553542596656162298526724464247672494'),
        fee_currency=A_BTC,
        link='id_of_trade',
    )
    assert trades == [expected_trade]


def test_coinbase_query_trade_history_advanced_fill(function_scope_coinbase):
    """Test that coinbase trade history query works fine for advanced_trade_fill"""
    coinbase = function_scope_coinbase
    mock_transactions_response = """
{ "data": [{
            "id": "id1",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "-192.790000",
                "currency": "USDC"
            },
            "native_amount": {
                "amount": "-176.94",
                "currency": "EUR"
            },
            "description": null,
            "created_at": "2024-03-07T08:12:51Z",
            "updated_at": "2024-03-07T08:12:51Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id1",
            "instant_exchange": false,
            "advanced_trade_fill": {
                "fill_price": "0.9174",
                "product_id": "USDC-EUR",
                "order_id": "orderid1",
                "commission": "0",
                "order_side": "sell"
            },
            "details": {
                "title": "Filled USDC on sell",
                "subtitle": null,
                "header": null,
                "health": "positive"
            },
            "hide_native_amount": false
        },
        {
            "id": "id2",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "-485.330000",
                "currency": "USDC"
            },
            "native_amount": {
                "amount": "-445.44",
                "currency": "EUR"
            },
            "description": null,
            "created_at": "2024-03-07T09:12:51Z",
            "updated_at": "2024-03-07T09:12:51Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id2",
            "instant_exchange": false,
            "advanced_trade_fill": {
                "fill_price": "0.9174",
                "product_id": "USDC-EUR",
                "order_id": "orderid2",
                "commission": "0",
                "order_side": "sell"
            },
            "details": {
                "title": "Filled USDC on sell",
                "subtitle": null,
                "header": null,
                "health": "positive"
            },
            "hide_native_amount": false
        },
        {
            "id": "id3",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "-1.120000",
                "currency": "ETH"
            },
            "native_amount": {
                "amount": "-3400.98",
                "currency": "EUR"
            },
            "description": null,
            "created_at": "2024-03-07T09:12:51Z",
            "updated_at": "2024-03-07T09:12:51Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id3",
            "instant_exchange": false,
            "advanced_trade_fill": {
                "fill_price": "3334.341",
                "product_id": "ETH-USDC",
                "order_id": "orderid3",
                "commission": "0.0000005",
                "order_side": "sell"
            },
            "details": {
                "title": "Filled ETH on sell",
                "subtitle": null,
                "header": null,
                "health": "positive"
            },
            "hide_native_amount": false
        },
        {
            "id": "id4",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "0.589290",
                "currency": "SOL"
            },
            "native_amount": {
                "amount": "80.08",
                "currency": "EUR"
            },
            "description": null,
            "created_at": "2024-03-07T09:12:51Z",
            "updated_at": "2024-03-07T09:12:51Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id4",
            "instant_exchange": false,
            "advanced_trade_fill": {
                "fill_price": "170.12",
                "product_id": "SOL-USDC",
                "order_id": "orderid4",
                "commission": "0.5710371002622",
                "order_side": "buy"
            },
            "details": {
                "title": "Filled Solana on buy",
                "subtitle": null,
                "header": null,
                "health": "positive"
            },
            "hide_native_amount": false
        },
        {
            "id": "id5",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "25.8100000000000000",
                "currency": "NEAR"
            },
            "native_amount": {
                "amount": "191.12",
                "currency": "USD"
            },
            "created_at": "2024-03-25T13:03:11Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id6",
            "advanced_trade_fill": {
                "fill_price": "7.409",
                "product_id": "NEAR-USD",
                "order_id": "orderid6",
                "commission": "1.9122629",
                "order_side": "buy"
            }
        },
        {
            "id": "id6",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "2.0000000000000000",
                "currency": "NEAR"
            },
            "native_amount": {
                "amount": "14.81",
                "currency": "USD"
            },
            "created_at": "2024-03-25T13:03:11Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id7",
            "advanced_trade_fill": {
                "fill_price": "7.408",
                "product_id": "NEAR-USD",
                "order_id": "orderid6",
                "commission": "0.14816",
                "order_side": "buy"
            }
        },
        {
            "id": "id7",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "-191.22",
                "currency": "USD"
            },
            "native_amount": {
                "amount": "-191.23",
                "currency": "USD"
            },
            "created_at": "2024-03-25T13:03:11Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id6",
            "advanced_trade_fill": {
                "fill_price": "7.409",
                "product_id": "NEAR-USD",
                "order_id": "orderid6",
                "commission": "1.9122629",
                "order_side": "buy"
            }
        },
        {
            "id": "id8",
            "type": "advanced_trade_fill",
            "status": "completed",
            "amount": {
                "amount": "-14.81",
                "currency": "USD"
            },
            "native_amount": {
                "amount": "-14.82",
                "currency": "USD"
            },
            "created_at": "2024-03-25T13:03:11Z",
            "resource": "transaction",
            "resource_path": "/v2/accounts/REDACTED/transactions/id7",
            "advanced_trade_fill": {
                "fill_price": "7.408",
                "product_id": "NEAR-USD",
                "order_id": "orderid6",
                "commission": "0.14816",
                "order_side": "buy"
            }
        }]
}
"""
    mock_coinbase_query = _create_coinbase_mock(mock_transactions_response)

    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=ts_now(),
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    # Notice that there are more trades included in the mock data
    # but we expect some of them to not be included in the output
    expected_trades = [Trade(
        timestamp=1709799171,
        location=Location.COINBASE,
        base_asset=A_USDC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=FVal('192.790000'),
        rate=FVal('0.9174'),
        fee=ZERO,
        fee_currency=A_EUR,
        link='id1',
    ), Trade(
        timestamp=1709802771,
        location=Location.COINBASE,
        base_asset=A_USDC,
        quote_asset=A_EUR,
        trade_type=TradeType.SELL,
        amount=FVal('485.330000'),
        rate=FVal('0.9174'),
        fee=ZERO,
        fee_currency=A_EUR,
        link='id2',
    ), Trade(
        timestamp=1709802771,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_USDC,
        trade_type=TradeType.SELL,
        amount=FVal('1.120000'),
        rate=FVal('3334.341'),
        fee=FVal('0.0000005'),
        fee_currency=A_USDC,
        link='id3',
    ), Trade(
        timestamp=1709802771,
        location=Location.COINBASE,
        base_asset=A_SOL,
        quote_asset=A_USDC,
        trade_type=TradeType.BUY,
        amount=FVal('0.589290'),
        rate=FVal('170.12'),
        fee=FVal('0.5710371002622'),
        fee_currency=A_USDC,
        link='id4',
    ), Trade(
        timestamp=1711371791,
        location=Location.COINBASE,
        base_asset=Asset('NEAR'),
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal('25.8100000000000000'),
        rate=FVal('7.409'),
        fee=FVal('1.9122629'),
        fee_currency=A_USD,
        link='id5',
    ), Trade(
        timestamp=1711371791,
        location=Location.COINBASE,
        base_asset=Asset('NEAR'),
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal('2.0000000000000000'),
        rate=FVal('7.408'),
        fee=FVal('0.14816'),
        fee_currency=A_USD,
        link='id6',
    )]
    assert trades == expected_trades


def test_advancedtrade_missing_order_side(mock_coinbase):
    """Test that we can read coinbase advanced trades missing order_side """
    tx_id1 = '77c5ad72-764e-414b-8bdb-b5aed20fb4b1'
    raw_trade_a = {
        'advanced_trade_fill': {
            'commission': '0.85',
            'fill_price': '1946.02',
            'order_id': '0e2ae3da-3sdf-45cf-a1f0-60a6bd77a987',
            'product_id': 'ETH-USD',
        },
        'amount': {
            'amount': '-205.5',
            'currency': 'USD',
        },
        'created_at': '2022-05-20T19:38:04Z',
        'id': tx_id1,
        'native_amount': {
            'amount': '-205.5',
            'currency': 'USD',
        },
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/883b6405-4099-5eec-9e33-b0f257f23bdd/transactions/{tx_id1}',  # noqa: E501
        'status': 'completed',
        'type': 'advanced_trade_fill',
    }
    trade = mock_coinbase._process_coinbase_trade(raw_trade_a)
    expected_trade = Trade(
        timestamp=1653075484,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal('0.105600147994367992106967040420961757844215372914975180111201323727402596067872'),
        rate=FVal('1946.02'),
        fee=FVal('0.85'),
        fee_currency=A_USD,
        link=tx_id1,
    )
    assert trade == expected_trade
    tx_id2 = '66c5ad72-764e-2f4b-8bdb-b5aed20fb389'
    raw_trade_b = {
        'advanced_trade_fill': {
            'commission': '0.0047',
            'fill_price': '1870.16',
            'order_id': '9bc52036-9b18-1dea-756c-c960fd3d18a1',
            'product_id': 'ETH-USD',
        },
        'amount': {
            'amount': '0.00100000',
            'currency': 'ETH',
        },
        'created_at': '2022-05-26T18:05:30Z',
        'id': tx_id2,
        'native_amount': {
            'amount': '1.87',
            'currency': 'USD',
        },
        'resource': 'transaction',
        'resource_path': f'/v2/accounts/b7a7a05a-58ed-5a74-a328-266530609c9f/transactions/{tx_id2}',  # noqa: E501
        'status': 'completed',
        'type': 'advanced_trade_fill',
    }
    trade = mock_coinbase._process_coinbase_trade(raw_trade_b)
    expected_trade = Trade(
        timestamp=1653588330,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal('0.001'),
        rate=FVal('1870.16'),
        fee=FVal('0.0047'),
        fee_currency=A_USD,
        link=tx_id2,
    )
    assert trade == expected_trade


def test_coverage_of_products():
    """Test that we can process all assets from coinbase"""
    data = requests.get('https://api.exchange.coinbase.com/currencies')
    for coin in data.json():
        try:  # Make sure all products can be processed
            asset_from_coinbase(coin['id'])
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.identifier} with symbol {coin["id"]} in Coinbase. '
                f'Support for it has to be added',
            ))
