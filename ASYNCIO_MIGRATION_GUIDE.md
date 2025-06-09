# AsyncIO Migration Guide

This guide helps developers migrate code from gevent to asyncio during the transition period.

## Quick Reference

### WebSocket Broadcasting
```python
# Old (gevent)
rotki_notifier.broadcast(
    message_type=WSMessageType.PROGRESS_UPDATE,
    to_send_data={'status': 'processing'},
)

# New (asyncio) - Use migration bridge
from rotkehlchen.api.websockets.migration import broadcast_ws_message
broadcast_ws_message(
    message_type=WSMessageType.PROGRESS_UPDATE,
    data={'status': 'processing'},
)
```

### Task Spawning
```python
# Old (gevent)
greenlet = self.greenlet_manager.spawn_and_track(
    after_seconds=5.0,
    task_name='query_balances',
    exception_is_error=True,
    method=self.query_balances,
    arg1=value1,
)

# New (asyncio)
task = await self.task_manager.spawn_and_track(
    task_name='query_balances',
    coro=self.query_balances(arg1=value1),
    exception_is_error=True,
    delay=5.0,
)
```

### Database Operations
```python
# Old (gevent)
with self.db.read_ctx() as cursor:
    cursor.execute('SELECT * FROM assets WHERE id = ?', (asset_id,))
    result = cursor.fetchone()

# New (asyncio with sync wrapper) - Same API!
with self.db.read_ctx() as cursor:
    cursor.execute('SELECT * FROM assets WHERE id = ?', (asset_id,))
    result = cursor.fetchone()
```

### HTTP Requests
```python
# Old (gevent + requests)
import requests
response = requests.get(url)

# New (asyncio + httpx)
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

## Migration Patterns

### Converting a Module to Async

1. **Identify async boundaries**
   - Network I/O (HTTP requests, WebSocket messages)
   - Database operations (if using aiosqlite)
   - Task spawning
   - Long-running computations

2. **Start from leaf functions**
   ```python
   # Before
   def fetch_data(url: str) -> dict:
       response = requests.get(url)
       return response.json()
   
   # After
   async def fetch_data(url: str) -> dict:
       async with httpx.AsyncClient() as client:
           response = await client.get(url)
           return response.json()
   ```

3. **Propagate async up the call chain**
   ```python
   # Before
   def process_asset(asset_id: str) -> Asset:
       data = fetch_data(f'/api/assets/{asset_id}')
       return Asset(**data)
   
   # After
   async def process_asset(asset_id: str) -> Asset:
       data = await fetch_data(f'/api/assets/{asset_id}')
       return Asset(**data)
   ```

### Using Migration Bridges

The migration bridges allow running both sync and async code during transition:

```python
# WebSocket bridge
from rotkehlchen.api.websockets.migration import ws_migration_bridge

# Enable async mode when ready
ws_migration_bridge.enable_async_mode()

# Task manager bridge  
from rotkehlchen.tasks.async_manager import TaskManagerMigrationBridge

task_manager = TaskManagerMigrationBridge(msg_aggregator)
# Works with both sync and async methods
task_manager.spawn_and_track(...)
```

### Testing Async Code

```python
import pytest

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected

# Use async fixtures
@pytest.fixture
async def async_client():
    async with httpx.AsyncClient() as client:
        yield client
```

## Common Pitfalls

### 1. Mixing Sync and Async
```python
# WRONG - Can't call async from sync directly
def sync_function():
    result = async_function()  # This won't work!
    
# RIGHT - Use asyncio.run() or event loop
def sync_function():
    result = asyncio.run(async_function())
```

### 2. Forgetting await
```python
# WRONG - Returns coroutine object
async def process():
    data = fetch_data()  # Missing await!
    
# RIGHT
async def process():
    data = await fetch_data()
```

### 3. Database Transactions
```python
# Be careful with async context managers
async with db.write_ctx() as cursor:
    await cursor.execute(...)
    # Don't do blocking I/O here!
    # Don't call sync functions that might block!
```

## Feature Flags

During migration, use feature flags to toggle between implementations:

```python
# In config
ASYNC_WEBSOCKETS_ENABLED = os.getenv('ASYNC_WEBSOCKETS', 'false').lower() == 'true'

# In code
if ASYNC_WEBSOCKETS_ENABLED:
    ws_migration_bridge.enable_async_mode()
```

## Gradual Migration Steps

1. **Phase 1**: Infrastructure (✓ Complete)
   - AsyncRotkiNotifier
   - AsyncTaskManager  
   - SQLCipher sync wrapper

2. **Phase 2**: WebSockets (In Progress)
   - Replace gevent-websocket
   - Update WebSocket handlers
   - Test with frontend

3. **Phase 3**: Web Framework
   - Migrate endpoints to FastAPI
   - Update middleware
   - Convert request handlers

4. **Phase 4**: Background Tasks
   - Convert periodic tasks
   - Update blockchain queries
   - Migrate exchange integrations

5. **Phase 5**: Cleanup
   - Remove gevent dependencies
   - Remove migration bridges
   - Update documentation

## Performance Considerations

- **Thread Pool**: SQLCipher operations run in thread pool (1 thread per connection)
- **Connection Pooling**: Consider implementing for better performance
- **Batch Operations**: Group async operations with `asyncio.gather()`
- **Timeouts**: Always use timeouts for network operations

## Getting Help

- Check existing async implementations in `api/websockets/async_notifier.py`
- Look at tests in `tests/test_async_*.py` for examples
- Use type hints to catch async/sync mismatches
- Run `mypy` to verify async annotations