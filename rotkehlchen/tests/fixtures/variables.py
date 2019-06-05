import random

import pytest

from rotkehlchen.ports import get_free_port


@pytest.fixture
def random_marker():
    """ A random marker used to identify a pytest run.

    Some tests will spawn a private chain, the private chain will be one or
    more ethereum nodes on a new subprocesss. These nodes may fail to start on
    concurrent test runs, mostly because of port number conflicts, but even
    though the test fails to start its private chain it may run interacting
    with the geth process from a different test run! This leads to
    unreasonable test errors.

    This fixture creates a random marker used to distinguish pytest runs and
    avoid test failures. Note this could fail for other reasons and fail to
    detect unwanted interations if the user sets the PYTHONHASHSEED to the same
    value.
    """
    random_hex = hex(random.getrandbits(100))

    # strip the leading 0x and trailing L
    return random_hex[2:-1]


@pytest.fixture(scope='session')
def port_generator(request):
    """ count generator used to get a unique port number. """
    return get_free_port('127.0.0.1', request.config.option.initial_port)


@pytest.fixture
def db_password():
    return '123'
