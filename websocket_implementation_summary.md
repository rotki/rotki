# WebSocket Implementation in Rotki

## Overview

Rotki uses `gevent-websocket` for WebSocket functionality. The implementation consists of:

1. **WebSocket Server**: Integrated into the main API server using gevent's WSGIServer
2. **WebSocket Notifier**: Central component that manages connections and broadcasts messages
3. **Message Types**: Defined enum for different types of WebSocket messages
4. **Client Management**: Subscription-based model for handling multiple WebSocket connections

## Key Components

### 1. WebSocket Server Initialization (`api/server.py`)

- WebSocket server runs on the same port as the REST API (default: 5042)
- WebSocket endpoint is available at `/ws`
- Uses `WebSocketHandler` from gevent-websocket
- Initialized with:
  ```python
  self.wsgiserver = WSGIServer(
      listener=(host, rest_port),
      application=WebsocketResource([
          ('^/ws', RotkiWSApp),
          ('^/', self.flask_app),
      ]),
      handler_class=WebSocketHandler,
      environ={'rotki_notifier': self.rotki_notifier},
  )
  ```

### 2. RotkiNotifier (`api/websockets/notifier.py`)

Main class that manages WebSocket connections:

- **Subscription Management**:
  - `subscribe(websocket)`: Add a new WebSocket connection
  - `unsubscribe(websocket)`: Remove a WebSocket connection
  - Maintains list of active connections and locks for thread safety

- **Message Broadcasting**:
  - `broadcast(message_type, to_send_data, callbacks)`: Send messages to all connected clients
  - Automatically removes closed connections
  - Supports success/failure callbacks
  - Messages are JSON-encoded

### 3. RotkiWSApp (`api/websockets/notifier.py`)

WebSocket application handler:

- `on_open()`: Called when a client connects, subscribes them to the notifier
- `on_message()`: Handles incoming messages from clients (mainly echoes back)
- `on_close()`: Called when client disconnects, unsubscribes from notifier

### 4. Message Types (`api/websockets/typedefs.py`)

Defined WebSocket message types include:
- `LEGACY`: General messages (warnings/errors)
- `BALANCE_SNAPSHOT_ERROR`
- `EVM_TRANSACTION_STATUS`
- `PREMIUM_STATUS_UPDATE`
- `DB_UPGRADE_STATUS`
- `EVMLIKE_ACCOUNTS_DETECTION`
- `NEW_EVM_TOKEN_DETECTED`
- `DATA_MIGRATION_STATUS`
- `MISSING_API_KEY`
- `HISTORY_EVENTS_STATUS`
- `REFRESH_BALANCES`
- `DATABASE_UPLOAD_RESULT`
- `ACCOUNTING_RULE_CONFLICT`
- `CALENDAR_REMINDER`
- `EXCHANGE_UNKNOWN_ASSET`
- `PROGRESS_UPDATES`
- `GNOSISPAY_SESSIONKEY_EXPIRED`

### 5. Message Aggregator Integration

- `MessagesAggregator` class integrates with the notifier
- Provides methods like `add_warning()`, `add_error()`, and `add_message()`
- Falls back to internal queues if WebSocket is not available

## How Messages are Sent

1. Components call `msg_aggregator.add_message()` with a message type and data
2. The message aggregator forwards to the WebSocket notifier
3. The notifier broadcasts to all connected clients
4. Messages are JSON-encoded with format: `{"type": "<message_type>", "data": <data>}`

## Authentication/Security

- **No explicit authentication** for WebSocket connections
- Security relies on:
  - Running on localhost by default (127.0.0.1)
  - CORS configuration for cross-origin requests
  - Same-origin policy when accessed from web frontend

## Connection Management

- Uses gevent locks (Semaphore) for thread-safe operations
- Automatically cleans up closed connections during broadcast
- No heartbeat/ping-pong mechanism visible in the code

## Configuration

- No separate WebSocket port configuration (uses same port as REST API)
- CORS domains configured via `--api-cors` argument
- Default CORS: `http://localhost:*/*`

## Usage Example (from tests)

```python
ws = create_connection(f'ws://127.0.0.1:{rest_api_port}/ws')
ws.send('{}')  # Subscribe by sending any message
# Receive messages
msg = ws.recv()
data = json.loads(msg)
```

## Key Observations for Migration

1. **Tight Integration**: WebSocket is tightly integrated with gevent's WSGIServer
2. **Simple Protocol**: No complex handshaking or authentication
3. **Broadcast-Only**: Primarily used for server-to-client notifications
4. **Thread Safety**: Uses gevent locks for concurrent access
5. **No Room/Channel Concept**: All clients receive all messages
6. **Fallback Mechanism**: Messages queue internally if WebSocket unavailable

## Potential Replacement Considerations

When replacing gevent-websocket, consider:
1. Maintaining the same WebSocket endpoint (`/ws`)
2. Preserving the message format and types
3. Ensuring thread-safe connection management
4. Supporting the broadcast pattern
5. Integrating with the existing REST API server
6. Handling the gevent/async context appropriately