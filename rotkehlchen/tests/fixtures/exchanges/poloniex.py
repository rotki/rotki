import pytest

from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockPoloniex(Poloniex):
    pass


@pytest.fixture(scope='session')
def poloniex(
        session_database,
        session_inquirer,  # pylint: disable=unused-argument
        messages_aggregator,
):
    mock = MockPoloniex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=session_database,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_poloniex(
        database,
        inquirer,  # pylint: disable=unused-argument
        function_scope_messages_aggregator,
):
    mock = MockPoloniex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
