import pytest


@pytest.fixture
def greenlet_manager(messages_aggregator):
    """Mock greenlet manager for tests - no longer used with asyncio"""
    class MockGreenletManager:
        def __init__(self, msg_aggregator):
            self.msg_aggregator = msg_aggregator
        
        def clear(self):
            pass
    
    manager = MockGreenletManager(msg_aggregator=messages_aggregator)
    yield manager
    manager.clear()