import pytest

from rotkehlchen.greenlets.manager import GreenletManager


@pytest.fixture
def greenlet_manager(messages_aggregator):
    manager = GreenletManager(msg_aggregator=messages_aggregator)
    yield manager
    manager.clear()
