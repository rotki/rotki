import warnings as test_warnings
from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_BITTREX_ASSETS, asset_from_bittrex
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import UnknownAsset, UnsupportedAsset
from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import TEST_END_TS
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import AssetMovementCategory, Location, TradeType


def test_name():
    exchange = Bittrex('a', b'a', object(), object())
    assert exchange.name == 'bittrex'


def test_bittrex_assets_are_known(bittrex):
    currencies = bittrex.get_currencies()
    for bittrex_asset in currencies:
        symbol = bittrex_asset['Currency']
        try:
            _ = asset_from_bittrex(symbol)
        except UnsupportedAsset:
            assert symbol in UNSUPPORTED_BITTREX_ASSETS
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Found unknown asset {e.asset_name} in Bittrex. Support for it has to be added',
            ))


def test_bittrex_query_balances_unknown_asset(bittrex):
    def mock_unknown_asset_return(url):  # pylint: disable=unused-argument
        response = MockResponse(
            200,
            """
{
  "success": true,
  "message": "''",
  "result": [
    {
      "Currency": "BTC",
      "Balance": "5.0",
      "Available": "5.0",
      "Pending": 0,
      "CryptoAddress": "DLxcEt3AatMyr2NTatzjsfHNoB9NT62HiF",
      "Requested": false,
      "Uuid": null
    },
    {
      "Currency": "ETH",
      "Balance": "10.0",
      "Available": "10.0",
      "Pending": 0,
      "CryptoAddress": "0xb55a183bf5db01665f9fc5dfba71fc6f8b5e42e6",
      "Requested": false,
      "Uuid": null
    },
    {
      "Currency": "IDONTEXIST",
      "Balance": "15.0",
      "Available": "15.0",
      "Pending": 0,
      "CryptoAddress": "0xb55a183bf5db01665f9fc5dfba71fc6f8b5e42e6",
      "Requested": false,
      "Uuid": null
    },
    {
      "Currency": "PTON",
      "Balance": "15.0",
      "Available": "15.0",
      "Pending": 0,
      "CryptoAddress": "0xb55a183bf5db01665f9fc5dfba71fc6f8b5e42e6",
      "Requested": false,
      "Uuid": null
    }
  ]
}
            """,
        )
        return response

    with patch.object(bittrex.session, 'get', side_effect=mock_unknown_asset_return):
        # Test that after querying the assets only ETH and BTC are there
        balances, msg = bittrex.query_balances()

    assert msg == ''
    assert len(balances) == 2
    assert balances[A_BTC]['amount'] == FVal('5.0')
    assert balances[A_ETH]['amount'] == FVal('10.0')

    warnings = bittrex.msg_aggregator.consume_warnings()
    assert len(warnings) == 2
    assert 'unknown bittrex asset IDONTEXIST' in warnings[0]
    assert 'unsupported bittrex asset PTON' in warnings[1]


BITTREX_ORDER_HISTORY_RESPONSE = """
{
  "success": true,
  "message": "''",
  "result": [
    {
      "OrderUuid": "fd97d393-e9b9-4dd1-9dbf-f288fc72a185",
      "Exchange": "BTC-LTC",
      "TimeStamp": "2014-02-13T00:00:00.00",
      "OrderType": "LIMIT_BUY",
      "Limit": 1e-8,
      "Quantity": 667.03644955,
      "QuantityRemaining": 0,
      "Commission": 0.00004921,
      "Price": 0.01968424,
      "PricePerUnit": 0.0000295,
      "IsConditional": false,
      "Condition": "",
      "ConditionTarget": 0,
      "ImmediateOrCancel": false,
      "Closed": "2014-02-13T00:00:00.00"
    }]}"""


def test_bittrex_query_trade_history(bittrex):
    """Test that turning a bittrex trade to our format works"""

    def mock_order_history(url):  # pylint: disable=unused-argument
        response = MockResponse(200, BITTREX_ORDER_HISTORY_RESPONSE)
        return response

    with patch.object(bittrex.session, 'get', side_effect=mock_order_history):
        trades = bittrex.query_trade_history(start_ts=0, end_ts=1564301134)

    expected_trade = Trade(
        timestamp=1392249600,
        location=Location.BITTREX,
        pair='LTC_BTC',
        trade_type=TradeType.BUY,
        amount=FVal('667.03644955'),
        rate=FVal('0.0000295'),
        fee=FVal('0.00004921'),
        fee_currency=A_BTC,
        link='fd97d393-e9b9-4dd1-9dbf-f288fc72a185',
    )

    assert len(trades) == 1
    assert trades[0] == expected_trade


def test_bittrex_query_trade_history_unexpected_data(bittrex):
    """Test that turning a bittrex trade that contains unexpected data is handled gracefully"""
    # turn caching off
    bittrex.cache_ttl_secs = 0

    def mock_order_history(url):  # pylint: disable=unused-argument
        response = MockResponse(200, BITTREX_ORDER_HISTORY_RESPONSE)
        return response

    def query_bittrex_and_test(
            input_trade_str,
            expected_warnings_num,
            expected_errors_num,
            warning_str_test=None,
            error_str_test=None,
    ):
        patch_get = patch.object(bittrex.session, 'get', side_effect=mock_order_history)
        patch_response = patch(
            'rotkehlchen.tests.test_bittrex.BITTREX_ORDER_HISTORY_RESPONSE',
            new=input_trade_str,
        )
        with patch_get, patch_response:
            # Test that after querying the assets only ETH and BTC are there
            trades = bittrex.query_online_trade_history(start_ts=0, end_ts=1564301134)

        assert len(trades) == 0
        errors = bittrex.msg_aggregator.consume_errors()
        warnings = bittrex.msg_aggregator.consume_warnings()
        assert len(errors) == expected_errors_num
        assert len(warnings) == expected_warnings_num
        if warning_str_test:
            assert warning_str_test in warnings[0]
        if error_str_test:
            assert error_str_test in errors[0]

    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"Quantity": 667.03644955',
        '"Quantity": "fdfdsf"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"QuantityRemaining": 0',
        '"QuantityRemaining": "dsa"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"TimeStamp": "2014-02-13T00:00:00.00"',
        '"TimeStamp": null',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"PricePerUnit": 0.0000295',
        '"PricePerUnit": "sdad"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"OrderType": "LIMIT_BUY"',
        '"OrderType": "dsadsd"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"Commission": 0.00004921',
        '"Commission": "dasdsad"',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    # Check that for non-string pairs we give a graceful error
    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"Exchange": "BTC-LTC"',
        '"Exchange": 4324234',
    )
    query_bittrex_and_test(input_str, expected_warnings_num=0, expected_errors_num=1)

    # Check that for unsupported assets in the pair are caught
    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"Exchange": "BTC-LTC"',
        '"Exchange": "BTC-PTON"',
    )
    query_bittrex_and_test(
        input_str,
        expected_warnings_num=1,
        expected_errors_num=0,
        warning_str_test='Found bittrex trade with unsupported asset PTON',
    )

    # Check that unprocessable pair is caught
    input_str = BITTREX_ORDER_HISTORY_RESPONSE.replace(
        '"Exchange": "BTC-LTC"',
        '"Exchange": "SSSS"',
    )
    query_bittrex_and_test(
        input_str,
        expected_warnings_num=0,
        expected_errors_num=1,
        error_str_test='Found bittrex trade with unprocessable pair SSSS',
    )


BITTREX_DEPOSIT_HISTORY_RESPONSE = """
{
  "success": true,
  "message": "''",
  "result": [
    {
      "Id": 1,
      "Amount": 2.12345678,
      "Currency": "BTC",
      "Confirmations": 2,
      "LastUpdated": "2014-02-13T07:38:53.883",
      "TxId": "e26d3b33fcfc2cb0c74d0938034956ea590339170bf4102f080eab4b85da9bde",
      "CryptoAddress": "15VyEAT4uf7ycrNWZVb1eGMzrs21BH95Va"
    }, {
      "Id": 2,
      "Amount": 50.81,
      "Currency": "ETH",
      "Confirmations": 5,
      "LastUpdated": "2015-06-15T07:38:53.883",
      "TxId": "e26d3b33fcfc2cb0cd4d0938034956ea590339170bf4102f080eab4s85da9bde",
      "CryptoAddress": "0x717E2De923A6377Fbd7e3c937491f71ad370e9A8"
    }
  ]
}
"""

BITTREX_WITHDRAWAL_HISTORY_RESPONSE = """
{
  "success": true,
  "message": "''",
  "result": [
    {
      "PaymentUuid": "b52c7a5c-90c6-4c6e-835c-e16df12708b1",
      "Currency": "BTC",
      "Amount": 17,
      "Address": "1DeaaFBdbB5nrHj87x3NHS4onvw1GPNyAu",
      "Opened": "2014-07-09T04:24:47.217",
      "Authorized": "boolean",
      "PendingPayment": "boolean",
      "TxCost": 0.0002,
      "TxId": "b4a575c2a71c7e56d02ab8e26bb1ef0a2f6cf2094f6ca2116476a569c1e84f6e",
      "Canceled": "boolean",
      "InvalidAddress": "boolean"
    }, {
      "PaymentUuid": "b52c7a5c-90c6-4c6e-835c-e16df12708b1",
      "Currency": "ETH",
      "Amount": 55,
      "Address": "0x717E2De923A6377Fbd7e3c937491f71ad370e9A8",
      "Opened": "2015-08-19T04:24:47.217",
      "Authorized": "boolean",
      "PendingPayment": "boolean",
      "TxCost": 0.0015,
      "TxId": "0xc65d3391739c96a04b868b205b34069f0bbd7ab7f62d1f59be02f29e77b59247",
      "Canceled": "boolean",
      "InvalidAddress": "boolean"
    }
  ]
}
"""


def test_bittrex_query_deposits_withdrawals(bittrex):
    """Test the happy case of bittrex deposit withdrawal query"""

    def mock_get_deposit_withdrawal(url):  # pylint: disable=unused-argument
        if 'deposit' in url:
            response_str = BITTREX_DEPOSIT_HISTORY_RESPONSE
        else:
            response_str = BITTREX_WITHDRAWAL_HISTORY_RESPONSE

        return MockResponse(200, response_str)

    with patch.object(bittrex.session, 'get', side_effect=mock_get_deposit_withdrawal):
        movements = bittrex.query_online_deposits_withdrawals(start_ts=0, end_ts=TEST_END_TS)

    errors = bittrex.msg_aggregator.consume_errors()
    warnings = bittrex.msg_aggregator.consume_warnings()
    assert len(errors) == 0
    assert len(warnings) == 0

    assert len(movements) == 4

    assert movements[0].location == Location.BITTREX
    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1392277133
    assert isinstance(movements[0].asset, Asset)
    assert movements[0].asset == A_BTC
    assert movements[0].amount == FVal('2.12345678')
    assert movements[0].fee == ZERO

    assert movements[1].location == Location.BITTREX
    assert movements[1].category == AssetMovementCategory.DEPOSIT
    assert movements[1].timestamp == 1434353933
    assert isinstance(movements[1].asset, Asset)
    assert movements[1].asset == A_ETH
    assert movements[1].amount == FVal('50.81')
    assert movements[1].fee == ZERO

    assert movements[2].location == Location.BITTREX
    assert movements[2].category == AssetMovementCategory.WITHDRAWAL
    assert movements[2].timestamp == 1404879887
    assert isinstance(movements[2].asset, Asset)
    assert movements[2].asset == A_BTC
    assert movements[2].amount == FVal('17')
    assert movements[2].fee == FVal('0.0002')

    assert movements[3].location == Location.BITTREX
    assert movements[3].category == AssetMovementCategory.WITHDRAWAL
    assert movements[3].timestamp == 1439958287
    assert isinstance(movements[3].asset, Asset)
    assert movements[3].asset == A_ETH
    assert movements[3].amount == FVal('55')
    assert movements[3].fee == FVal('0.0015')

    # now test a particular time range and see that we only get 1 withdrawal and 1 deposit
    with patch.object(bittrex.session, 'get', side_effect=mock_get_deposit_withdrawal):
        movements = bittrex.query_online_deposits_withdrawals(start_ts=0, end_ts=1419984000)

    assert len(movements) == 2
    assert len(errors) == 0
    assert len(warnings) == 0

    assert movements[0].category == AssetMovementCategory.DEPOSIT
    assert movements[0].timestamp == 1392277133
    assert movements[1].category == AssetMovementCategory.WITHDRAWAL
    assert movements[1].timestamp == 1404879887


def test_bittrex_query_deposits_withdrawals_unexpected_data(bittrex):
    """Test that we handle unexpected bittrex deposit withdrawal data gracefully"""

    def mock_bittrex_and_query(deposits, withdrawals, expected_warnings_num, expected_errors_num):

        def mock_get_deposit_withdrawal(url):  # pylint: disable=unused-argument
            if 'deposit' in url:
                response_str = deposits
            else:
                response_str = withdrawals

            return MockResponse(200, response_str)

        with patch.object(bittrex.session, 'get', side_effect=mock_get_deposit_withdrawal):
            movements = bittrex.query_online_deposits_withdrawals(start_ts=0, end_ts=TEST_END_TS)

        if expected_errors_num == 0 and expected_warnings_num == 0:
            assert len(movements) == 1
        else:
            assert len(movements) == 0
            warnings = bittrex.msg_aggregator.consume_warnings()
            assert len(warnings) == expected_warnings_num
            errors = bittrex.msg_aggregator.consume_errors()
            assert len(errors) == expected_errors_num

    def check_permutations_of_input_invalid_data(deposits, withdrawals):
        # First make sure it works with normal data
        mock_bittrex_and_query(
            deposits,
            withdrawals,
            expected_warnings_num=0,
            expected_errors_num=0,
        )
        testing_deposits = 'Currency' in deposits

        # From here and on test unexpected data
        # invalid timestamp
        if testing_deposits:
            new_deposits = deposits.replace('"2014-07-09T04:24:47.217"', '"dsadasd"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"2014-07-09T04:24:47.217"', '"dsadasd"')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # invalid currency
        if testing_deposits:
            new_deposits = deposits.replace('"BTC"', '[]')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"BTC"', '[]')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Unknown asset
        if testing_deposits:
            new_deposits = deposits.replace('"BTC"', '"dasdsDSDSAD"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"BTC"', '"dasdsDSDSAD"')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Unsupported Asset
        if testing_deposits:
            new_deposits = deposits.replace('"BTC"', '"OGO"')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"BTC"', '"OGO"')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=1,
            expected_errors_num=0,
        )

        # Invalid amount
        if testing_deposits:
            new_deposits = deposits.replace('17', 'null')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('17', 'null')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

        # Invalid fee, only for withdrawals
        if testing_deposits:
            new_withdrawals = withdrawals.replace('0.0002', '"dsadsda"')
            mock_bittrex_and_query(
                new_deposits,
                new_withdrawals,
                expected_warnings_num=0,
                expected_errors_num=1,
            )

        # Missing Key Error
        if testing_deposits:
            new_deposits = deposits.replace('"Currency": "BTC",', '')
            new_withdrawals = withdrawals
        else:
            new_deposits = deposits
            new_withdrawals = withdrawals.replace('"Currency": "BTC",', '')
        mock_bittrex_and_query(
            new_deposits,
            new_withdrawals,
            expected_warnings_num=0,
            expected_errors_num=1,
        )

    # To make the test easy to write the values for deposit/withdrawal attributes
    # are the same in the two examples below
    empty_response = '{"success": true, "message": "''", "result": []}'
    input_withdrawals = """{
    "success": true,
    "message": "''",
    "result": [
    {
      "PaymentUuid": "b52c7a5c-90c6-4c6e-835c-e16df12708b1",
      "Currency": "BTC",
      "Amount": 17,
      "Address": "1DeaaFBdbB5nrHj87x3NHS4onvw1GPNyAu",
      "Opened": "2014-07-09T04:24:47.217",
      "Authorized": "boolean",
      "PendingPayment": "boolean",
      "TxCost": 0.0002,
      "TxId": "b4a575c2a71c7e56d02ab8e26bb1ef0a2f6cf2094f6ca2116476a569c1e84f6e",
      "Canceled": "boolean",
      "InvalidAddress": "boolean"
    }]}"""
    check_permutations_of_input_invalid_data(
        deposits=empty_response,
        withdrawals=input_withdrawals,
    )

    input_deposits = """{
    "success": true,
    "message": "''",
    "result": [
    {
      "Id": 1,
      "Amount": 17,
      "Currency": "BTC",
      "Confirmations": 2,
      "LastUpdated": "2014-07-09T04:24:47.217",
      "TxId": "e26d3b33fcfc2cb0c74d0938034956ea590339170bf4102f080eab4b85da9bde",
      "CryptoAddressAddress": "1DeaaFBdbB5nrHj87x3NHS4onvw1GPNyAu"
    }]}"""
    check_permutations_of_input_invalid_data(
        deposits=input_deposits,
        withdrawals=empty_response,
    )
