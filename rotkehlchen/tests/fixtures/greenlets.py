import pytest

from rotkehlchen.greenlets import GreenletManager


@pytest.fixture(scope='session')
def greenlet_manager(messages_aggregator):
    return GreenletManager(msg_aggregator=messages_aggregator)


@pytest.fixture
def function_greenlet_manager(function_scope_messages_aggregator):
    return GreenletManager(msg_aggregator=function_scope_messages_aggregator)
