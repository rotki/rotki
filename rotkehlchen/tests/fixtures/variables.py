import re
from collections.abc import Sequence
from itertools import count

import pytest

from rotkehlchen.types import Location


@pytest.fixture(scope='session', name='port_generator')
def fixture_port_generator(request, worker_id):
    """Generate deterministic non-overlapping ports across xdist workers."""
    worker_idx = 0
    if worker_id != 'master' and (match := re.match(r'gw(\d+)$', worker_id)) is not None:
        worker_idx = int(match.group(1))

    if hasattr(request.config, 'workerinput'):
        worker_count = int(request.config.workerinput['workercount'])
    else:
        worker_count = int(request.config.option.numprocesses or 1)

    step = max(1, worker_count)
    start_port = int(request.config.option.initial_port) + worker_idx
    return count(start_port, step)


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
