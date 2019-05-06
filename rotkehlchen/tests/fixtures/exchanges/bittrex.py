import base64

import pytest

from rotkehlchen.bittrex import Bittrex
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.user_messages import MessagesAggregator


class MockBittrex(Bittrex):
    pass


@pytest.fixture(scope='session')
def bittrex(session_data_dir, session_inquirer):
    mock = MockBittrex(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        secret=base64.b64encode(make_random_b64bytes(128)),
        user_directory=session_data_dir,
        msg_aggregator=MessagesAggregator(),
    )
    return mock
