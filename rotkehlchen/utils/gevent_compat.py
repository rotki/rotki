"""Compatibility layer for gevent to asyncio migration

This module provides a single place to handle conditional imports during
the migration from gevent to asyncio. It automatically selects the appropriate
implementation based on feature flags.
"""
# Compatibility imports during migration
try:
    from rotkehlchen.api.feature_flags import async_features, AsyncFeature
    
    if async_features.is_enabled(AsyncFeature.TASK_MANAGER):
        # Use asyncio implementations
        import asyncio
        
        sleep = asyncio.sleep
        Semaphore = asyncio.Semaphore
        Event = asyncio.Event
        Lock = asyncio.Lock
        Queue = asyncio.Queue
        
        def spawn(func, *args, **kwargs):
            """Spawn a task using asyncio"""
            return asyncio.create_task(func(*args, **kwargs))
            
        def kill_all(tasks):
            """Cancel all async tasks"""
            for task in tasks:
                task.cancel()
                
        def kill(task):
            """Cancel a single task"""
            task.cancel()
            
        def joinall(tasks, timeout=None):
            """Wait for all tasks to complete"""
            import asyncio
            return asyncio.gather(*tasks, return_exceptions=True)
            
        def wait(objects=None, timeout=None, count=None):
            """Wait for objects (simplified)"""
            import asyncio
            if objects:
                return asyncio.wait(objects, timeout=timeout)
            else:
                return asyncio.sleep(timeout if timeout else 0)
                
        class Timeout:
            """Async timeout context manager"""
            def __init__(self, seconds):
                self.seconds = seconds
                
            async def __aenter__(self):
                self.task = asyncio.create_task(asyncio.sleep(self.seconds))
                return self
                
            async def __aexit__(self, *args):
                self.task.cancel()
                
        # Pool is complex, provide basic interface
        class Pool:
            def __init__(self, size=None):
                self.size = size
                
            def spawn(self, func, *args, **kwargs):
                return spawn(func, *args, **kwargs)
                
    else:
        # Use gevent implementations
        import gevent
        from gevent import sleep, spawn, kill, joinall, wait, Timeout
        from gevent.lock import Semaphore
        from gevent.event import Event
        from gevent.lock import BoundedSemaphore as Lock
        from gevent.queue import Queue
        from gevent.pool import Pool
        
        def kill_all(greenlets):
            """Kill all greenlets"""
            gevent.killall(greenlets)
            
except ImportError:
    # Fallback to gevent if feature flags not available
    import gevent
    from gevent import sleep, spawn, kill, joinall, wait, Timeout
    from gevent.lock import Semaphore
    from gevent.event import Event
    from gevent.lock import BoundedSemaphore as Lock
    from gevent.queue import Queue
    from gevent.pool import Pool
    
    def kill_all(greenlets):
        """Kill all greenlets"""
        gevent.killall(greenlets)

# Export Greenlet type for type annotations
try:
    if async_features.is_enabled(AsyncFeature.TASK_MANAGER):
        # For async mode, we use asyncio.Task as Greenlet equivalent
        from asyncio import Task as Greenlet
    else:
        from gevent import Greenlet
except (ImportError, NameError):
    from gevent import Greenlet

__all__ = [
    'sleep', 'spawn', 'kill', 'kill_all', 'joinall', 'wait',
    'Semaphore', 'Event', 'Lock', 'Queue', 
    'Timeout', 'Pool', 'Greenlet'
]