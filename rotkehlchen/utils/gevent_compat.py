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
                
    else:
        # Use gevent implementations
        import gevent
        from gevent import sleep, spawn
        from gevent.lock import Semaphore
        from gevent.event import Event
        from gevent.lock import BoundedSemaphore as Lock
        from gevent.queue import Queue
        
        def kill_all(greenlets):
            """Kill all greenlets"""
            gevent.killall(greenlets)
            
except ImportError:
    # Fallback to gevent if feature flags not available
    import gevent
    from gevent import sleep, spawn
    from gevent.lock import Semaphore
    from gevent.event import Event
    from gevent.lock import BoundedSemaphore as Lock
    from gevent.queue import Queue
    
    def kill_all(greenlets):
        """Kill all greenlets"""
        gevent.killall(greenlets)

__all__ = ['sleep', 'spawn', 'Semaphore', 'Event', 'Lock', 'Queue', 'kill_all']