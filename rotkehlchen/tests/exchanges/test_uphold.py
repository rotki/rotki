from rotkehlchen.assets.converters import asset_from_uphold
from rotkehlchen.locations.constants import (
    LOCATION_UPHOLD,
)
from rotkehlchen.tests.utils.exchanges import get_exchange_asset_symbols


def test_uphold_all_symbols_are_known() -> None:
    """
    Test that the hardcoded uphold symbols are all supported by rotki
    May raise:
    - DeserializationError
    - UnsupportedAsset
    - UnknownAsset
    """
    for symbol in get_exchange_asset_symbols(LOCATION_UPHOLD):
        asset = asset_from_uphold(symbol)
        assert asset is not None
