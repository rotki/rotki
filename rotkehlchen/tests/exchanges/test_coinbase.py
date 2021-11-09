from unittest.mock import patch

from rotkehlchen.accounting.ledger_actions import LedgerAction, LedgerActionType
from rotkehlchen.assets.converters import asset_from_coinbase
from rotkehlchen.constants.assets import A_1INCH, A_BTC, A_ETH, A_USD, A_USDC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.coinbase import Coinbase, trade_from_conversion
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Location, TradeType


def test_name():
    exchange = Coinbase('coinbase1', 'a', b'a', object(), object())
    assert exchange.location == Location.COINBASE
    assert exchange.name == 'coinbase1'


def test_coinbase_query_balances(function_scope_coinbase):
    """Test that coinbase balance query works fine for the happy path"""
    coinbase = function_scope_coinbase

    def mock_coinbase_accounts(url, timeout):  # pylint: disable=unused-argument
        response = MockResponse(
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
        return response

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
            assert len(balances) == 1
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
        contains_expected_msg='Coinbase json response does not contain data',
    )
    # account entry without "balance" key
    input_data = data.replace('"balance"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry without amount in "balance"
    input_data = data.replace('"amount"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry without currency in "balance"
    input_data = data.replace('"currency"', '"foo"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry with invalid balance amount
    input_data = data.replace('"4.00000000"', '"csadasdsd"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry with unknown asset
    input_data = data.replace('"BTC"', '"DDSADSAD"')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=1, expected_errors_num=0)
    # account entry with invalid asset
    input_data = data.replace('"BTC"', 'null')
    query_coinbase_and_test_local_mock(input_data, expected_warnings_num=0, expected_errors_num=1)


BUYS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
  "id": "9e14d574-30fa-5d85-b02c-6be0d851d61d",
  "status": "completed",
  "payment_method": {
    "id": "83562370-3e5c-51db-87da-752af5ab9559",
    "resource": "payment_method",
    "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
  },
  "transaction": {
    "id": "4117f7d6-5694-5b36-bc8f-847509850ea4",
    "resource": "transaction",
    "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/441b9494"
  },
  "amount": {
    "amount": "486.34313725",
    "currency": "BTC"
  },
  "total": {
    "amount": "4863.43",
    "currency": "USD"
  },
  "subtotal": {
    "amount": "4862.42",
    "currency": "USD"
  },
  "created_at": "2017-07-21T23:43:59-07:00",
  "updated_at": "2017-07-21T23:43:59-07:00",
  "resource": "buy",
  "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/buys/9e14d574",
  "committed": true,
  "instant": false,
  "fee": {
    "amount": "1.01",
    "currency": "USD"
  },
  "payout_at": "2017-07-23T23:44:08Z"
}]}"""


SELLS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
  "id": "1e14d574-30fa-5d85-b02c-6be0d851d61d",
  "status": "completed",
  "payment_method": {
    "id": "23562370-3e5c-51db-87da-752af5ab9559",
    "resource": "payment_method",
    "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
  },
  "transaction": {
    "id": "3117f7d6-5694-5b36-bc8f-847509850ea4",
    "resource": "transaction",
    "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/4117f7d6"
  },
  "amount": {
    "amount": "100.45",
    "currency": "ETH"
  },
  "total": {
    "amount": "8940.12",
    "currency": "USD"
  },
  "subtotal": {
    "amount": "8930.02",
    "currency": "USD"
  },
  "created_at": "2015-03-26T13:42:00-07:00",
  "updated_at": "2015-03-26T13:42:00-07:00",
  "resource": "sell",
  "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/sells/9e14d574",
  "committed": true,
  "instant": true,
  "fee": {
    "amount": "10.1",
    "currency": "USD"
  },
  "payout_at": "2015-04-01T23:43:59-07:00"
}]}"""

DEPOSITS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
      "id": "1130eaec-07d7-54c4-a72c-2e92826897df",
      "status": "completed",
      "payment_method": {
        "id": "83562370-3e5c-51db-87da-752af5ab9559",
        "resource": "payment_method",
        "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
      },
      "transaction": {
        "id": "441b9494-b3f0-5b98-b9b0-4d82c21c252a",
        "resource": "transaction",
        "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/441b9494"
      },
      "amount": {
        "amount": "55.00",
        "currency": "USD"
      },
      "subtotal": {
        "amount": "54.95",
        "currency": "USD"
      },
      "created_at": "2015-01-31T20:49:02Z",
      "updated_at": "2015-02-11T16:54:02-08:00",
      "resource": "deposit",
      "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/deposits/67e0eaec",
      "committed": true,
      "fee": {
        "amount": "0.05",
        "currency": "USD"
      },
      "payout_at": "2018-02-18T16:54:00-08:00"
}]}"""


WITHDRAWALS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
      "id": "146eaec-07d7-54c4-a72c-2e92826897df",
      "status": "completed",
      "payment_method": {
        "id": "85562970-3e5c-51db-87da-752af5ab9559",
        "resource": "payment_method",
        "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
      },
      "transaction": {
        "id": "441b9454-b3f0-5b98-b9b0-4d82c21c252a",
        "resource": "transaction",
        "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/transactions/441b9494"
      },
      "amount": {
        "amount": "10.00",
        "currency": "USD"
      },
      "subtotal": {
        "amount": "9.99",
        "currency": "USD"
      },
      "created_at": "2017-01-31T20:49:02Z",
      "updated_at": "2017-01-31T20:49:02Z",
      "resource": "withdrawal",
      "resource_path": "/v2/accounts/2bbf394c-193b-5b2a-9155-3b4732659ede/withdrawals/67e0eaec",
      "committed": true,
      "fee": {
        "amount": "0.01",
        "currency": "USD"
      },
      "payout_at": null
}]}"""

TRANSACTIONS_RESPONSE = """{
"pagination": {
    "ending_before": null,
    "starting_after": null,
    "limit": 25,
    "order": "desc",
    "previous_uri": null,
    "next_uri": null
},
"data": [{
  "id": "id1",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "-0.05770427",
    "currency": "ETH"
  },
  "native_amount": {
    "amount": "-9.83",
    "currency": "EUR"
  },
  "description": null,
  "created_at": "2019-08-25T09:42:06Z",
  "updated_at": "2019-08-25T09:43:42Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/foo/transactions/boo",
  "instant_exchange": false,
  "network": {
    "status": "confirmed",
    "hash": "0x558bfa4d2a4ef598ddb92233459c00eda9e6c14cda75e6773b90208cb6938169",
    "transaction_url": "https://etherscan.io/tx/bbb",
    "transaction_fee": {"amount": "0.00021", "currency": "ETH"},
    "transaction_amount": {"amount": "0.05749427", "currency": "ETH"},
    "confirmations": 86
   },
    "to": {
      "resource": "ethereum_address",
      "address": "0x6dcd6449dbca615e40d696328209686ea95327b2",
      "currency": "ETH",
      "address_info": {"address": "0xboo"}
    },
    "idem": "zzzz",
    "details": {"title": "Sent Ethereum", "subtitle": "To Ethereum address"}
},{
  "id": "id2",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "-0.05770427",
    "currency": "ETH"
  },
  "native_amount": {
    "amount": "-9.83",
    "currency": "EUR"
  },
  "description": null,
  "created_at": "2019-08-25T09:42:06Z",
  "updated_at": "2019-08-25T09:43:42Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/foo/transactions/coo",
  "instant_exchange": false,
    "to": {
      "resource": "ethereum_address",
      "address": "0x6dcd6449dbca615e40d696328209686ea95327b2",
      "currency": "ETH",
      "address_info": {"address": "0xboo"}
    },
    "idem": "zzzz",
    "details": {"title": "Sent Ethereum", "subtitle": "To Ethereum address"}
}, {
  "id": "id3",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "0.10181673",
    "currency": "BTC"
  },
  "native_amount": {
    "amount": "410.24",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2017-08-12T16:11:44Z",
  "updated_at": "2017-08-12T16:21:41Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/boo",
  "instant_exchange": false,
  "network": {
    "status": "confirmed",
    "status_description": null,
    "hash": "ccc",
    "transaction_url":
    "https://blockchain.info/tx/ccc"
  },
  "from": {
    "resource": "bitcoin_network",
    "currency": "BTC"
  },
  "details": {
    "title": "Received Bitcoin",
    "subtitle": "From Bitcoin address",
    "header": "Received 0.10181673 BTC ($410.24)",
    "health": "positive"
  },
  "hide_native_amount": false

},{
  "id": "id4",
  "type": "send",
  "status": "completed",
  "amount": {
    "amount": "0.02762431",
    "currency": "NMR"
  },
  "native_amount": {
    "amount": "1.01",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2021-01-05T20:11:54Z",
  "updated_at": "2021-01-05T20:11:54Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/boo",
  "instant_exchange": false,
  "off_chain_status": "completed",
  "network": {"status": "off_blockchain", "status_description": null},
  "from": {
    "id": "idc",
    "resource": "user",
    "resource_path": "/v2/users/idc",
    "currency": "NMR"
  },
  "details": {
    "title": "Received Numeraire",
    "subtitle": "From Coinbase Earn",
    "header": "Received 0.02762431 NMR ($1.01)",
    "health": "positive"
  },
  "hide_native_amount": false
},{
  "id": "id5",
  "type": "inflation_reward",
  "status": "completed",
  "amount": {
    "amount": "0.000076",
    "currency": "ALGO"
  },
  "native_amount": {
    "amount": "0.00",
    "currency": "USD"
  },
  "description": null,
  "created_at": "2021-01-23T18:23:53Z",
  "updated_at": "2021-01-23T18:23:53Z",
  "resource": "transaction",
  "resource_path": "/v2/accounts/boo",
  "instant_exchange": false,
  "from": {
    "id": "idc",
    "resource": "user",
    "resource_path": "/v2/users/idd",
    "currency": "ALGO"
  },
  "details": {
    "title": "Algorand reward",
    "subtitle": "From Coinbase",
    "header": "Received 0.000076 ALGO ($0.00)",
    "health": "positive"
  },
  "hide_native_amount": false
}]}"""


def mock_normal_coinbase_query(url, **kwargs):  # pylint: disable=unused-argument
    if 'buys' in url:
        return MockResponse(200, BUYS_RESPONSE)
    if 'sells' in url:
        return MockResponse(200, SELLS_RESPONSE)
    if 'deposits' in url:
        return MockResponse(200, DEPOSITS_RESPONSE)
    if 'withdrawals' in url:
        return MockResponse(200, WITHDRAWALS_RESPONSE)
    if 'transactions' in url:
        return MockResponse(200, TRANSACTIONS_RESPONSE)
    if 'accounts' in url:
        # keep it simple just return a single ID and ignore the rest of the fields
        return MockResponse(200, '{"data": [{"id": "5fs23"}]}')
    # else
    raise AssertionError(f'Unexpected url {url} for test')


def test_coinbase_query_trade_history(function_scope_coinbase):
    """Test that coinbase trade history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=TEST_END_TS,
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 2
    expected_trades = [Trade(
        timestamp=1500705839,
        location=Location.COINBASE,
        base_asset=A_BTC,
        quote_asset=A_USD,
        trade_type=TradeType.BUY,
        amount=FVal("486.34313725"),
        rate=FVal("9.997920454875299055122012005"),
        fee=FVal("1.01"),
        fee_currency=A_USD,
        link='9e14d574-30fa-5d85-b02c-6be0d851d61d',
    ), Trade(
        timestamp=1427402520,
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_USD,
        trade_type=TradeType.SELL,
        amount=FVal("100.45"),
        rate=FVal("88.90014932802389248382279741"),
        fee=FVal("10.1"),
        fee_currency=A_USD,
        link='1e14d574-30fa-5d85-b02c-6be0d851d61d',
    )]
    assert trades == expected_trades

    # and now try only a smaller time range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=1451606400,
            only_cache=False,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 1
    assert trades[0].trade_type == TradeType.SELL
    assert trades[0].timestamp == 1427402520


def query_coinbase_and_test(
        coinbase,
        query_fn_name,
        buys_response=BUYS_RESPONSE,
        buys_paginated_end=BUYS_RESPONSE,
        sells_response=SELLS_RESPONSE,
        sells_paginated_end=SELLS_RESPONSE,
        deposits_response=DEPOSITS_RESPONSE,
        withdrawals_response=WITHDRAWALS_RESPONSE,
        expected_warnings_num=0,
        expected_errors_num=0,
        # Since this test only mocks as breaking only one of the two actions by default
        expected_actions_num=1,
):
    def mock_coinbase_query(url, **kwargs):  # pylint: disable=unused-argument
        if 'buys' in url:
            if 'next-page' in url:
                return MockResponse(200, buys_paginated_end)
            # else
            return MockResponse(200, buys_response)
        if 'sells' in url:
            if 'next-page' in url:
                return MockResponse(200, sells_paginated_end)
            # else
            return MockResponse(200, sells_response)
        if 'deposits' in url:
            return MockResponse(200, deposits_response)
        if 'withdrawals' in url:
            return MockResponse(200, withdrawals_response)
        if 'accounts' in url:
            # keep it simple just return a single ID and ignore the rest of the fields
            return MockResponse(200, '{"data": [{"id": "5fs23"}]}')
        # else
        raise AssertionError(f'Unexpected url {url} for test')

    query_fn = getattr(coinbase, query_fn_name)
    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_query):
        if query_fn_name == 'query_online_trade_history':
            actions, _ = query_fn(
                start_ts=0,
                end_ts=TEST_END_TS,
            )
        else:
            actions = query_fn(
                start_ts=0,
                end_ts=TEST_END_TS,
            )

    errors = coinbase.msg_aggregator.consume_errors()
    warnings = coinbase.msg_aggregator.consume_warnings()
    if expected_errors_num == 0 and expected_warnings_num == 0 and expected_actions_num == 1:
        assert len(actions) == 2
        assert len(errors) == 0
        assert len(warnings) == 0
    else:
        assert len(actions) == expected_actions_num
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num


def test_coinbase_query_trade_history_unexpected_data(function_scope_coinbase):
    """Test that coinbase trade history query handles unexpected data properly"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    # first query with proper data and expect no errors
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=0,
    )

    # fallback to payout_at if created_date is missing
    broken_response = BUYS_RESPONSE.replace('"created_at": "2017-07-21T23:43:59-07:00",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=0,
    )

    # invalid created_at timestamp
    broken_response = SELLS_RESPONSE.replace('"2015-03-26T13:42:00-07:00"', '"dadssd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        sells_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown asset
    broken_response = BUYS_RESPONSE.replace('"BTC"', '"dsadsad"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid asset format
    broken_response = BUYS_RESPONSE.replace('"BTC"', '123')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid trade type
    broken_response = BUYS_RESPONSE.replace('"buy"', 'null')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid amount
    broken_response = BUYS_RESPONSE.replace('"486.34313725"', '"gfgfg"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid subtotal amount
    broken_response = BUYS_RESPONSE.replace('"4862.42"', 'false')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid fee amount
    broken_response = BUYS_RESPONSE.replace('"1.01"', '"aas"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown fee asset
    broken_response = BUYS_RESPONSE.replace('"USD"', '"DSADSA"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid fee asset
    broken_response = BUYS_RESPONSE.replace('"USD"', '[]')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # missing key error
    broken_response = SELLS_RESPONSE.replace('  "status": "completed",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )


def test_coinbase_query_trade_history_paginated(function_scope_coinbase):
    """Test that coinbase trade history query can deal with paginated response"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    paginated_buys_response = BUYS_RESPONSE.replace(
        '"next_uri": null',
        '"next_uri": "/v2/buys/?next-page"',
    )

    paginated_sells_response = SELLS_RESPONSE.replace(
        '"next_uri": null',
        '"next_uri": "/v2/sells/?next-page"',
    )

    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_trade_history',
        expected_warnings_num=0,
        expected_errors_num=0,
        expected_actions_num=4,
        buys_response=paginated_buys_response,
        sells_response=paginated_sells_response,
    )


def test_coinbase_query_deposit_withdrawals(function_scope_coinbase):
    """Test that coinbase deposit/withdrawals history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        movements = coinbase.query_online_deposits_withdrawals(
            start_ts=0,
            end_ts=1566726126,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(movements) == 5
    expected_movements = [AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.DEPOSIT,
        timestamp=1519001640,
        address=None,
        transaction_id=None,
        asset=A_USD,
        amount=FVal('55.00'),
        fee_asset=A_USD,
        fee=FVal('0.05'),
        link='1130eaec-07d7-54c4-a72c-2e92826897df',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address=None,
        transaction_id=None,
        timestamp=1485895742,
        asset=A_USD,
        amount=FVal('10.00'),
        fee_asset=A_USD,
        fee=FVal('0.01'),
        link='146eaec-07d7-54c4-a72c-2e92826897df',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address='0x6dcD6449dbCa615e40d696328209686eA95327b2',
        transaction_id='0x558bfa4d2a4ef598ddb92233459c00eda9e6c14cda75e6773b90208cb6938169',
        timestamp=1566726126,
        asset=A_ETH,
        amount=FVal('0.05770427'),
        fee_asset=A_ETH,
        fee=FVal('0.00021'),
        link='https://etherscan.io/tx/bbb',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.WITHDRAWAL,
        address='0x6dcD6449dbCa615e40d696328209686eA95327b2',
        transaction_id=None,
        timestamp=1566726126,
        asset=A_ETH,
        amount=FVal('0.05770427'),
        fee_asset=A_ETH,
        fee=ZERO,
        link='id2',
    ), AssetMovement(
        location=Location.COINBASE,
        category=AssetMovementCategory.DEPOSIT,
        address=None,
        transaction_id='ccc',
        timestamp=1502554304,
        asset=A_BTC,
        amount=FVal('0.10181673'),
        fee_asset=A_BTC,
        fee=ZERO,
        link='https://blockchain.info/tx/ccc',
    )]
    assert expected_movements == movements

    # and now try to query within a specific range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        movements = coinbase.query_online_deposits_withdrawals(
            start_ts=0,
            end_ts=1519001640,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(movements) == 3
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1519001640
    assert movements[1].category == AssetMovementCategory.WITHDRAWAL
    assert movements[1].timestamp == 1485895742
    assert movements[2].category == AssetMovementCategory.DEPOSIT
    assert movements[2].timestamp == 1502554304


def test_coinbase_query_income_loss_expense(function_scope_coinbase):
    """Test that coinbase deposit/withdrawals history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        ledger_actions = coinbase.query_online_income_loss_expense(
            start_ts=0,
            end_ts=1611426233,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(ledger_actions) == 2
    expected_ledger_actions = [LedgerAction(
        identifier=ledger_actions[0].identifier,
        location=Location.COINBASE,
        action_type=LedgerActionType.INCOME,
        timestamp=1609877514,
        asset=asset_from_coinbase('NMR'),
        amount=FVal('0.02762431'),
        rate=FVal('36.56199919563601769600761069'),
        rate_asset=A_USD,
        link='id4',
        notes=('Received Numeraire '
               'From Coinbase Earn '
               'Received 0.02762431 NMR ($1.01)'),
    ), LedgerAction(
        identifier=ledger_actions[1].identifier,
        location=Location.COINBASE,
        action_type=LedgerActionType.INCOME,
        timestamp=1611426233,
        asset=asset_from_coinbase('ALGO'),
        amount=FVal('0.000076'),
        rate=ZERO,
        rate_asset=A_USD,
        link='id5',
        notes=('Algorand reward '
               'From Coinbase '
               'Received 0.000076 ALGO ($0.00)'),
    )]
    assert expected_ledger_actions == ledger_actions

    # and now try to query within a specific range
    with patch.object(coinbase.session, 'get', side_effect=mock_normal_coinbase_query):
        ledger_actions = coinbase.query_online_income_loss_expense(
            start_ts=0,
            end_ts=1609877514,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(ledger_actions) == 1
    assert ledger_actions[0].action_type == LedgerActionType.INCOME
    assert ledger_actions[0].timestamp == 1609877514


def test_coinbase_query_deposit_withdrawals_unexpected_data(function_scope_coinbase):
    """Test that coinbase deposit/withdrawals query handles unexpected data properly"""
    coinbase = function_scope_coinbase

    # first query with proper data and expect no errors
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        expected_warnings_num=0,
        expected_errors_num=0,
    )

    # invalid payout_at timestamp
    broken_response = DEPOSITS_RESPONSE.replace('"2018-02-18T16:54:00-08:00"', '"dadas"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        deposits_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid created_at timestamp
    broken_response = WITHDRAWALS_RESPONSE.replace('"2017-01-31T20:49:02Z"', '"dadssd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid asset movement type
    broken_response = WITHDRAWALS_RESPONSE.replace('"withdrawal"', 'null')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown asset
    broken_response = WITHDRAWALS_RESPONSE.replace('"USD"', '"dasdad"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid asset
    broken_response = WITHDRAWALS_RESPONSE.replace('"USD"', '{}')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid amount
    broken_response = WITHDRAWALS_RESPONSE.replace('"10.00"', 'true')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid fee
    broken_response = WITHDRAWALS_RESPONSE.replace('"0.01"', '"dasd"')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        withdrawals_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # missing key error
    broken_response = DEPOSITS_RESPONSE.replace('      "resource": "deposit",', '')
    query_coinbase_and_test(
        coinbase=coinbase,
        query_fn_name='query_online_deposits_withdrawals',
        deposits_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )


def test_asset_conversion():
    trade_b = {
        "id": "77c5ad72-764e-414b-8bdb-b5aed20fb4b1",
        "type": "trade",
        "status": "completed",
        "amount": {
            "amount": "-1000.000000",
            "currency": "USDC",
        },
        "native_amount": {
            "amount": "-1000.00",
            "currency": "USD",
        },
        "description": None,
        "created_at": "2020-06-08T02:32:16Z",
        "updated_at": "2021-06-08T02:32:16Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/sd5af/transactions/77c5ad72-764e-414b-8bdb-b5aed20fb4b1",
        "instant_exchange": False,
        "trade": {
            "id": "5dceef97-ef34-41e6-9171-3e60cd01639e",
            "resource": "trade",
            "resource_path": "/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e",
        },
        "details": {
            "title": "Converted from USD Coin",
            "subtitle": "Using USDC Wallet",
            "header": "Converted 1,000.0000 USDC ($1,000.00)",
            "health": "positive",
            "payment_method_name": "USDC Wallet",
        },
    }

    trade_a = {
        "id": "8f530cd1-5ec0-4aae-afdc-198502a53b17",
        "type": "trade",
        "status": "completed",
        "amount": {
            "amount": "0.01694165",
            "currency": "BTC",
        },
        "native_amount": {
            "amount": "910.00",
            "currency": "USD",
        },
        "description": None,
        "created_at": "2020-06-08T02:32:16Z",
        "updated_at": "2020-06-08T02:32:16Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/sd5af/transactions/8f530cd1-5ec0-4aae-afdc-198502a53b17",
        "instant_exchange": False,
        "trade": {
            "id": "5dceef97-ef34-41e6-9171-3e60cd01639e",
            "resource": "trade",
            "resource_path": "/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e",
        },
        "details": {
            "title": "Converted to Bitcoin",
            "subtitle": "Using USDC Wallet",
            "header": "Converted 0.01694165 BTC ($910.00)",
            "health": "positive",
            "payment_method_name": "USDC Wallet",
        },
    }

    trade = trade_from_conversion(trade_a, trade_b)
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
    assert trade == expected_trade


def test_asset_conversion_not_stable_coin():
    """Test a conversion using a from asset that is not a stable coin"""
    trade_a = {
        "id": "77c5ad72-764e-414b-8bdb-b5aed20fb4b1",
        "type": "trade",
        "status": "completed",
        "amount": {
            "amount": "-6000.000000",
            "currency": "1INCH",
        },
        "native_amount": {
            "amount": "-1000.00",
            "currency": "USD",
        },
        "description": None,
        "created_at": "2020-06-08T02:32:16Z",
        "updated_at": "2021-06-08T02:32:16Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/sd5af/transactions/77c5ad72-764e-414b-8bdb-b5aed20fb4b1",
        "instant_exchange": False,
        "trade": {
            "id": "5dceef97-ef34-41e6-9171-3e60cd01639e",
            "resource": "trade",
            "resource_path": "/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e",
        },
        "details": {
            "title": "Converted from USD Coin",
            "subtitle": "Using USDC Wallet",
            "header": "Converted 1,000.0000 USDC ($1,000.00)",
            "health": "positive",
            "payment_method_name": "USDC Wallet",
        },
    }

    trade_b = {
        "id": "8f530cd1-5ec0-4aae-afdc-198502a53b17",
        "type": "trade",
        "status": "completed",
        "amount": {
            "amount": "0.01694165",
            "currency": "BTC",
        },
        "native_amount": {
            "amount": "910.00",
            "currency": "USD",
        },
        "description": None,
        "created_at": "2020-06-08T02:32:16Z",
        "updated_at": "2020-06-08T02:32:16Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/sd5af/transactions/8f530cd1-5ec0-4aae-afdc-198502a53b17",
        "instant_exchange": False,
        "trade": {
            "id": "5dceef97-ef34-41e6-9171-3e60cd01639e",
            "resource": "trade",
            "resource_path": "/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e",
        },
        "details": {
            "title": "Converted to Bitcoin",
            "subtitle": "Using USDC Wallet",
            "header": "Converted 0.01694165 BTC ($910.00)",
            "health": "positive",
            "payment_method_name": "USDC Wallet",
        },
    }

    trade = trade_from_conversion(trade_a, trade_b)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_1INCH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('6000.0'),
        rate=FVal('0.000002823608333333333333333333333'),
        fee=FVal('540'),
        fee_currency=A_1INCH,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trade == expected_trade


def test_asset_conversion_zero_fee():
    """Test a conversion with 0 fee"""

    trade_a = {
        "id": "77c5ad72-764e-414b-8bdb-b5aed20fb4b1",
        "type": "trade",
        "status": "completed",
        "amount": {
            "amount": "-6000.000000",
            "currency": "1INCH",
        },
        "native_amount": {
            "amount": "-1000.00",
            "currency": "USD",
        },
        "description": None,
        "created_at": "2020-06-08T02:32:16Z",
        "updated_at": "2021-06-08T02:32:16Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/sd5af/transactions/77c5ad72-764e-414b-8bdb-b5aed20fb4b1",
        "instant_exchange": False,
        "trade": {
            "id": "5dceef97-ef34-41e6-9171-3e60cd01639e",
            "resource": "trade",
            "resource_path": "/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e",
        },
        "details": {
            "title": "Converted from USD Coin",
            "subtitle": "Using USDC Wallet",
            "header": "Converted 1,000.0000 USDC ($1,000.00)",
            "health": "positive",
            "payment_method_name": "USDC Wallet",
        },
    }

    trade_b = {
        "id": "8f530cd1-5ec0-4aae-afdc-198502a53b17",
        "type": "trade",
        "status": "completed",
        "amount": {
            "amount": "0.01694165",
            "currency": "BTC",
        },
        "native_amount": {
            "amount": "1000.00",
            "currency": "USD",
        },
        "description": None,
        "created_at": "2020-06-08T02:32:16Z",
        "updated_at": "2020-06-08T02:32:16Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/sd5af/transactions/8f530cd1-5ec0-4aae-afdc-198502a53b17",
        "instant_exchange": False,
        "trade": {
            "id": "5dceef97-ef34-41e6-9171-3e60cd01639e",
            "resource": "trade",
            "resource_path": "/v2/accounts/sd5af/trades/5dceef97-ef34-41e6-9171-3e60cd01639e",
        },
        "details": {
            "title": "Converted to Bitcoin",
            "subtitle": "Using USDC Wallet",
            "header": "Converted 0.01694165 BTC ($910.00)",
            "health": "positive",
            "payment_method_name": "USDC Wallet",
        },
    }

    trade = trade_from_conversion(trade_a, trade_b)
    expected_trade = Trade(
        timestamp=1623119536,
        location=Location.COINBASE,
        base_asset=A_1INCH,
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=FVal('6000.0'),
        rate=FVal('0.000002823608333333333333333333333'),
        fee=FVal(ZERO),
        fee_currency=A_1INCH,
        link='5dceef97-ef34-41e6-9171-3e60cd01639e',
    )
    assert trade == expected_trade
