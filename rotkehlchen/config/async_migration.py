"""Configuration for asyncio migration

This module contains feature flags and configuration for the gradual
migration from gevent to asyncio.
"""
import os
from enum import Enum


class AsyncMode(Enum):
    """Async implementation mode"""
    GEVENT = "gevent"
    ASYNCIO = "asyncio"
    HYBRID = "hybrid"  # Run both in parallel during migration


class AsyncMigrationConfig:
    """Configuration for async migration"""
    
    def __init__(self):
        # Read from environment or config file
        mode_str = os.getenv('ROTKI_ASYNC_MODE', 'gevent').lower()
        self.mode = AsyncMode(mode_str)
        
        # Feature flags for gradual migration
        self.features = {
            'websockets': os.getenv('ASYNC_WEBSOCKETS', 'false').lower() == 'true',
            'task_manager': os.getenv('ASYNC_TASK_MANAGER', 'false').lower() == 'true',
            'database': os.getenv('ASYNC_DATABASE', 'false').lower() == 'true',
            'web_framework': os.getenv('ASYNC_WEB_FRAMEWORK', 'false').lower() == 'true',
            'exchanges': os.getenv('ASYNC_EXCHANGES', 'false').lower() == 'true',
        }
    
    @property
    def use_async_websockets(self) -> bool:
        """Should use async WebSocket implementation"""
        return self.mode != AsyncMode.GEVENT and self.features['websockets']
    
    @property
    def use_async_tasks(self) -> bool:
        """Should use async task manager"""
        return self.mode != AsyncMode.GEVENT and self.features['task_manager']
    
    @property
    def use_async_database(self) -> bool:
        """Should use async database driver"""
        return self.mode != AsyncMode.GEVENT and self.features['database']
    
    @property
    def use_fastapi(self) -> bool:
        """Should use FastAPI instead of Flask"""
        return self.mode != AsyncMode.GEVENT and self.features['web_framework']
    
    @property
    def use_async_exchanges(self) -> bool:
        """Should use async exchange implementations"""
        return self.mode != AsyncMode.GEVENT and self.features['exchanges']
    
    def enable_all_async(self):
        """Enable all async features (for testing)"""
        self.mode = AsyncMode.ASYNCIO
        for key in self.features:
            self.features[key] = True
    
    def disable_all_async(self):
        """Disable all async features (fallback to gevent)"""
        self.mode = AsyncMode.GEVENT
        for key in self.features:
            self.features[key] = False


# Global configuration instance
async_config = AsyncMigrationConfig()


def requires_async_mode(feature: str):
    """Decorator to check if async mode is enabled for a feature"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not async_config.features.get(feature, False):
                raise RuntimeError(f"Async {feature} is not enabled. Set ASYNC_{feature.upper()}=true")
            return func(*args, **kwargs)
        return wrapper
    return decorator