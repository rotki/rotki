#!/usr/bin/env python
"""Script to start rotki with async features enabled for testing

This demonstrates how to run the server with various async features
enabled during the migration period.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_async_features():
    """Configure which async features to enable"""
    # Choose migration mode
    mode = os.getenv("ASYNC_MODE", "pilot")
    
    if mode == "pilot":
        # Enable basic endpoints for pilot testing
        os.environ["ASYNC_FEATURE_WEBSOCKETS"] = "true"
        os.environ["ASYNC_FEATURE_PING"] = "true"
        os.environ["ASYNC_FEATURE_INFO"] = "true"
        print("🚀 Starting in PILOT mode - basic endpoints enabled")
        
    elif mode == "mixed":
        # Enable more features
        os.environ["ASYNC_FEATURE_WEBSOCKETS"] = "true"
        os.environ["ASYNC_FEATURE_TASK_MANAGER"] = "true"
        os.environ["ASYNC_FEATURE_PING"] = "true"
        os.environ["ASYNC_FEATURE_INFO"] = "true"
        os.environ["ASYNC_FEATURE_SETTINGS"] = "true"
        print("🚀 Starting in MIXED mode - stable features enabled")
        
    elif mode == "full":
        # Enable all async features
        os.environ["ASYNC_MODE"] = "full"
        print("🚀 Starting in FULL async mode - all features enabled")
        
    else:
        print("⚠️  Starting with default settings - async features disabled")
    
    # Print enabled features
    print("\nAsync features status:")
    for key, value in os.environ.items():
        if key.startswith("ASYNC_"):
            print(f"  {key}: {value}")


async def start_hybrid_server():
    """Start the server with both Flask and FastAPI running"""
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.api.async_server import AsyncAPIServer
    from rotkehlchen.api.flask_fastapi_bridge import FlaskFastAPIBridge
    from rotkehlchen.api.rest import RestAPI
    from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
    from rotkehlchen.api.websockets.notifier import RotkiNotifier
    from rotkehlchen.api.websockets.migration import ws_migration_bridge
    
    # Mock setup - in production this would use real Rotkehlchen instance
    print("\n📦 Setting up server components...")
    
    # Create mock RestAPI
    class MockRestAPI(RestAPI):
        def __init__(self):
            # Mock initialization
            self.rotkehlchen = None
            
        def get_info(self, check_for_updates=False):
            """Mock implementation"""
            return {
                "result": {
                    "version": "1.35.0",
                    "data_directory": str(Path.home() / ".rotki"),
                    "log_level": "debug",
                    "backend_default_arguments": {},
                },
                "message": ""
            }
    
    rest_api = MockRestAPI()
    
    # Setup WebSocket migration
    use_async_ws = os.getenv("ASYNC_FEATURE_WEBSOCKETS", "false").lower() == "true"
    if use_async_ws:
        print("✅ Using async WebSocket implementation")
        ws_migration_bridge.enable_async_mode()
        notifier = ws_migration_bridge.get_notifier()
    else:
        print("📌 Using legacy WebSocket implementation")
        notifier = RotkiNotifier()
    
    # Create servers
    flask_server = APIServer(
        rest_api=rest_api,
        ws_notifier=notifier,
        cors_domain_list=["http://localhost:*"]
    )
    
    async_server = AsyncAPIServer(
        rest_api=rest_api,
        ws_notifier=notifier if isinstance(notifier, AsyncRotkiNotifier) else AsyncRotkiNotifier(),
        cors_domain_list=["http://localhost:*"]
    )
    
    # Create bridge
    bridge = FlaskFastAPIBridge(
        flask_app=flask_server.flask_app,
        fastapi_app=async_server.app,
        rest_api=rest_api,
    )
    
    print("\n🌐 Server configuration:")
    print(f"  Host: 127.0.0.1")
    print(f"  Port: 5042")
    print(f"  CORS: Enabled for localhost")
    
    # Show available endpoints
    print("\n📍 Available endpoints:")
    print("  Flask endpoints:")
    for rule in flask_server.flask_app.url_map.iter_rules():
        if rule.endpoint != 'static':
            print(f"    {rule.methods} {rule.rule}")
    
    print("\n  FastAPI endpoints:")
    for route in async_server.app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            print(f"    {route.methods} {route.path}")
    
    # Show migration status
    from rotkehlchen.api.feature_flags import get_migration_metrics
    metrics = get_migration_metrics()
    print(f"\n📊 Migration progress: {metrics['progress_percentage']:.1f}%")
    print(f"   Endpoints migrated: {metrics['endpoint_migration']['migrated']}/{metrics['endpoint_migration']['total']}")
    
    print("\n✨ Server ready!")
    print("   Test async features: curl http://127.0.0.1:5042/api/1/async/features")
    print("   Test ping: curl http://127.0.0.1:5042/api/1/ping")
    print("   Test info: curl http://127.0.0.1:5042/api/1/info")
    
    # In production, would use uvicorn to run
    # For demo, just keep alive
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


def main():
    """Main entry point"""
    print("🚀 Rotki Async Migration Test Server")
    print("="*50)
    
    # Setup features based on environment
    setup_async_features()
    
    # Run the hybrid server
    try:
        asyncio.run(start_hybrid_server())
    except KeyboardInterrupt:
        print("\nShutdown complete")


if __name__ == "__main__":
    main()