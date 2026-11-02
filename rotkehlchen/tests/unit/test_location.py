import pytest

from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    SUPPORTED_EXCHANGES,
)
from rotkehlchen.locations.catalog import load_builtin_catalog
from rotkehlchen.types import LEGACY_PROTOCOL_LOCATIONS, Location


def test_location_details_coverage():
    """Test that all locations are covered in the location details"""
    for location in Location:
        if location == Location.TOTAL:
            continue  # this is a big exception we need to get rid of
        assert location in LOCATION_DETAILS
        if location in ALL_SUPPORTED_EXCHANGES:
            location_detail = LOCATION_DETAILS[location]
            if location in SUPPORTED_EXCHANGES:
                assert 'exchange_details' in location_detail
                exchange_details = location_detail['exchange_details']
                assert 'is_exchange_with_key' in exchange_details
                if location in EXCHANGES_WITH_PASSPHRASE:
                    assert 'is_exchange_with_passphrase' in exchange_details
                if location in EXCHANGES_WITHOUT_API_SECRET:
                    assert 'is_exchange_without_api_secret' in exchange_details
                continue
            assert 'is_exchange' in location_detail


def test_coinex_exists_in_db_schema():
    """Test that fresh user DBs contain CoinEx."""
    assert ('coinex', 'exchanges') in {
        (x.identifier, x.parent_identifier) for x in load_builtin_catalog()
    }


def test_protocol_locations_are_stored_as_legacy_nodes() -> None:
    assert {x.serialize_for_db() for x in LEGACY_PROTOCOL_LOCATIONS} == {
        'legacy:uniswap', 'legacy:balancer', 'legacy:gitcoin', 'legacy:sushiswap',
    }
    for location in Location:
        assert Location.deserialize_from_db(location.serialize_for_db()) == location
        if location not in LEGACY_PROTOCOL_LOCATIONS:
            assert location.serialize_for_db() == location.serialize()


def test_only_protocol_locations_can_have_the_legacy_prefix() -> None:
    with pytest.raises(DeserializationError):
        Location.deserialize_from_db('legacy:kraken')
