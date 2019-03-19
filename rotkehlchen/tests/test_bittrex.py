from rotkehlchen.assets.converters import asset_from_bittrex


def test_bittrex_assets_are_known(bittrex):
    currencies = bittrex.get_currencies()
    for bittrex_asset in currencies:
        _ = asset_from_bittrex(bittrex_asset['Currency'])
