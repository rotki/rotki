"""Pytest configuration for async tests

This module provides async-specific fixtures and configuration for pytest.
"""
import asyncio
import pytest
from typing import Any, Callable


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for the test session"""
    return asyncio.DefaultEventLoopPolicy()


# Fixture to run sync functions in executor when in async context
@pytest.fixture
def run_in_executor():
    """Run synchronous function in thread executor from async context"""
    async def _run(func: Callable, *args: Any, **kwargs: Any) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    return _run


# Async fixtures for common test needs
@pytest.fixture
async def async_db():
    """Provide async database connection for tests"""
    from rotkehlchen.db.drivers.asyncio_sqlite import AsyncDBConnection, DBConnectionType
    
    db = AsyncDBConnection(":memory:", DBConnectionType.GLOBAL)
    await db.connect()
    yield db
    await db.close()


@pytest.fixture
async def async_task_manager(messages_aggregator):
    """Provide async task manager for tests"""
    from rotkehlchen.tasks.async_manager import AsyncTaskManager
    
    manager = AsyncTaskManager(messages_aggregator)
    yield manager
    manager.clear()  # Clean up any remaining tasks