# AsyncIO Replacement Libraries Evaluation

## 1. WebSocket Libraries

### Current: gevent-websocket (ABANDONED)
- Last update: 2017
- No asyncio support
- Security vulnerabilities

### Option A: websockets
**Pros:**
- Pure Python, asyncio-native
- Well maintained (15k+ stars)
- Simple API
- Good performance

**Cons:**
- Server-only, need separate client library
- No Socket.IO protocol support

**Example:**
```python
import websockets

async def handler(websocket, path):
    async for message in websocket:
        await websocket.send(f"Echo: {message}")

start_server = websockets.serve(handler, "localhost", 8765)
```

### Option B: python-socketio
**Pros:**
- Socket.IO protocol (fallback support)
- Works with multiple async frameworks
- Client and server in one package
- Room/namespace support

**Cons:**
- Heavier than pure WebSocket
- More complex API

**Example:**
```python
import socketio

sio = socketio.AsyncServer(async_mode='aiohttp')

@sio.event
async def message(sid, data):
    await sio.emit('reply', data, room=sid)
```

### Option C: aiohttp with WebSockets
**Pros:**
- Part of aiohttp ecosystem
- Good if migrating to aiohttp
- Battle-tested

**Cons:**
- Requires full aiohttp adoption
- More setup code

**Recommendation:** Start with `websockets` for simplicity, consider `python-socketio` if we need Socket.IO features.

## 2. Web Framework Options

### Current: Flask + gevent
- Synchronous by design
- Async support is limited

### Option A: Flask with async views (Flask 2.0+)
**Pros:**
- Minimal code changes
- Familiar API
- Can mix sync/async views

**Cons:**
- Not fully async
- Still uses WSGI
- Limited async ecosystem

**Example:**
```python
@app.route('/async')
async def async_route():
    await some_async_operation()
    return jsonify({"status": "ok"})
```

### Option B: FastAPI
**Pros:**
- Async-first design
- Automatic API documentation
- Type hints for validation
- WebSocket support built-in
- Modern Python features

**Cons:**
- Complete rewrite needed
- Different middleware system
- Learning curve

**Example:**
```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    item = await get_item(item_id)
    return {"item": item}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello")
```

### Option C: Starlette
**Pros:**
- Lightweight ASGI framework
- FastAPI is built on it
- Simpler than FastAPI
- Good middle ground

**Cons:**
- Less features than FastAPI
- Smaller ecosystem

### Option D: Quart
**Pros:**
- Flask-compatible API
- Drop-in replacement
- Async version of Flask

**Cons:**
- Smaller community
- Less mature

**Recommendation:** Start with Quart for easier migration, consider FastAPI for long-term.

## 3. Database Libraries

### For SQLite: aiosqlite
**Pros:**
- Drop-in asyncio SQLite
- Well maintained
- Compatible API

**Cons:**
- No built-in pooling
- Uses thread pool internally

### For SQLCipher: Custom Solution Needed

**Option A: Thread Pool Wrapper**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pysqlcipher3 import dbapi2

class AsyncSQLCipher:
    def __init__(self, path: str):
        self.path = path
        self.executor = ThreadPoolExecutor(max_workers=1)
        
    async def execute(self, query: str, params=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._execute_sync, 
            query, 
            params
        )
```

**Option B: asyncpg + pgcrypto**
- Switch to PostgreSQL with encryption
- Native async support
- Better performance

**Option C: Sync regions**
- Keep SQLCipher operations synchronous
- Use async for everything else

**Recommendation:** Start with thread pool wrapper, evaluate PostgreSQL for v2.

## 4. Task Management

### Current: GreenletManager
### Replacement: Native asyncio.TaskGroup (Python 3.11+)

**Example:**
```python
import asyncio

class AsyncTaskManager:
    def __init__(self):
        self.tasks: set[asyncio.Task] = set()
        
    async def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task
        
    async def shutdown(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
```

## 5. Testing Libraries

### Current: pytest with gevent wrapper
### Replacement: pytest-asyncio

**Example:**
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected
```

## Migration Priority

1. **WebSockets** - Use `websockets` library
2. **Web Framework** - Start with Quart (Flask-compatible)
3. **Task Manager** - Native asyncio
4. **Database** - Thread pool wrapper for SQLCipher
5. **Testing** - pytest-asyncio

## Implementation Strategy

### Phase 1: WebSocket Migration (Week 1-2)
- Replace gevent-websocket with websockets
- Update WebSocket handlers
- Test real-time features

### Phase 2: Web Framework (Week 3-4)
- Install Quart alongside Flask
- Migrate endpoints gradually
- Update middleware

### Phase 3: Task Management (Week 5-6)
- Replace GreenletManager
- Update background tasks
- Convert periodic tasks

### Phase 4: Database Layer (Week 7-9)
- Implement thread pool wrapper
- Migrate read operations
- Update write operations

### Phase 5: Testing & Cleanup (Week 10-12)
- Update test infrastructure
- Remove gevent dependencies
- Performance testing