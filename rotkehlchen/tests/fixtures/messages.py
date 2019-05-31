import pytest

from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture
def messages_aggregator():
    return MessagesAggregator()
