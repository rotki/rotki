import pytest

from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockPoloniex(Poloniex):
    pass


@pytest.fixture(scope='session')
def poloniex(session_data_dir, session_inquirer, messages_aggregator):
    mock = MockPoloniex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        user_directory=session_data_dir,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_poloniex(accounting_data_dir, inquirer, function_scope_messages_aggregator):
    mock = MockPoloniex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        user_directory=accounting_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
