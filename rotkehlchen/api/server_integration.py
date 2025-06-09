"""Integration module to run Flask and FastAPI side by side during migration

This module allows gradual migration from Flask/WSGI to FastAPI/ASGI by
running both servers together with shared state.
"""
import asyncio
import logging
import threading
from typing import Any

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.server_async import RotkiASGIServer, set_global_dependencies
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier, WebSocketCompatibilityWrapper
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.gevent_compat import spawn

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HybridAPIServer:
    """Runs Flask and FastAPI servers together during migration period
    
    This allows:
    1. Existing Flask endpoints to continue working
    2. New FastAPI endpoints to be added gradually
    3. Shared WebSocket notification between both
    4. Eventual complete migration to FastAPI
    """
    
    def __init__(
        self,
        rest_api: RestAPI,
        cors_domain_list: list[str] | None = None,
        use_async_websockets: bool = False,
    ) -> None:
        self.rest_api = rest_api
        self.cors_domain_list = cors_domain_list
        self.use_async_websockets = use_async_websockets
        
        # Create appropriate WebSocket notifier
        if use_async_websockets:
            # Use async WebSocket implementation
            self.async_notifier = AsyncRotkiNotifier()
            # Create event loop for async operations
            self.async_loop = asyncio.new_event_loop()
            self.async_thread = threading.Thread(
                target=self._run_async_loop,
                daemon=True,
            )
            # Wrap for Flask compatibility
            self.flask_notifier = WebSocketCompatibilityWrapper(
                self.async_notifier,
                self.async_loop,
            )
        else:
            # Use existing gevent-based WebSocket
            self.flask_notifier = RotkiNotifier()
            self.async_notifier = None
            self.async_loop = None
            self.async_thread = None
        
        # Create servers
        self.flask_server = APIServer(
            rest_api=rest_api,
            ws_notifier=self.flask_notifier,
            cors_domain_list=cors_domain_list,
        )
        
        # Only create FastAPI server if using async
        self.fastapi_server = None
        if use_async_websockets:
            self.fastapi_server = RotkiASGIServer(
                rest_api=rest_api,
                ws_notifier=self.async_notifier,
                cors_domain_list=cors_domain_list,
            )
            # Set up dependency injection
            set_global_dependencies(rest_api, self.async_notifier)
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in a separate thread"""
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()
    
    def start(
        self,
        host: str = '127.0.0.1',
        rest_port: int = 5042,
        fastapi_port: int | None = None,
    ) -> None:
        """Start both servers
        
        Args:
            host: Host to bind to
            rest_port: Port for Flask server
            fastapi_port: Port for FastAPI server (if None, uses rest_port + 1)
        """
        if self.use_async_websockets and self.async_thread:
            # Start async event loop thread
            self.async_thread.start()
        
        # Determine FastAPI port
        if fastapi_port is None:
            fastapi_port = rest_port + 1
        
        # Start FastAPI server in a greenlet if enabled
        if self.fastapi_server and self.use_async_websockets:
            def run_fastapi():
                try:
                    import uvicorn
                    # Run in the existing async loop
                    asyncio.run_coroutine_threadsafe(
                        self._run_fastapi_server(host, fastapi_port),
                        self.async_loop,
                    ).result()
                except Exception as e:
                    log.error(f"Failed to start FastAPI server: {e}")
            
            spawn(run_fastapi)
            log.info(f"FastAPI server starting on {host}:{fastapi_port}")
        
        # Start Flask server (this blocks)
        log.info(f"Flask server starting on {host}:{rest_port}")
        self.flask_server.start(host=host, rest_port=rest_port)
    
    async def _run_fastapi_server(self, host: str, port: int) -> None:
        """Run FastAPI server asynchronously"""
        import uvicorn
        
        config = uvicorn.Config(
            app=self.fastapi_server.app,
            host=host,
            port=port,
            log_level="info",
            access_log=False,
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def stop(self, timeout: int = 5) -> None:
        """Stop both servers"""
        # Stop Flask server
        if self.flask_server:
            self.flask_server.stop(timeout=timeout)
        
        # Stop async loop if running
        if self.async_loop and self.async_loop.is_running():
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)
            if self.async_thread and self.async_thread.is_alive():
                self.async_thread.join(timeout=timeout)
        
        log.info("All servers stopped")


def create_api_server(
    rest_api: RestAPI,
    cors_domain_list: list[str] | None = None,
    use_hybrid_mode: bool = False,
    use_async_websockets: bool = False,
) -> APIServer | HybridAPIServer:
    """Factory function to create appropriate API server
    
    Args:
        rest_api: The REST API instance
        cors_domain_list: CORS allowed domains
        use_hybrid_mode: If True, run both Flask and FastAPI
        use_async_websockets: If True, use async WebSocket implementation
        
    Returns:
        Either Flask-only server or hybrid server
    """
    if use_hybrid_mode:
        return HybridAPIServer(
            rest_api=rest_api,
            cors_domain_list=cors_domain_list,
            use_async_websockets=use_async_websockets,
        )
    else:
        # Traditional Flask-only server
        ws_notifier = RotkiNotifier()
        return APIServer(
            rest_api=rest_api,
            ws_notifier=ws_notifier,
            cors_domain_list=cors_domain_list,
        )