"""Tests for asyncio migration components"""
import asyncio
from unittest.mock import Mock, patch

import pytest

from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.errors.misc import TaskKilledError
from rotkehlchen.tasks.async_manager import AsyncTaskManager
from rotkehlchen.user_messages import MessagesAggregator


class MockWebSocket:
    """Mock WebSocket for testing"""
    
    def __init__(self):
        self.messages = []
        self.closed = False
        
    async def send(self, message: str):
        if not self.closed:
            self.messages.append(message)
            
    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_async_notifier_broadcast():
    """Test AsyncRotkiNotifier broadcasting"""
    notifier = AsyncRotkiNotifier()
    
    # Create mock websockets
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    
    # Subscribe websockets
    await notifier.subscribe(ws1)
    await notifier.subscribe(ws2)
    
    # Broadcast message
    await notifier.broadcast(
        message_type=WSMessageType.BALANCE_SNAPSHOT_ERROR,
        to_send_data={'error': 'Test error'},
    )
    
    # Check both received the message
    assert len(ws1.messages) == 1
    assert len(ws2.messages) == 1
    assert 'balance_snapshot_error' in ws1.messages[0]
    
    # Unsubscribe one
    await notifier.unsubscribe(ws1)
    
    # Broadcast again
    await notifier.broadcast(
        message_type=WSMessageType.REFRESH_BALANCES,
        to_send_data={'refresh': True},
    )
    
    # Only ws2 should receive
    assert len(ws1.messages) == 1  # No new message
    assert len(ws2.messages) == 2  # Got new message


@pytest.mark.asyncio
async def test_async_task_manager():
    """Test AsyncTaskManager functionality"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    manager = AsyncTaskManager(msg_aggregator)
    
    # Create a simple async task
    async def sample_task():
        await asyncio.sleep(0.1)
        return "completed"
    
    # Spawn and track task
    tracked = await manager.spawn_and_track(
        task_name="test_task",
        coro=sample_task(),
        exception_is_error=True,
    )
    
    # Check task is tracked
    assert manager.has_task("test_task")
    assert manager.task_count == 1
    
    # Wait for completion
    await manager.wait_for_all(timeout=1.0)
    
    # Check task completed
    assert tracked.done
    assert not manager.has_task("test_task")
    
    # Clear finished
    manager.clear_finished()
    assert manager.task_count == 0


@pytest.mark.asyncio
async def test_task_manager_exception_handling():
    """Test AsyncTaskManager exception handling"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    manager = AsyncTaskManager(msg_aggregator)
    
    # Task that raises exception
    async def failing_task():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")
    
    # Spawn with exception as error
    tracked = await manager.spawn_and_track(
        task_name="failing_task",
        coro=failing_task(),
        exception_is_error=True,
    )
    
    # Wait for completion
    await asyncio.sleep(0.2)
    
    # Check error was reported
    assert tracked.done
    assert tracked.exception() is not None
    msg_aggregator.add_error.assert_called_once()
    
    # Reset mock
    msg_aggregator.reset_mock()
    
    # Spawn with exception not as error
    tracked2 = await manager.spawn_and_track(
        task_name="failing_task_2",
        coro=failing_task(),
        exception_is_error=False,
    )
    
    await asyncio.sleep(0.2)
    
    # Error should not be reported
    msg_aggregator.add_error.assert_not_called()


@pytest.mark.asyncio
async def test_task_cancellation():
    """Test task cancellation"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    manager = AsyncTaskManager(msg_aggregator)
    
    # Long running task
    async def long_task():
        await asyncio.sleep(10.0)
    
    tracked = await manager.spawn_and_track(
        task_name="long_task",
        coro=long_task(),
    )
    
    # Cancel it
    tracked.cancel()
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    # Check it's cancelled
    assert tracked.cancelled
    assert tracked.done
    
    # Clear should remove it
    manager.clear()
    assert manager.task_count == 0


@pytest.mark.asyncio
async def test_delayed_task():
    """Test delayed task spawning"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    manager = AsyncTaskManager(msg_aggregator)
    
    start_time = asyncio.get_event_loop().time()
    
    async def delayed_task():
        return asyncio.get_event_loop().time() - start_time
    
    # Spawn with delay
    tracked = await manager.spawn_and_track(
        task_name="delayed",
        coro=delayed_task(),
        delay=0.5,
    )
    
    # Wait for completion
    await asyncio.sleep(0.6)
    
    # Check delay was applied
    result = tracked.task.result()
    assert result >= 0.5