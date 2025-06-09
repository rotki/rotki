"""WebSocket migration utilities for transitioning from gevent to asyncio"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WebSocketMigrationBridge:
    """Bridge between sync (gevent) and async (asyncio) WebSocket implementations
    
    This allows gradual migration by providing both interfaces during transition.
    """
    
    def __init__(self):
        # Create both notifiers
        self.sync_notifier = RotkiNotifier()
        self.async_notifier = AsyncRotkiNotifier()
        
        # Event loop for async operations
        self.loop: asyncio.AbstractEventLoop | None = None
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ws-bridge')
        
        # Flag to determine which implementation to use
        self.use_async = False
        
    def start_async_loop(self) -> None:
        """Start the asyncio event loop in a separate thread"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
            
        self.executor.submit(run_loop)
        
        # Wait for loop to be ready
        while self.loop is None:
            import time
            time.sleep(0.01)
    
    def stop_async_loop(self) -> None:
        """Stop the asyncio event loop"""
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.executor.shutdown(wait=True)
    
    def broadcast(
            self,
            message_type: 'WSMessageType',
            to_send_data: dict[str, Any] | list[Any],
            **kwargs,
    ) -> None:
        """Broadcast message using appropriate implementation"""
        if self.use_async and self.loop:
            # Schedule async broadcast in the event loop
            future = asyncio.run_coroutine_threadsafe(
                self.async_notifier.broadcast(message_type, to_send_data, **kwargs),
                self.loop
            )
            # Don't wait for result to maintain non-blocking behavior
        else:
            # Use sync implementation
            self.sync_notifier.broadcast(message_type, to_send_data, **kwargs)
    
    def get_notifier(self) -> RotkiNotifier | AsyncRotkiNotifier:
        """Get the active notifier based on configuration"""
        return self.async_notifier if self.use_async else self.sync_notifier
    
    def enable_async_mode(self) -> None:
        """Switch to async WebSocket implementation"""
        log.info("Enabling async WebSocket mode")
        self.use_async = True
        if not self.loop:
            self.start_async_loop()
    
    def disable_async_mode(self) -> None:
        """Switch back to sync WebSocket implementation"""
        log.info("Disabling async WebSocket mode")
        self.use_async = False


# Global instance for easy access during migration
ws_migration_bridge = WebSocketMigrationBridge()


def get_ws_notifier() -> RotkiNotifier | AsyncRotkiNotifier:
    """Get the current WebSocket notifier"""
    return ws_migration_bridge.get_notifier()


def broadcast_ws_message(
        message_type: 'WSMessageType',
        data: dict[str, Any] | list[Any],
        **kwargs,
) -> None:
    """Broadcast a WebSocket message using the current implementation"""
    ws_migration_bridge.broadcast(message_type, data, **kwargs)