"""Feature flag system for gradual asyncio migration"""
import os
from enum import Enum
from typing import Any


class AsyncFeature(Enum):
    """Available async features that can be toggled"""
    WEBSOCKETS = "websockets"
    TASK_MANAGER = "task_manager"
    PING_ENDPOINT = "ping"
    INFO_ENDPOINT = "info"
    SETTINGS_ENDPOINT = "settings"
    DATABASE_ENDPOINTS = "database"
    HISTORY_ENDPOINTS = "history"
    ALL_ENDPOINTS = "all_endpoints"


class FeatureFlags:
    """Manage feature flags for asyncio migration
    
    Features can be enabled via:
    1. Environment variables: ASYNC_FEATURE_<NAME>=true
    2. Configuration file
    3. Runtime API calls
    """
    
    def __init__(self):
        self._flags: dict[AsyncFeature, bool] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load feature flags from environment variables"""
        for feature in AsyncFeature:
            env_var = f"ASYNC_FEATURE_{feature.value.upper()}"
            enabled = os.getenv(env_var, "false").lower() in ("true", "1", "yes")
            self._flags[feature] = enabled
            
        # Special handling for ASYNC_MODE
        async_mode = os.getenv("ASYNC_MODE", "disabled").lower()
        if async_mode == "full":
            # Enable all features
            for feature in AsyncFeature:
                self._flags[feature] = True
        elif async_mode == "mixed":
            # Enable only stable features
            self._flags[AsyncFeature.WEBSOCKETS] = True
            self._flags[AsyncFeature.TASK_MANAGER] = True
            self._flags[AsyncFeature.PING_ENDPOINT] = True
    
    def is_enabled(self, feature: AsyncFeature) -> bool:
        """Check if a feature is enabled"""
        # ALL_ENDPOINTS is a meta-feature
        if feature == AsyncFeature.ALL_ENDPOINTS:
            endpoint_features = [
                AsyncFeature.PING_ENDPOINT,
                AsyncFeature.INFO_ENDPOINT,
                AsyncFeature.SETTINGS_ENDPOINT,
                AsyncFeature.DATABASE_ENDPOINTS,
                AsyncFeature.HISTORY_ENDPOINTS,
            ]
            return all(self._flags.get(f, False) for f in endpoint_features)
        
        return self._flags.get(feature, False)
    
    def enable(self, feature: AsyncFeature):
        """Enable a feature at runtime"""
        self._flags[feature] = True
        
        # If enabling ALL_ENDPOINTS, enable all endpoint features
        if feature == AsyncFeature.ALL_ENDPOINTS:
            for f in AsyncFeature:
                if "endpoint" in f.value.lower():
                    self._flags[f] = True
    
    def disable(self, feature: AsyncFeature):
        """Disable a feature at runtime"""
        self._flags[feature] = False
    
    def get_status(self) -> dict[str, bool]:
        """Get status of all features"""
        return {
            feature.value: self.is_enabled(feature)
            for feature in AsyncFeature
        }
    
    def get_enabled_features(self) -> list[str]:
        """Get list of enabled features"""
        return [
            feature.value
            for feature in AsyncFeature
            if self.is_enabled(feature)
        ]


# Global instance
async_features = FeatureFlags()


def feature_enabled(feature: AsyncFeature):
    """Decorator to conditionally enable async endpoints based on feature flags
    
    Usage:
        @feature_enabled(AsyncFeature.SETTINGS_ENDPOINT)
        async def get_settings():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not async_features.is_enabled(feature):
                # Return None to indicate this endpoint should not be registered
                return None
            return func(*args, **kwargs)
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper._feature_flag = feature
        return wrapper
    
    return decorator


def get_migration_metrics() -> dict[str, Any]:
    """Get metrics about the migration progress"""
    total_features = len(AsyncFeature)
    enabled_features = len(async_features.get_enabled_features())
    
    endpoint_features = [f for f in AsyncFeature if "endpoint" in f.value.lower()]
    enabled_endpoints = sum(1 for f in endpoint_features if async_features.is_enabled(f))
    
    return {
        "total_features": total_features,
        "enabled_features": enabled_features,
        "progress_percentage": (enabled_features / total_features) * 100,
        "endpoint_migration": {
            "total": len(endpoint_features),
            "migrated": enabled_endpoints,
            "percentage": (enabled_endpoints / len(endpoint_features)) * 100 if endpoint_features else 0,
        },
        "status": async_features.get_status(),
    }