# Remaining Gevent Usage in Rotki Codebase

## Summary

After searching the codebase, here are the main areas where gevent is still actively used:

## 1. Core Server and Initialization
- **`rotkehlchen/__main__.py`**: Monkey patches all modules at startup
- **`rotkehlchen/server.py`**: Uses gevent Event and signal handling
- **`rotkehlchen/api/server.py`**: Uses gevent WSGI server and WebSocket handler
- **`rotkehlchen_mock/__main__.py`**: Also uses monkey patching

## 2. Greenlet Management
- **`rotkehlchen/greenlets/manager.py`**: Core greenlet management system
- **`rotkehlchen/greenlets/utils.py`**: Greenlet utilities
- **`rotkehlchen/tasks/manager.py`**: Task management system built on greenlets

## 3. WebSocket System
- **`rotkehlchen/api/websockets/ws_app.py`**: Uses geventwebsocket
- WebSocket notifications still rely on gevent

## 4. Database Layer
- **`rotkehlchen/db/drivers/gevent.py`**: Gevent-based database driver (being replaced)
- Various DB operations still use gevent locks

## 5. Compatibility Layer
- **`rotkehlchen/utils/gevent_compat.py`**: Compatibility layer for migration (already created)

## 6. External Tools
- **`tools/assets_database/main.py`**: Uses monkey patching
- **`tools/profiling/cpu.py`**: Profiling tools use gevent

## 7. Core Components Using Gevent Primitives
- **`rotkehlchen/rotkehlchen.py`**: Main app class uses gevent.Event, spawn
- **`rotkehlchen/chain/aggregator.py`**: Chain aggregator spawns greenlets
- **`rotkehlchen/accounting/accountant.py`**: Accounting system uses greenlets
- **`rotkehlchen/tasks/unified.py`**: Unified task system
- **`rotkehlchen/premium/sync.py`**: Premium sync uses greenlets
- **`rotkehlchen/globaldb/handler.py`**: Global DB handler uses locks
- **`rotkehlchen/api/rest.py`**: REST API uses greenlets for background tasks

## 8. Exchange Integrations
Many exchange classes use threading.Lock() which gets monkey-patched:
- binance.py, bitfinex.py, kraken.py, coinbase.py, etc.

## 9. Chain/Blockchain Modules
- Various node inquirers spawn greenlets for concurrent operations
- EVM transaction decoding uses greenlets
- Substrate manager uses greenlets

## 10. Miscellaneous
- Icon manager uses greenlets
- History manager uses greenlets for querying
- Various imports and exception handling for GreenletKilledError

## Migration Strategy

The main areas to focus on for removing gevent:

1. **Replace monkey patching** in `__main__.py` - This is critical
2. **Convert GreenletManager** to AsyncTaskManager
3. **Replace gevent WSGI server** with an ASGI server (uvicorn/hypercorn)
4. **Convert WebSocket system** to use async WebSockets
5. **Update all spawn() calls** to use asyncio.create_task()
6. **Replace gevent.Event/Lock/Semaphore** with asyncio equivalents
7. **Update signal handling** to use asyncio-compatible methods
8. **Convert all greenlet-based concurrent operations** to async/await

The compatibility layer in `gevent_compat.py` helps during the transition, but ultimately all imports should be updated to use asyncio directly.