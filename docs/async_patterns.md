# Async Patterns and Best Practices

This guide documents the async patterns used in the Rotki asyncio migration and provides best practices for developers.

## Overview

The migration from gevent to asyncio introduces modern Python async patterns throughout the codebase. This document explains the key patterns and how to use them effectively.

## Key Concepts

### 1. Natural Async/Await

Instead of gevent's implicit yielding through monkey patching, we use explicit async/await:

```python
# Before (gevent)
def query_balance(address):
    response = requests.get(f'/balance/{address}')  # Blocks but yields to other greenlets
    return response.json()

# After (asyncio)
async def query_balance(address):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'/balance/{address}') as response:
            return await response.json()
```

### 2. Concurrent Operations

Asyncio makes concurrent operations explicit and easier to reason about:

```python
# Concurrent balance queries
async def query_all_balances(addresses):
    tasks = [query_balance(addr) for addr in addresses]
    return await asyncio.gather(*tasks)
```

### 3. Database Operations

The async database layer uses a thread pool for SQLCipher operations:

```python
# Async database query
async with async_db.read_ctx() as cursor:
    await cursor.execute('SELECT * FROM balances WHERE address = ?', (address,))
    return await cursor.fetchall()
```

## Common Patterns

### Pattern 1: Async Context Managers

Use async context managers for resource management:

```python
class AsyncResource:
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

# Usage
async with AsyncResource() as resource:
    await resource.do_something()
```

### Pattern 2: Rate Limiting

Implement rate limiting with semaphores:

```python
class AsyncAPIClient:
    def __init__(self):
        self.rate_limit = asyncio.Semaphore(10)  # Max 10 concurrent requests
        
    async def make_request(self, endpoint):
        async with self.rate_limit:
            return await self._do_request(endpoint)
```

### Pattern 3: Background Tasks

Manage background tasks with proper lifecycle:

```python
class AsyncService:
    def __init__(self):
        self._task = None
        self._stop_event = asyncio.Event()
        
    async def start(self):
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        
    async def stop(self):
        self._stop_event.set()
        if self._task:
            await self._task
            
    async def _run(self):
        while not self._stop_event.is_set():
            await self._do_work()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
            except asyncio.TimeoutError:
                continue
```

### Pattern 4: Error Handling

Proper error handling in async code:

```python
async def safe_operation():
    try:
        return await risky_operation()
    except aiohttp.ClientError as e:
        log.error(f'Network error: {e}')
        raise RemoteError(f'Failed to connect: {e}')
    except asyncio.TimeoutError:
        log.error('Operation timed out')
        raise RemoteError('Request timed out')
```

### Pattern 5: Batch Processing

Process items in batches for efficiency:

```python
async def process_in_batches(items, batch_size=100):
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_tasks = [process_item(item) for item in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                log.error(f'Batch processing error: {result}')
            else:
                results.append(result)
                
    return results
```

## Migration Guidelines

### Converting Sync to Async

1. **Identify I/O Operations**: Focus on functions that perform I/O (network, disk, database)
2. **Add async/await**: Convert function signatures and add await to async calls
3. **Update Call Sites**: Propagate async up the call chain
4. **Test Concurrency**: Ensure concurrent operations work correctly

### Maintaining Compatibility

During migration, maintain compatibility with sync code:

```python
class HybridService:
    """Service that supports both sync and async usage"""
    
    def get_data_sync(self):
        """Synchronous method for compatibility"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.get_data_async())
        finally:
            loop.close()
            
    async def get_data_async(self):
        """Async method for new code"""
        return await self._fetch_data()
```

### Testing Async Code

Use pytest-asyncio for testing:

```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_operation()
    assert result == expected_value
    
@pytest.mark.asyncio
async def test_concurrent_operations():
    # Test that operations run concurrently
    start = time.time()
    await asyncio.gather(
        asyncio.sleep(1),
        asyncio.sleep(1),
        asyncio.sleep(1),
    )
    duration = time.time() - start
    assert duration < 1.5  # Should take ~1 second, not 3
```

## Performance Considerations

### 1. Connection Pooling

Reuse connections for better performance:

```python
class AsyncClient:
    def __init__(self):
        self.session = None
        
    async def ensure_session(self):
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
            )
            self.session = aiohttp.ClientSession(connector=connector)
```

### 2. Avoid Blocking Operations

Never use blocking operations in async code:

```python
# Bad - blocks the event loop
async def bad_example():
    time.sleep(1)  # Blocks!
    data = open('file.txt').read()  # Blocks!
    
# Good - use async equivalents
async def good_example():
    await asyncio.sleep(1)
    async with aiofiles.open('file.txt') as f:
        data = await f.read()
```

### 3. CPU-Bound Operations

Use thread/process pools for CPU-bound operations:

```python
async def compute_intensive_task(data):
    loop = asyncio.get_event_loop()
    
    # Run in thread pool
    result = await loop.run_in_executor(None, cpu_bound_function, data)
    
    return result
```

## Debugging Async Code

### Enable Asyncio Debug Mode

```python
import asyncio
asyncio.set_debug(True)

# Or via environment variable
export PYTHONASYNCIODEBUG=1
```

### Common Issues and Solutions

1. **Forgotten await**
   ```python
   # Wrong - creates coroutine but doesn't run it
   result = async_function()
   
   # Correct
   result = await async_function()
   ```

2. **Synchronous code in async function**
   ```python
   # Wrong - blocks event loop
   async def fetch_data():
       response = requests.get(url)  # Blocking!
       
   # Correct
   async def fetch_data():
       async with aiohttp.ClientSession() as session:
           async with session.get(url) as response:
               return await response.text()
   ```

3. **Unclosed resources**
   ```python
   # Wrong - session never closed
   session = aiohttp.ClientSession()
   
   # Correct - use context manager
   async with aiohttp.ClientSession() as session:
       # Use session
   ```

## Monitoring and Profiling

Use the built-in performance monitoring:

```python
from rotkehlchen.utils.async_performance import measure_performance

@measure_performance('async')
async def monitored_operation():
    return await do_something()

# View metrics
from rotkehlchen.utils.async_performance import performance_monitor
summary = performance_monitor.get_summary()
```

## Best Practices Summary

1. **Always use async/await** for I/O operations
2. **Handle exceptions properly** with try/except blocks
3. **Use connection pooling** for network operations
4. **Implement proper cleanup** with context managers
5. **Test concurrent behavior** not just functionality
6. **Monitor performance** to ensure improvements
7. **Document async interfaces** clearly
8. **Maintain compatibility** during migration
9. **Use type hints** for async functions
10. **Avoid blocking operations** in async code

## Further Reading

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [aiohttp documentation](https://docs.aiohttp.org/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Async best practices](https://github.com/python/asyncio/wiki/Best-Practices)