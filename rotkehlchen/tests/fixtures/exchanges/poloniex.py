import base64

import pytest

from rotkehlchen.exchanges.poloniex import Poloniex
from rotkehlchen.tests.utils.factories import make_random_b64bytes


class MockPoloniex(Poloniex):
    pass


@pytest.fixture(scope='session')
def poloniex(session_data_dir, session_inquirer, messages_aggregator):
    mock = MockPoloniex(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        user_directory=session_data_dir,
        msg_aggregator=messages_aggregator,
    )
    return mock


@pytest.fixture(scope='function')
def function_scope_poloniex(accounting_data_dir, inquirer, function_scope_messages_aggregator):
    mock = MockPoloniex(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        user_directory=accounting_data_dir,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return mock
