"""Compatibility module for gevent -> asyncio migration

This module provides backward compatibility for code that still imports from gevent_compat.
All functionality has been moved to the concurrency module using asyncio.
"""
# Re-export everything from concurrency module for backward compatibility
from rotkehlchen.utils.concurrency import *  # noqa: F403, F401

# Add specific imports that tests might be looking for
from rotkehlchen.utils.concurrency import (  # noqa: F401
    ConcurrentObjectUseError,
    Event,
    Greenlet,
    Lock,
    Pool,
    Queue,
    Semaphore,
    Task,
    get_hub,
    get_task_name,
    getcurrent,
    joinall,
    kill,
    kill_all,
    signal,
    sleep,
    spawn,
    spawn_later,
    timeout,
    wait,
)

# Additional compatibility aliases that might be expected
Timeout = timeout  # Some code might expect Timeout instead of timeout