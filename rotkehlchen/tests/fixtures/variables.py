from collections.abc import Sequence

import pytest

from rotkehlchen.tests.utils.ports import get_free_port
from rotkehlchen.types import Location


@pytest.fixture(scope='session', name='port_generator')
def fixture_port_generator(request):
    """ count generator used to get a unique port number. """
    return get_free_port('127.0.0.1', request.config.option.initial_port)


@pytest.fixture
def db_password():
    return '123'


@pytest.fixture
def rest_api_port(port_generator):
    return next(port_generator)


@pytest.fixture
def added_exchanges() -> Sequence[Location]:
    """A fixture determining which exchanges to add to a test rotkehlchen api server"""
    return (
        Location.KRAKEN,
        Location.POLONIEX,
        Location.BINANCE,
        Location.BITMEX,
        Location.COINBASE,
        Location.GEMINI,
        Location.BITSTAMP,
        Location.BITFINEX,
    )


@pytest.fixture
def network_mocking(request):
    """Uses the --no-network-mocking argument. By default when not passed, the network
    is mocked in all tests that are aware of it (by using this fixture).
    Once the --no-network-mocking argument is passed all tests that use this fixture
    switch to using the network instead.
    """
    return not request.config.getoption('--no-network-mocking', default=False)
