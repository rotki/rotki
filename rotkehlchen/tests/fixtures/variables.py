from typing import Sequence

import pytest

from rotkehlchen.tests.utils.ports import get_free_port
from rotkehlchen.typing import Location


@pytest.fixture(scope='session', name='port_generator')
def fixture_port_generator(request):
    """ count generator used to get a unique port number. """
    return get_free_port('127.0.0.1', request.config.option.initial_port)


@pytest.fixture
def db_password():
    return '123'


@pytest.fixture(scope='session')
def session_db_password():
    return '123'


@pytest.fixture
def rest_api_port(port_generator):
    port = next(port_generator)
    return port


@pytest.fixture
def websockets_api_port(port_generator):
    port = next(port_generator)
    return port


@pytest.fixture
def added_exchanges() -> Sequence[Location]:
    """A fixture determining which exchanges to add to a test rotkehlchen api server"""
    return (
        Location.KRAKEN,
        Location.POLONIEX,
        Location.BITTREX,
        Location.BINANCE,
        Location.BITMEX,
        Location.COINBASE,
        Location.COINBASEPRO,
        Location.GEMINI,
        Location.BITSTAMP,
        Location.BITFINEX,
    )
