import pytest

from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockBittrex(Bittrex):
    pass


@pytest.fixture(scope='session')
def bittrex(database, session_inquirer, messages_aggregator):
    mock = MockBittrex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_bittrex(database, function_scope_messages_aggregator):
    mock = MockBittrex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
