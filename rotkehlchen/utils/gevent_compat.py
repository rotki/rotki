"""Compatibility layer for gevent to asyncio migration

This module provides a single place to handle conditional imports during
the migration from gevent to asyncio. It automatically selects the appropriate
implementation based on feature flags.

IMPORTANT: This is a transitional module. When AsyncFeature.TASK_MANAGER is
enabled, the calling code must also be converted to async/await patterns.
The async implementations here are placeholders showing the future API.
"""
# Compatibility imports during migration
try:
    from rotkehlchen.api.feature_flags import async_features, AsyncFeature
    
    if async_features.is_enabled(AsyncFeature.TASK_MANAGER):
        # Use asyncio implementations - calling code must be async
        import asyncio
        import threading
        
        sleep = asyncio.sleep  # Requires await
        Semaphore = asyncio.Semaphore
        Event = asyncio.Event  
        Lock = asyncio.Lock
        Queue = asyncio.Queue
        
        async def spawn(coro):
            """Create and return an asyncio task"""
            return asyncio.create_task(coro)
            
        def kill_all(tasks):
            """Cancel all async tasks"""
            for task in tasks:
                task.cancel()
                
        def kill(task):
            """Cancel a single task"""
            task.cancel()
            
        async def joinall(tasks, timeout=None):
            """Wait for all tasks to complete"""
            return await asyncio.gather(*tasks, return_exceptions=True)
            
        async def wait(objects=None, timeout=None, count=None):
            """Wait for objects"""
            if objects:
                done, pending = await asyncio.wait(objects, timeout=timeout)
                return done
            else:
                await asyncio.sleep(timeout if timeout else 0)
                return set()
                
        # Use asyncio timeout
        from asyncio import timeout as Timeout
        
        class Pool:
            """Simple async pool implementation"""
            def __init__(self, size=None):
                self.size = size or 10
                self._semaphore = asyncio.Semaphore(self.size)
                
            async def spawn(self, coro):
                async with self._semaphore:
                    return await coro
                    
        def get_hub():
            """Get the current event loop"""
            try:
                return asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.get_event_loop()
            
        def signal(sig, handler):
            """Register signal handler"""
            loop = get_hub()
            loop.add_signal_handler(sig, handler)
            
        def getcurrent():
            """Get current context (thread in async mode)"""
            return threading.current_thread()
            
        def spawn_later(seconds, coro):
            """Schedule a coroutine to run after specified seconds"""
            async def delayed_task():
                await asyncio.sleep(seconds)
                return await coro
            return asyncio.create_task(delayed_task())
            
        # Exception types
        class ConcurrentObjectUseError(Exception):
            """Error when an object is used concurrently"""
            pass
            
        # Type alias for compatibility
        from asyncio import Task as Greenlet
                
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
            
        def get_hub():
            """Get the gevent hub"""
            return gevent.get_hub()
            
        def signal(sig, handler):
            """Register signal handler"""
            gevent.signal(sig, handler)
            
        def getcurrent():
            """Get current greenlet"""
            return gevent.getcurrent()
            
        def spawn_later(seconds, func, *args, **kwargs):
            """Schedule a greenlet to run after specified seconds"""
            return gevent.spawn_later(seconds, func, *args, **kwargs)
            
        # Import exception types
        from gevent.exceptions import ConcurrentObjectUseError
            
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
        
    def get_hub():
        """Get the gevent hub"""
        return gevent.get_hub()
        
    def signal(sig, handler):
        """Register signal handler"""
        gevent.signal(sig, handler)
        
    def getcurrent():
        """Get current greenlet"""
        return gevent.getcurrent()
        
    def spawn_later(seconds, func, *args, **kwargs):
        """Schedule a greenlet to run after specified seconds"""
        return gevent.spawn_later(seconds, func, *args, **kwargs)
        
    # Import exception types
    from gevent.exceptions import ConcurrentObjectUseError

# Export Greenlet type for type annotations if not already defined
try:
    if 'Greenlet' not in locals():
        if async_features.is_enabled(AsyncFeature.TASK_MANAGER):
            # Already imported above
            pass
        else:
            from gevent import Greenlet
except (ImportError, NameError):
    if 'Greenlet' not in locals():
        from gevent import Greenlet

__all__ = [
    'sleep', 'spawn', 'kill', 'kill_all', 'joinall', 'wait',
    'Semaphore', 'Event', 'Lock', 'Queue', 
    'Timeout', 'Pool', 'Greenlet', 'get_hub', 'signal', 'getcurrent',
    'spawn_later', 'ConcurrentObjectUseError'
]