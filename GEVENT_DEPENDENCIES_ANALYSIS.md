# Gevent Dependencies Analysis

## Direct Dependencies

### Core Packages
1. **gevent==25.4.2**
   - Main async framework
   - Provides greenlets, monkey patching, and event loop
   - Used throughout the codebase

2. **greenlet==3.2.3**
   - Low-level greenlet implementation
   - Required by gevent
   - Direct usage in GreenletManager

3. **gevent-websocket==0.10.1** ⚠️ ABANDONED
   - WebSocket server for gevent
   - Last updated in 2017
   - Used in API WebSocket implementation

4. **wsaccel==0.6.7** ⚠️ ABANDONED  
   - WebSocket acceleration for gevent-websocket
   - Optional performance enhancement
   - Also abandoned

## Replacement Strategy

### 1. Core Async Framework
**Current**: gevent + greenlet  
**Replacement**: Built-in asyncio (Python 3.11+)
- No external dependencies needed
- Standard library solution
- Better ecosystem support

### 2. WebSocket Support
**Current**: gevent-websocket + wsaccel  
**Replacement Options**:
- **websockets** - Pure Python asyncio WebSocket implementation
- **python-socketio** - Higher-level with Socket.IO protocol
- **FastAPI WebSockets** - If migrating to FastAPI

### 3. Database Async Support
**Current**: Custom gevent SQLite driver  
**Replacement**: 
- **aiosqlite** - Async SQLite for asyncio
- Well-maintained and actively developed

## Indirect Dependencies
No other packages in requirements.txt appear to depend on gevent directly.

## Migration Impact

### High Impact Areas
1. **WebSocket server** - Complete replacement needed
2. **Database driver** - Custom implementation must be rewritten
3. **Task management** - All greenlet spawning code

### Medium Impact Areas
1. **HTTP server** - Flask integration with gevent
2. **Concurrent operations** - Exchange queries, blockchain sync
3. **Lock mechanisms** - All gevent locks/events

### Low Impact Areas
1. **Tests** - Need new test runner
2. **Entry points** - Remove monkey patching

## Recommended Replacements

```txt
# Remove from requirements.txt
- gevent==25.4.2
- greenlet==3.2.3  
- gevent-websocket==0.10.1
- wsaccel==0.6.7

# Add to requirements.txt
+ aiosqlite==0.20.0  # For async SQLite
+ websockets==13.1   # For WebSocket support
+ pytest-asyncio==0.24.0  # For async tests (dev dependency)
```

## Notes
- Both WebSocket packages are abandoned, making migration urgent
- No complex dependency chains to worry about
- Clean separation makes migration easier