"""Unified task manager interface for migration period

Provides a single interface that automatically uses the appropriate
task manager implementation based on feature flags.
"""
import asyncio
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional, Union

from rotkehlchen.api.feature_flags import AsyncFeature, async_features
from rotkehlchen.utils.gevent_compat import Greenlet
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.async_manager import AsyncTaskManager, AsyncTask
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UnifiedTaskManager:
    """Unified task manager that uses appropriate implementation"""
    
    def __init__(self, msg_aggregator: MessagesAggregator):
        self.msg_aggregator = msg_aggregator
        self.use_async = async_features.is_enabled(AsyncFeature.TASK_MANAGER)
        
        if self.use_async:
            log.info("Using AsyncTaskManager")
            self._async_manager = AsyncTaskManager()
            self._sync_manager = None
            self._executor = ThreadPoolExecutor(max_workers=2)
            self._loop: Optional[asyncio.AbstractEventLoop] = None
            self._start_async_loop()
        else:
            log.info("Using GreenletManager")
            self._sync_manager = GreenletManager(msg_aggregator)
            self._async_manager = None
            self._executor = None
            
    def _start_async_loop(self):
        """Start async event loop in thread if using async manager"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
            
        self._executor.submit(run_loop)
        
        # Wait for loop to start
        while self._loop is None:
            import time
            time.sleep(0.01)
            
    def spawn_task(
        self,
        task_name: str,
        task_fn: Callable,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Union[Greenlet, Future]:
        """Spawn a task using appropriate manager"""
        if self.use_async:
            # Convert sync function to async if needed
            if asyncio.iscoroutinefunction(task_fn):
                coro = task_fn(**kwargs)
            else:
                async def async_wrapper():
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, task_fn, **kwargs)
                coro = async_wrapper()
                
            # Schedule in async loop
            future = asyncio.run_coroutine_threadsafe(
                self._async_manager.spawn_and_track(
                    task_name=task_name,
                    coro=coro,
                    timeout=timeout,
                ),
                self._loop,
            )
            return future
        else:
            # Use sync manager
            return self._sync_manager.spawn_and_track(
                method=task_name,
                module_name='unified',
                **kwargs,
            )
            
    def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get status of a task"""
        if self.use_async:
            # Get from async manager
            future = asyncio.run_coroutine_threadsafe(
                self._async_manager.get_task(task_id),
                self._loop,
            )
            task = future.result()
            if task:
                return {
                    'id': task.id,
                    'name': task.name,
                    'status': task.status,
                    'created_at': task.created_at,
                    'completed_at': task.completed_at,
                    'error': task.error,
                }
        else:
            # Get from sync manager
            # Would need to implement task tracking in GreenletManager
            pass
            
        return None
        
    def cleanup(self):
        """Clean up resources"""
        if self.use_async and self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._executor:
                self._executor.shutdown(wait=True)
        elif self._sync_manager:
            # Stop all greenlets
            for greenlet in list(self._sync_manager.greenlets):
                greenlet.kill()


def create_task_manager(msg_aggregator: MessagesAggregator) -> UnifiedTaskManager:
    """Factory function to create appropriate task manager"""
    return UnifiedTaskManager(msg_aggregator)