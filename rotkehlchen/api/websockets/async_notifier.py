"""Asyncio-based WebSocket notifier using websockets library"""
import asyncio
import json
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import websockets
from websockets.server import WebSocketServerProtocol

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.serialize import process_result

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncRotkiNotifier:
    """Async WebSocket notification manager using websockets library"""

    def __init__(self) -> None:
        self.subscribers: set[WebSocketServerProtocol] = set()
        # Lock per connection for thread-safe operations
        self.locks: dict[WebSocketServerProtocol, asyncio.Lock] = {}

    async def subscribe(self, websocket: WebSocketServerProtocol) -> None:
        """Add a new WebSocket connection to subscribers"""
        log.info(f'Websocket with hash id {hash(websocket)} subscribed to rotki notifier')
        self.subscribers.add(websocket)
        self.locks[websocket] = asyncio.Lock()

    async def unsubscribe(self, websocket: WebSocketServerProtocol) -> None:
        """Remove a WebSocket connection from subscribers"""
        self.locks.pop(websocket, None)
        self.subscribers.discard(websocket)
        log.info(f'Websocket with hash id {hash(websocket)} unsubscribed from rotki notifier')

    async def _send_to_websocket(
            self,
            websocket: WebSocketServerProtocol,
            message: str,
            success_callback: Callable | None = None,
            success_callback_args: dict[str, Any] | None = None,
            failure_callback: Callable | None = None,
            failure_callback_args: dict[str, Any] | None = None,
    ) -> bool:
        """Send message to a single websocket with error handling
        
        Returns True if successful, False otherwise
        """
        try:
            async with self.locks[websocket]:
                await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            log.debug(f'Websocket {hash(websocket)} closed during send')
            if failure_callback:
                failure_callback_args = failure_callback_args or {}
                failure_callback(**failure_callback_args)
            return False
        except Exception as e:
            log.error(f'Websocket send with message {message} failed due to {e!s}')
            if failure_callback:
                failure_callback_args = failure_callback_args or {}
                failure_callback(**failure_callback_args)
            return False

        if success_callback:
            success_callback_args = success_callback_args or {}
            success_callback(**success_callback_args)
        return True

    async def broadcast(
            self,
            message_type: 'WSMessageType',
            to_send_data: dict[str, Any] | list[Any],
            success_callback: Callable | None = None,
            success_callback_args: dict[str, Any] | None = None,
            failure_callback: Callable | None = None,
            failure_callback_args: dict[str, Any] | None = None,
    ) -> None:
        """Broadcasts a websocket message to all subscribers
        
        A callback to run on message success and a callback to run on message
        failure can be optionally provided.
        """
        message_data = process_result({'type': message_type, 'data': to_send_data})
        try:
            message = json.dumps(message_data)
        except TypeError as e:
            log.error(f'Failed to broadcast websocket {message_type} message due to {e!s}')
            if failure_callback is not None:
                failure_callback_args = failure_callback_args or {}
                failure_callback(**failure_callback_args)
            return

        # Collect closed connections to remove after iteration
        closed_websockets = set()
        tasks = []
        
        for websocket in self.subscribers.copy():
            if websocket.closed:
                closed_websockets.add(websocket)
                continue
            
            # Create task for each send operation
            task = self._send_to_websocket(
                websocket=websocket,
                message=message,
                success_callback=success_callback,
                success_callback_args=success_callback_args,
                failure_callback=failure_callback,
                failure_callback_args=failure_callback_args,
            )
            tasks.append(task)

        # Remove closed connections
        for websocket in closed_websockets:
            await self.unsubscribe(websocket)

        # Execute all sends concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Check if at least one succeeded
            if not any(r is True for r in results if not isinstance(r, Exception)):
                if failure_callback is not None:
                    failure_callback_args = failure_callback_args or {}
                    failure_callback(**failure_callback_args)
        elif failure_callback is not None:
            # No subscribers or all were closed
            failure_callback_args = failure_callback_args or {}
            failure_callback(**failure_callback_args)


class AsyncRotkiWSHandler:
    """WebSocket connection handler for the async implementation"""
    
    def __init__(self, notifier: AsyncRotkiNotifier):
        self.notifier = notifier
    
    async def handle_connection(
            self,
            websocket: WebSocketServerProtocol,
            path: str,
    ) -> None:
        """Handle a WebSocket connection lifecycle"""
        # Subscribe on connection
        await self.notifier.subscribe(websocket)
        
        try:
            # Keep connection alive and handle any incoming messages
            async for message in websocket:
                # Echo back any messages (matches current behavior)
                # In the current implementation, on_message just echoes back
                if websocket in self.notifier.locks:
                    async with self.notifier.locks[websocket]:
                        if not websocket.closed:
                            try:
                                await websocket.send(message)
                            except websockets.exceptions.ConnectionClosed:
                                log.warning(
                                    f'Got ConnectionClosed for sending message {message} to a websocket',
                                )
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Unsubscribe on close
            await self.notifier.unsubscribe(websocket)


# Compatibility layer for gradual migration
class WebSocketCompatibilityWrapper:
    """Wraps the async notifier to provide sync-like interface during migration"""
    
    def __init__(self, async_notifier: AsyncRotkiNotifier, loop: asyncio.AbstractEventLoop):
        self.async_notifier = async_notifier
        self.loop = loop
    
    def broadcast(self, *args, **kwargs) -> None:
        """Sync wrapper for broadcast method"""
        # Schedule the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(
            self.async_notifier.broadcast(*args, **kwargs),
            self.loop
        )
        # Don't wait for result to maintain non-blocking behavior
        # This matches gevent's fire-and-forget pattern