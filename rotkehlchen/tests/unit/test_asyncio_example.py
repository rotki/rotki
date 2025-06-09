"""Example test showing asyncio usage in rotki tests"""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from rotkehlchen.tasks.manager import TaskManager
from rotkehlchen.user_messages import MessagesAggregator


@pytest.mark.asyncio
async def test_async_task_manager_basic():
    """Test basic async task manager functionality"""
    # Create mock dependencies
    msg_aggregator = Mock(spec=MessagesAggregator)
    
    # Create task manager
    task_manager = TaskManager(msg_aggregator=msg_aggregator)
    
    # Define a simple async task
    async def sample_task():
        await asyncio.sleep(0.1)
        return 'task completed'
    
    # Test spawning and tracking a task
    task = task_manager.spawn_and_track(coro=sample_task())
    assert task is not None
    
    # Wait for task completion
    result = await task.task
    assert result == 'task completed'


@pytest.mark.asyncio
async def test_async_task_cancellation():
    """Test task cancellation"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    task_manager = TaskManager(msg_aggregator=msg_aggregator)
    
    # Create a long-running task
    async def long_task():
        try:
            await asyncio.sleep(10)
            return 'should not reach here'
        except asyncio.CancelledError:
            return 'task cancelled'
    
    # Spawn the task
    task = task_manager.spawn_and_track(coro=long_task())
    
    # Cancel it immediately
    task.task.cancel()
    
    # Verify it was cancelled
    with pytest.raises(asyncio.CancelledError):
        await task.task


def test_sync_to_async_compatibility():
    """Test that sync code can still work with async infrastructure"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    task_manager = TaskManager(msg_aggregator=msg_aggregator)
    
    # Define a sync function
    def sync_function():
        return 'sync result'
    
    # Spawn it using the compatibility layer
    task = task_manager.spawn_and_track(method=sync_function)
    assert task is not None
    
    # The result should be available eventually
    # In real usage, this would be checked asynchronously
    

@pytest.mark.asyncio
async def test_multiple_concurrent_tasks():
    """Test running multiple tasks concurrently"""
    msg_aggregator = Mock(spec=MessagesAggregator)
    task_manager = TaskManager(msg_aggregator=msg_aggregator)
    
    results = []
    
    async def task_with_delay(delay: float, value: str):
        await asyncio.sleep(delay)
        results.append(value)
        return value
    
    # Spawn multiple tasks
    tasks = []
    for i in range(3):
        task = task_manager.spawn_and_track(
            coro=task_with_delay(0.1 * (3 - i), f'task_{i}')
        )
        tasks.append(task)
    
    # Wait for all tasks
    await asyncio.gather(*[t.task for t in tasks])
    
    # Results should be in reverse order due to delays
    assert results == ['task_2', 'task_1', 'task_0']


@pytest.mark.asyncio 
async def test_websocket_mock():
    """Test mocking websocket functionality"""
    # Example of how to mock async websocket behavior
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock(return_value='{"type": "test", "data": "value"}')
    
    # Simulate websocket interaction
    await mock_ws.send('test message')
    mock_ws.send.assert_called_once_with('test message')
    
    response = await mock_ws.recv()
    assert response == '{"type": "test", "data": "value"}'