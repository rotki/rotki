# Remove Gevent - AsyncIO Migration Foundation

## Summary
This PR lays the foundation for migrating rotki from gevent to asyncio, addressing issue #10090. It provides all the necessary components for a gradual, risk-free migration while maintaining full backward compatibility.

## Motivation
- **Abandoned dependencies**: gevent-websocket and wsaccel are unmaintained
- **SQLite hack**: gevent requires complex progress handler callbacks for context switching
- **Better ecosystem**: asyncio is standard Python with better tooling and libraries
- **Threading issues**: gevent's monkey patching causes problems with native threads

## What's Implemented

### 1. Core Components ✅
- **AsyncRotkiNotifier**: WebSocket server using `websockets` library
- **AsyncTaskManager**: Native asyncio task management replacing GreenletManager  
- **Async SQLite drivers**: Clean implementation without progress handler hacks
- **FastAPI integration**: Modern async web framework to replace Flask

### 2. Migration Tools ✅
- **Compatibility bridges**: Allow running sync/async code side-by-side
- **Feature flags**: Gradual rollout capability
- **Performance benchmarking**: Ensure no regression
- **Integration tests**: Validate mixed operation

### 3. Documentation ✅
- Comprehensive migration strategy
- Developer guide with examples
- Deployment procedures
- Performance comparison tools

## Key Technical Achievement

### Eliminating the Progress Handler Hack

**Before (gevent):**
```python
def _progress_callback(connection):
    # Complex hack to force context switching
    with connection.in_callback:
        gevent.sleep(0)
    return 0

conn.set_progress_handler(callback, 100)  # Called every 100 VM instructions
```

**After (asyncio):**
```python
# Natural async/await - no hacks needed
async with db.read_ctx() as cursor:
    await cursor.execute(query)  # Yields naturally
```

## Files Changed

### Core Implementation
- `api/websockets/async_notifier.py` - Async WebSocket implementation
- `tasks/async_manager.py` - Async task manager
- `db/drivers/asyncio_sqlite.py` - Clean async SQLite driver
- `db/drivers/sqlcipher_sync.py` - Thread pool wrapper for SQLCipher
- `api/async_server.py` - FastAPI server
- `api/flask_fastapi_bridge.py` - Compatibility layer

### Migration Support
- `api/websockets/migration.py` - WebSocket migration bridge
- `api/v1/schemas_fastapi.py` - Pydantic schemas
- `api/v1/resources_fastapi.py` - Example FastAPI endpoints
- `api/v1/endpoint_migration_example.py` - Migration patterns

### Testing & Documentation
- `tests/test_async_migration.py` - Comprehensive test suite
- `tests/test_flask_fastapi_integration.py` - Integration tests
- `examples/async_migration_example.py` - Working examples
- `scripts/benchmark_async_migration.py` - Performance tools
- Multiple documentation files

## Migration Plan

### Phase 1: Foundation (This PR) ✅
- Core async components
- Migration tooling
- Documentation

### Phase 2: Pilot Migration 
- Migrate simple endpoints (/ping, /info)
- Test in production with feature flags
- Gather performance data

### Phase 3: Gradual Rollout
- Migrate endpoints module by module
- Monitor performance and errors
- Update based on feedback

### Phase 4: Completion
- Remove gevent dependencies
- Clean up migration bridges
- Update all documentation

## Testing
- ✅ Unit tests for all async components
- ✅ Integration tests for mixed Flask/FastAPI
- ✅ Performance benchmarking tools
- ✅ Examples demonstrating usage

## Breaking Changes
None - all changes are backward compatible with gradual migration support.

## Dependencies
Added (will replace gevent dependencies after migration):
- websockets==13.1
- aiosqlite==0.20.0  
- fastapi==0.115.5
- uvicorn==0.32.1
- httpx==0.28.1
- pytest-asyncio==0.24.0

## Checklist
- [x] Code follows project style guidelines
- [x] Tests pass
- [x] Documentation updated
- [x] No breaking changes
- [x] Performance impact assessed
- [x] Migration path documented

## Next Steps
1. Review and merge this foundation
2. Start pilot migration with simple endpoints
3. Monitor and iterate based on results
4. Gradually expand migration scope

## Related Issues
Closes #10090 (when fully migrated)