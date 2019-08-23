from unittest.mock import patch

from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USD
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import TradeType


def test_coinbase_query_balances(function_scope_coinbase):
    """Test that coinbase balance query works fine for the happy path"""
    coinbase = function_scope_coinbase

    def mock_coinbase_accounts(url):  # pylint: disable=unused-argument
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
    assert balances[A_BTC]['amount'] == FVal('5.23')
    assert balances[A_ETH]['amount'] == FVal('39.59')
    assert 'usd_value' in balances[A_ETH]
    assert 'usd_value' in balances[A_BTC]

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

    def query_coinbase_and_test(
            response_str,
            expected_warnings_num,
            expected_errors_num,
            contains_expected_msg=None,
    ):
        def mock_coinbase_accounts(url):  # pylint: disable=unused-argument
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
            assert balances[A_BTC]['amount'] == FVal('4')
            assert 'usd_value' in balances[A_BTC]
        else:
            assert len(warnings) == expected_warnings_num
            assert len(errors) == expected_errors_num
            assert msg == ''
            assert len(balances) == 0

    # test that all is fine with normal data
    query_coinbase_and_test(data, expected_warnings_num=0, expected_errors_num=0)

    # From now on unexpected data
    # no data key
    query_coinbase_and_test(
        '{"foo": 1}',
        expected_warnings_num=0,
        expected_errors_num=0,
        contains_expected_msg='Coinbase json response does not contain data',
    )
    # account entry without "balance" key
    input_data = data.replace('"balance"', '"foo"')
    query_coinbase_and_test(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry without amount in "balance"
    input_data = data.replace('"amount"', '"foo"')
    query_coinbase_and_test(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry without currency in "balance"
    input_data = data.replace('"currency"', '"foo"')
    query_coinbase_and_test(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry with invalid balance amount
    input_data = data.replace('"4.00000000"', '"csadasdsd"')
    query_coinbase_and_test(input_data, expected_warnings_num=0, expected_errors_num=1)
    # account entry with unknown asset
    input_data = data.replace('"BTC"', '"DDSADSAD"')
    query_coinbase_and_test(input_data, expected_warnings_num=1, expected_errors_num=0)
    # account entry with invalid asset
    input_data = data.replace('"BTC"', 'null')
    query_coinbase_and_test(input_data, expected_warnings_num=0, expected_errors_num=1)


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
  "status": "created",
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
  "id": "9e14d574-30fa-5d85-b02c-6be0d851d61d",
  "status": "created",
  "payment_method": {
    "id": "83562370-3e5c-51db-87da-752af5ab9559",
    "resource": "payment_method",
    "resource_path": "/v2/payment-methods/83562370-3e5c-51db-87da-752af5ab9559"
  },
  "transaction": {
    "id": "4117f7d6-5694-5b36-bc8f-847509850ea4",
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


def test_coinbase_query_trade_history(function_scope_coinbase):
    """Test that coinbase trade history query works fine for the happy path"""
    coinbase = function_scope_coinbase

    def mock_coinbase_query(url):  # pylint: disable=unused-argument
        if 'buys' in url:
            return MockResponse(200, BUYS_RESPONSE)
        elif 'sells' in url:
            return MockResponse(200, SELLS_RESPONSE)
        elif 'accounts' in url:
            # keep it simple just return a single ID and ignore the rest of the fields
            return MockResponse(200, '{"data": [{"id": "5fs23"}]}')
        else:
            raise AssertionError(f'Unexpected url {url} for test')

    with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_query):
        trades = coinbase.query_trade_history(
            start_ts=0,
            end_ts=TEST_END_TS,
            end_at_least_ts=TEST_END_TS,
        )

    warnings = coinbase.msg_aggregator.consume_warnings()
    errors = coinbase.msg_aggregator.consume_errors()
    assert len(warnings) == 0
    assert len(errors) == 0
    assert len(trades) == 2
    expected_trades = [Trade(
        timestamp=1500853448,
        location='coinbase',
        pair='BTC_USD',
        trade_type=TradeType.BUY,
        amount=FVal("486.34313725"),
        rate=FVal("0.1000000282208235751311317321"),
        fee=FVal("1.01"),
        fee_currency=A_USD,
    ), Trade(
        timestamp=1427402520,
        location='coinbase',
        pair='ETH_USD',
        trade_type=TradeType.SELL,
        amount=FVal("100.45"),
        rate=FVal("0.01123586708008393623351811833"),
        fee=FVal("10.1"),
        fee_currency=A_USD,
    )]
    assert trades == expected_trades


def test_coinbase_query_trade_history_unexpected_data(function_scope_coinbase):
    """Test that coinbase trade history query handles unexpected data properly"""
    coinbase = function_scope_coinbase
    coinbase.cache_ttl_secs = 0

    def query_coinbase_and_test(
            buys_response=BUYS_RESPONSE,
            sells_response=SELLS_RESPONSE,
            expected_warnings_num=0,
            expected_errors_num=0,
            # Since this test only mocks as breaking only either buys or sells by default
            expected_trades_num=1,
    ):
        def mock_coinbase_query(url):  # pylint: disable=unused-argument
            if 'buys' in url:
                return MockResponse(200, buys_response)
            elif 'sells' in url:
                return MockResponse(200, sells_response)
            elif 'accounts' in url:
                # keep it simple just return a single ID and ignore the rest of the fields
                return MockResponse(200, '{"data": [{"id": "5fs23"}]}')
            else:
                raise AssertionError(f'Unexpected url {url} for test')

        with patch.object(coinbase.session, 'get', side_effect=mock_coinbase_query):
            trades = coinbase.query_trade_history(
                start_ts=0,
                end_ts=TEST_END_TS,
                end_at_least_ts=TEST_END_TS,
            )

        errors = coinbase.msg_aggregator.consume_errors()
        warnings = coinbase.msg_aggregator.consume_warnings()
        if expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(trades) == 2
            assert len(errors) == 0
            assert len(warnings) == 0
        else:
            assert len(trades) == expected_trades_num
            assert len(errors) == expected_errors_num
            assert len(warnings) == expected_warnings_num

    # first query with proper data and expect no errors
    query_coinbase_and_test(expected_warnings_num=0, expected_errors_num=0)

    # invalid payout_at timestamp
    broken_response = BUYS_RESPONSE.replace('"2017-07-23T23:44:08Z"', 'true')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid created_at timestamp
    broken_response = SELLS_RESPONSE.replace('"2015-03-26T13:42:00-07:00"', '"dadssd"')
    query_coinbase_and_test(
        sells_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown asset
    broken_response = BUYS_RESPONSE.replace('"BTC"', '"dsadsad"')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid asset format
    broken_response = BUYS_RESPONSE.replace('"BTC"', '123')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid trade type
    broken_response = BUYS_RESPONSE.replace('"buy"', 'null')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid amount
    broken_response = BUYS_RESPONSE.replace('"486.34313725"', '"gfgfg"')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid total amount
    broken_response = BUYS_RESPONSE.replace('"4863.43"', 'false')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # invalid fee amount
    broken_response = BUYS_RESPONSE.replace('"1.01"', '"aas"')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )

    # unknown fee asset
    broken_response = BUYS_RESPONSE.replace('"USD"', '"DSADSA"')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=1,
        expected_errors_num=0,
    )

    # invalid fee asset
    broken_response = BUYS_RESPONSE.replace('"USD"', '[]')
    query_coinbase_and_test(
        buys_response=broken_response,
        expected_warnings_num=0,
        expected_errors_num=1,
    )
