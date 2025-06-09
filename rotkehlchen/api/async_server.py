"""AsyncIO-based API server using FastAPI"""
import asyncio
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from rotkehlchen.api.flask_fastapi_bridge import FlaskFastAPIBridge
from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.resources_fastapi import router as v1_router
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncAPIServer:
    """FastAPI-based async API server to replace Flask/gevent implementation"""
    
    _api_prefix = '/api/1'
    
    def __init__(
            self,
            rest_api: RestAPI,
            ws_notifier: RotkiNotifier | AsyncRotkiNotifier,
            cors_domain_list: list[str] | None = None,
    ) -> None:
        self.rest_api = rest_api
        self.app = FastAPI(title="Rotki API", version="1.0.0")
        
        # Setup async notifier
        if isinstance(ws_notifier, RotkiNotifier):
            # During migration, wrap the sync notifier
            self.async_notifier = AsyncRotkiNotifier()
            self.sync_notifier = ws_notifier
        else:
            self.async_notifier = ws_notifier
            self.sync_notifier = None
        
        # Setup CORS
        if cors_domain_list:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_domain_list,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Setup middleware
        self.app.middleware("http")(self.log_requests)
        
        # Setup WebSocket endpoint
        self.app.websocket("/ws")(self.websocket_endpoint)
        
        # Include FastAPI router
        self.app.include_router(v1_router)
        
        # Inject RestAPI dependency
        self.app.dependency_overrides[self._get_rest_api] = lambda: self.rest_api
        
        # Setup routes
        self._setup_routes()
        
        self.server = None
        
    async def log_requests(self, request: Request, call_next):
        """Log all requests and responses"""
        # Log request
        log.debug(
            f'start rotki api {request.method} {request.url.path}',
            query_params=dict(request.query_params),
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        log.debug(
            f'end rotki api {request.method} {request.url.path}',
            status_code=response.status_code,
        )
        
        return response
    
    @staticmethod
    def _get_rest_api() -> RestAPI:
        """Dependency injection placeholder"""
        raise NotImplementedError("Should be overridden")
    
    def _setup_routes(self):
        """Setup API routes (placeholder for migration)"""
        # Routes are now in resources_fastapi.py via router
        pass
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """Handle WebSocket connections"""
        await websocket.accept()
        
        # Convert FastAPI WebSocket to websockets protocol for compatibility
        # This is a simplified adapter - full implementation would handle all methods
        class WebSocketAdapter:
            def __init__(self, fastapi_ws: WebSocket):
                self.ws = fastapi_ws
                self.closed = False
                
            async def send(self, message: str):
                if not self.closed:
                    await self.ws.send_text(message)
                    
            async def close(self):
                self.closed = True
                await self.ws.close()
        
        adapter = WebSocketAdapter(websocket)
        await self.async_notifier.subscribe(adapter)
        
        try:
            while True:
                # Handle incoming messages (echo them back as per current behavior)
                message = await websocket.receive_text()
                if adapter in self.async_notifier.locks:
                    async with self.async_notifier.locks[adapter]:
                        if not adapter.closed:
                            try:
                                await adapter.send(message)
                            except Exception as e:
                                log.warning(
                                    f'Got exception {e} for sending message {message} to a websocket',
                                )
        except WebSocketDisconnect:
            pass
        finally:
            await self.async_notifier.unsubscribe(adapter)
    
    async def start(
            self,
            host: str = '127.0.0.1',
            rest_port: int = 5042,
    ) -> None:
        """Start the async API server"""
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=rest_port,
            log_level="info",
            access_log=False,  # We handle logging ourselves
        )
        self.server = uvicorn.Server(config)
        await self.server.serve()
    
    async def stop(self) -> None:
        """Stop the async API server"""
        if self.server:
            await self.server.shutdown()


# Migration helpers to run FastAPI alongside Flask
class MigrationAPIServer:
    """Temporary server that runs both Flask and FastAPI during migration"""
    
    def __init__(
            self,
            flask_server: 'APIServer',  # The existing Flask server
            fastapi_server: AsyncAPIServer,
    ):
        self.flask_server = flask_server
        self.fastapi_server = fastapi_server
        self.loop = None
        
    def start(self, host: str = '127.0.0.1', rest_port: int = 5042) -> None:
        """Start both servers during migration"""
        # For now, just start Flask server
        # In next phase, we'll run FastAPI on different port
        # Then gradually migrate endpoints
        self.flask_server.start(host, rest_port)
        
        # Future: Run FastAPI in thread with event loop
        # self.loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(self.loop)
        # self.loop.run_until_complete(
        #     self.fastapi_server.start(host, rest_port + 1)
        # )