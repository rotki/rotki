# Gevent to Asyncio Migration Strategy

## Overview
This document outlines the strategy for migrating rotki from gevent to asyncio, addressing issue #10090.

## Motivation
- **SQLite issues**: Complex callback mechanism required for context switching
- **Threading incompatibility**: Gevent doesn't work well with native threads
- **Monkey patching**: Global modifications create unpredictable behavior
- **Maintenance**: Gevent-dependent packages are becoming unmaintained (e.g., gevent-websocket)
- **Python ecosystem**: Asyncio is the standard for async programming in modern Python

## Migration Phases

### Phase 1: Foundation (High Priority)
1. **Replace SQLite driver**
   - Current: Custom gevent driver with progress callbacks
   - Target: Use `aiosqlite` for async SQLite operations
   - Challenge: Rewrite connection pooling and transaction management

2. **Create compatibility layer**
   - Build adapters to allow gradual migration
   - Maintain backward compatibility during transition

### Phase 2: Core Infrastructure (Medium Priority)
1. **Replace GreenletManager**
   - Create `AsyncTaskManager` using asyncio tasks
   - Migrate task spawning, tracking, and cancellation

2. **Update web framework**
   - Option A: Migrate Flask to async views (Flask 2.0+)
   - Option B: Switch to FastAPI or Starlette
   - Replace gevent-websocket with websockets or python-socketio

3. **Convert concurrency primitives**
   - Replace gevent.Lock with asyncio.Lock
   - Replace gevent.Event with asyncio.Event
   - Update all semaphore usage

### Phase 3: Business Logic (Low Priority)
1. **Migrate periodic tasks**
   - Convert blockchain sync tasks
   - Update price query tasks
   - Migrate exchange API calls

2. **Update test infrastructure**
   - Replace pytestgeventwrapper.py
   - Use pytest-asyncio for async tests
   - Update test fixtures

3. **Remove monkey patching**
   - Update entry points
   - Remove gevent imports
   - Clean up compatibility code

## Technical Considerations

### Database Layer
The most complex migration is the SQLite driver. Current implementation uses:
```python
# Current gevent approach
def _progress_callback(connection):
    with connection.in_callback:
        gevent.sleep(0)  # Yield to other greenlets
```

Target implementation with aiosqlite:
```python
# Asyncio approach
async def execute_query(query):
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(query) as cursor:
            return await cursor.fetchall()
```

### WebSocket Migration
Current: `gevent-websocket` (abandoned)
Options:
1. `websockets` - Pure asyncio WebSocket client/server
2. `python-socketio` - Higher-level with fallback support
3. `fastapi` + WebSockets - If switching frameworks

### Task Management
```python
# Current
greenlet = self.greenlet_manager.spawn(task_function, *args)

# Target
task = asyncio.create_task(task_function(*args))
```

## Migration Order
1. Start with isolated components (easier to test)
2. Create feature flags for gradual rollout
3. Maintain both implementations temporarily
4. Migrate one subsystem at a time
5. Extensive testing at each step

## Risk Mitigation
- **Parallel implementation**: Keep gevent code until asyncio is stable
- **Feature flags**: Allow switching between implementations
- **Comprehensive testing**: Add integration tests for async code
- **Gradual rollout**: Start with non-critical paths
- **Performance monitoring**: Ensure no regression

## Success Criteria
- All tests pass with asyncio
- No performance regression
- Simplified codebase
- Better error handling
- Improved developer experience

## Timeline Estimate
- Phase 1: 2-3 weeks
- Phase 2: 3-4 weeks  
- Phase 3: 2-3 weeks
- Testing & stabilization: 2 weeks

Total: 9-12 weeks for complete migration