from typing import Any, Dict, List
from unittest.mock import patch

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import UNSUPPORTED_BITTREX_ASSETS, asset_from_bittrex
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.errors import UnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.mock import MockResponse


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
                msg = (
                    f'{idx} - {symbol} is not known. '
                    f'Bittrex name: {bittrex_asset["CurrencyLong"]}'
                )
                assert False, msg
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
    assert len(warnings) == 1
    assert 'unsupported/unknown bittrex asset IDONTEXIST' in warnings[0]
