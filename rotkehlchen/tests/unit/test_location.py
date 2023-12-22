from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES
from rotkehlchen.types import Location


def test_location_details_coverage():
    """Test that all locations are covered in the location details"""
    for location in Location:
        if location == Location.TOTAL:
            continue  # this is a big exception we need to get rid of
        assert location in LOCATION_DETAILS
        if location in SUPPORTED_EXCHANGES:
            assert 'is_exchange_with_key' in LOCATION_DETAILS[location]
