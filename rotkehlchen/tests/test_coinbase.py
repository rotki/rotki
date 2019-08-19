from unittest.mock import patch

from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse


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
