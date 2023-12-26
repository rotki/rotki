from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    SUPPORTED_EXCHANGES,
)
from rotkehlchen.types import Location


def test_location_details_coverage():
    """Test that all locations are covered in the location details"""
    for location in Location:
        if location == Location.TOTAL:
            continue  # this is a big exception we need to get rid of
        assert location in LOCATION_DETAILS
        if location in ALL_SUPPORTED_EXCHANGES:
            location_detail = LOCATION_DETAILS[location]
            assert 'is_exchange' in location_detail
            if location in SUPPORTED_EXCHANGES:
                assert 'exchange_data' in location_detail
                exchange_data = location_detail['exchange_data']
                assert 'is_exchange_with_key' in exchange_data
                if location in EXCHANGES_WITH_PASSPHRASE:
                    assert 'is_exchange_with_passphrase' in exchange_data
                if location in EXCHANGES_WITHOUT_API_SECRET:
                    assert 'is_exchange_without_api_secret' in exchange_data
