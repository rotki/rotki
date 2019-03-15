import base64

import pytest

from rotkehlchen.poloniex import Poloniex
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.user_messages import MessagesAggregator


class MockPoloniex(Poloniex):
    pass


@pytest.fixture(scope='session')
def poloniex(session_data_dir, session_inquirer):
    mock = MockPoloniex(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        inquirer=session_inquirer,
        user_directory=session_data_dir,
        msg_aggregator=MessagesAggregator(),
    )
    return mock
