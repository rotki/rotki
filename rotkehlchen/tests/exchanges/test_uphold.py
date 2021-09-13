import warnings as test_warnings

from rotkehlchen.assets.converters import asset_from_uphold, UPHOLD_TO_WORLD
from rotkehlchen.errors import UnknownAsset


def test_uphold_all_symbols_are_known():
    """
    Test that the uphold symbols are all supported by rotki
    May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    symbols = list(UPHOLD_TO_WORLD.keys())
    for symbol in symbols:
        asset = None
        try:
            asset = asset_from_uphold(symbol)
        except UnknownAsset as e:
            test_warnings.warn(UserWarning(
                f'Unknown uphold asset detected. {e}',
            ))

        assert asset is not None
