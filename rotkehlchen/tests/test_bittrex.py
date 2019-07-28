from typing import Any, Dict, List
from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_BITTREX_ASSETS, asset_from_bittrex
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.order_formatting import Trade
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import TradeType


def analyze_bittrex_assets(currencies: List[Dict[str, Any]]):
    """Go through all bittrex assets and print info whether or not Rotkehlchen
    supports each asset or not.

    This function should be used when wanting to analyze/categorize new Bittrex assets
    """
    checking_index = 0
    for idx, bittrex_asset in enumerate(currencies):
        if idx >= checking_index:
            symbol = bittrex_asset['Currency']
            if symbol in UNSUPPORTED_BITTREX_ASSETS:
                print(f'{idx} - {symbol} is NOT SUPPORTED')
                continue

            if not AssetResolver().is_identifier_canonical(symbol):
                raise AssertionError(
                    f'{idx} - {symbol} is not known. '
                    f'Bittrex name: {bittrex_asset["CurrencyLong"]}',
                )
            else:
                asset = Asset(symbol)
                print(
                    f'{idx} - {symbol} with name {asset.name} '
                    f'is known. Bittrex name: {bittrex_asset["CurrencyLong"]}',
                )


def test_bittrex_assets_are_known(bittrex):
    currencies = bittrex.get_currencies()
    for bittrex_asset in currencies:
        symbol = bittrex_asset['Currency']
        try:
            _ = asset_from_bittrex(symbol)
        except UnsupportedAsset:
            assert symbol in UNSUPPORTED_BITTREX_ASSETS


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
    # turn caching off
    bittrex.cache_ttl_secs = 0

    def mock_order_history(url):  # pylint: disable=unused-argument
        response = MockResponse(200, BITTREX_ORDER_HISTORY_RESPONSE)
        return response

    with patch.object(bittrex.session, 'get', side_effect=mock_order_history):
        # Test that after querying the assets only ETH and BTC are there
        trades = bittrex.query_trade_history(0, 1564301134, 1564301134)

    expected_trade = Trade(
        timestamp=1392249600,
        location='bittrex',
        pair='LTC_BTC',
        trade_type=TradeType.BUY,
        amount=FVal('667.03644955'),
        rate=FVal('0.0000295'),
        fee=FVal('0.00004921'),
        fee_currency=A_BTC,
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
            trades = bittrex.query_trade_history(0, 1564301134, 1564301134)

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
