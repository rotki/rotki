"""Configuration for asyncio

This module contains configuration for asyncio-based operations.
"""
import os


class AsyncMigrationConfig:
    """Configuration for async operations"""
    
    def __init__(self):
        # All features now use asyncio by default
        self.features = {
            'websockets': True,
            'task_manager': True,
            'database': True,
            'web_framework': True,
            'exchanges': True,
            'blockchain': True,
            'premium': True,
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if an async feature is enabled"""
        return self.features.get(feature, True)
    
    def enable_all(self) -> None:
        """Enable all async features"""
        for key in self.features:
            self.features[key] = True
    
    def disable_all(self) -> None:
        """Disable all async features"""
        for key in self.features:
            self.features[key] = False


# Global configuration instance
async_config = AsyncMigrationConfig()