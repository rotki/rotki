import pytest

from rotkehlchen.tests.utils.ports import get_free_port


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
def api_port(port_generator):
    port = next(port_generator)
    return port


@pytest.fixture
def added_exchanges():
    """A fixture determining which exchanges to add to a test rotkehlchen api server"""
    return (
        'kraken',
        'poloniex',
        'bittrex',
        'binance',
        'bitmex',
        'coinbase',
        'coinbasepro',
        'gemini',
        'bitstamp',
        'bitfinex',
    )
