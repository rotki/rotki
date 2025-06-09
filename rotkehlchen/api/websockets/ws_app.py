"""Unified WebSocket application for migration period

This module provides a WebSocket app that works with both sync and async implementations.
"""
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from geventwebsocket import WebSocketApplication
from geventwebsocket.exceptions import WebSocketError

from rotkehlchen.api.feature_flags import AsyncFeature, async_features
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
    from rotkehlchen.api.websockets.notifier import RotkiNotifier

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UnifiedWSApp(WebSocketApplication):
    """WebSocket app that works with both sync and async notifiers"""

    def on_open(self, *args: Any, **kwargs: Any) -> None:
        """Handle WebSocket connection open"""
        if async_features.is_enabled(AsyncFeature.WEBSOCKETS):
            # Async notifier handles connections differently
            # It's managed by the AsyncRotkiNotifier
            pass
        else:
            # Use sync notifier
            rotki_notifier: 'RotkiNotifier' = self.ws.environ['rotki_notifier']
            rotki_notifier.subscribe(self.ws)

    def on_message(self, message: str | None, *args: Any, **kwargs: Any) -> None:
        """Handle incoming WebSocket message"""
        if async_features.is_enabled(AsyncFeature.WEBSOCKETS):
            # Async notifier handles messages differently
            pass
        else:
            # Use sync notifier
            if self.ws.environ is not None and (rotki_notifier := self.ws.environ.get('rotki_notifier')) and self.ws in rotki_notifier.locks:
                lock = rotki_notifier.locks[self.ws]
            else:  # can happen only when shutting down
                lock = contextlib.nullcontext()

            with lock:
                if self.ws.closed:
                    return
                try:
                    self.ws.send(message, **kwargs)
                except WebSocketError as e:
                    log.warning(
                        f'Got WebSocketError {e!s} for sending message {message} to a websocket',
                    )

    def on_close(self, *args: Any, **kwargs: Any) -> None:
        """Handle WebSocket connection close"""
        if async_features.is_enabled(AsyncFeature.WEBSOCKETS):
            # Async notifier handles disconnections differently
            pass
        else:
            # Use sync notifier
            if self.ws.environ is not None:
                rotki_notifier: 'RotkiNotifier' = self.ws.environ['rotki_notifier']
                rotki_notifier.unsubscribe(self.ws)


# Export as RotkiWSApp for backward compatibility
RotkiWSApp = UnifiedWSApp