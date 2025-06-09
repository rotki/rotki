"""Unified WebSocket interface for migration period

This module provides a single interface that automatically uses the
appropriate implementation based on feature flags.
"""
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.api.feature_flags import AsyncFeature, async_features
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.migration import ws_migration_bridge
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.api.websockets.typedefs import WSMessageType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UnifiedWSNotifier:
    """Unified WebSocket notifier that uses appropriate implementation"""
    
    def __init__(self):
        # Check if async WebSockets are enabled
        self.use_async = async_features.is_enabled(AsyncFeature.WEBSOCKETS)
        
        if self.use_async:
            log.info("Using async WebSocket implementation")
            ws_migration_bridge.enable_async_mode()
            self._impl = ws_migration_bridge.async_notifier
        else:
            log.info("Using sync (gevent) WebSocket implementation")
            self._impl = ws_migration_bridge.sync_notifier
            
    def broadcast(
        self,
        message_type: 'WSMessageType',
        to_send_data: dict[str, Any] | list[Any],
        **kwargs,
    ) -> None:
        """Broadcast message using appropriate implementation"""
        ws_migration_bridge.broadcast(message_type, to_send_data, **kwargs)
        
    def get_implementation(self) -> RotkiNotifier | AsyncRotkiNotifier:
        """Get the underlying implementation"""
        return self._impl
        
    @property
    def is_async(self) -> bool:
        """Check if using async implementation"""
        return self.use_async


def create_ws_notifier() -> RotkiNotifier | AsyncRotkiNotifier:
    """Factory function to create appropriate WebSocket notifier"""
    if async_features.is_enabled(AsyncFeature.WEBSOCKETS):
        log.info("Creating AsyncRotkiNotifier")
        return AsyncRotkiNotifier()
    else:
        log.info("Creating RotkiNotifier (gevent)")
        return RotkiNotifier()