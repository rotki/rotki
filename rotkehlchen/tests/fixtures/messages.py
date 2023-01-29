import pytest

from rotkehlchen.user_messages import MessagesAggregator


@pytest.fixture(scope='session')
def messages_aggregator():
    return MessagesAggregator()


@pytest.fixture()
def function_scope_messages_aggregator():
    return MessagesAggregator()
