from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.converters import (
    BITTREX_TO_WORLD,
    UNSUPPORTED_BITTREX_ASSETS,
    asset_from_bittrex,
)
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.errors import UnsupportedAsset


def test_bittrex_assets_are_known(bittrex):
    currencies = bittrex.get_currencies()
    for bittrex_asset in currencies:
        symbol = bittrex_asset['Currency']
        try:
            _ = asset_from_bittrex(symbol)
        except UnsupportedAsset:
            assert symbol in UNSUPPORTED_BITTREX_ASSETS

    # checking_index = 199
    # for idx, bittrex_asset in enumerate(currencies):
    #     if idx >= checking_index:
    #         symbol = bittrex_asset['Currency']
    #         if symbol in UNSUPPORTED_BITTREX_ASSETS:
    #             print(f'{idx} - {symbol} is NOT SUPPORTED')
    #             continue

    #         if not AssetResolver().is_symbol_canonical(symbol):
    #             msg = (
    #                 f'{idx} - {symbol} is not known. '
    #                 f'Bittrex name: {bittrex_asset["CurrencyLong"]}'
    #             )
    #             assert False, msg
    #         else:
    #             asset = Asset(symbol)
    #             print(
    #                 f'{idx} - {symbol} with name {asset.name} '
    #                 f'is known. Bittrex name: {bittrex_asset["CurrencyLong"]}',
    #             )
