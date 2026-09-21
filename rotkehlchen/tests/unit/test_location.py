from rotkehlchen.constants.location_details import LOCATION_DETAILS
from rotkehlchen.exchanges.constants import (
    ALL_SUPPORTED_EXCHANGES,
    EXCHANGES_WITH_PASSPHRASE,
    EXCHANGES_WITHOUT_API_SECRET,
    SUPPORTED_EXCHANGES,
    serialize_exchange_connectors,
)
from rotkehlchen.locations.catalog import load_builtin_catalog


def test_location_details_coverage():
    """Test that all locations are covered in the location details and every exchange
    location is flagged as one"""
    for location in (x.identifier for x in load_builtin_catalog()):
        assert location in LOCATION_DETAILS
        if location in ALL_SUPPORTED_EXCHANGES:
            assert LOCATION_DETAILS[location]['is_exchange'] is True


def test_exchange_connectors_serialization():
    """Every supported exchange connector is listed with what its setup needs, and its data
    goes to a known location"""
    connectors = {x['connector']: x for x in serialize_exchange_connectors()}
    assert connectors.keys() == set(SUPPORTED_EXCHANGES)
    builtin = {x.identifier for x in load_builtin_catalog()}
    for connector, details in connectors.items():
        assert details['location'] in builtin
        assert details['is_exchange_with_passphrase'] is (connector in EXCHANGES_WITH_PASSPHRASE)
        assert details['is_exchange_without_api_secret'] is (connector in EXCHANGES_WITHOUT_API_SECRET)  # noqa: E501


def test_coinex_exists_in_db_schema():
    """Test that fresh user DBs contain CoinEx."""
    assert ('coinex', 'exchanges') in {
        (x.identifier, x.parent_identifier) for x in load_builtin_catalog()
    }
