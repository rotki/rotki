import pytest

from rotkehlchen.exchanges.bittrex import Bittrex
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


class MockBittrex(Bittrex):
    pass


@pytest.fixture(scope='session')
def bittrex(session_data_dir, session_inquirer, messages_aggregator):
    mock = MockBittrex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        user_directory=session_data_dir,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_bittrex(accounting_data_dir, function_scope_messages_aggregator):
    mock = MockBittrex(
        api_key=make_api_key(),
        secret=make_api_secret(),
        user_directory=accounting_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
