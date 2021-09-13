from rotkehlchen.assets.converters import asset_from_uphold, UPHOLD_TO_WORLD


def test_uphold_all_symbols_are_known():
    """
    Test that the hardcoded uphold symbols are all supported by rotki
    May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    symbols = list(UPHOLD_TO_WORLD.keys())
    for symbol in symbols:
        asset = asset_from_uphold(symbol)
        assert asset is not None
