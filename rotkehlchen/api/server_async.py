"""FastAPI-based ASGI server for rotki

This is the async replacement for the Flask/WSGI server.
It uses FastAPI with uvicorn for high-performance async operation.
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocket

from rotkehlchen.api.rest import RestAPI, wrap_in_fail_result
from rotkehlchen.api.v1.schemas_fastapi import create_error_response
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier, AsyncRotkiWSHandler
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.version_check import get_current_version

# Import all async route modules
from rotkehlchen.api.v1.async_transactions import router as transactions_router
from rotkehlchen.api.v1.async_base import router as base_router
from rotkehlchen.api.v1.async_balances import router as balances_router
from rotkehlchen.api.v1.async_exchanges import router as exchanges_router
from rotkehlchen.api.v1.async_assets_extended import router as assets_extended_router
from rotkehlchen.api.v1.async_users import router as users_router
from rotkehlchen.api.v1.async_database import router as database_router
from rotkehlchen.api.v1.async_statistics import router as statistics_router
from rotkehlchen.api.v1.async_history import router as history_router
from rotkehlchen.api.v1.async_accounting import router as accounting_router
from rotkehlchen.api.v1.async_blockchain import router as blockchain_router
from rotkehlchen.api.v1.async_nfts import router as nfts_router
from rotkehlchen.api.v1.async_eth2 import router as eth2_router
from rotkehlchen.api.v1.async_defi import router as defi_router
from rotkehlchen.api.v1.async_utils import router as utils_router
from rotkehlchen.api.v1.async_addressbook import router as addressbook_router
from rotkehlchen.api.v1.async_calendar import router as calendar_router
from rotkehlchen.api.v1.async_spam import router as spam_router
from rotkehlchen.api.v1.async_misc import router as misc_router

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkiASGIServer:
    """FastAPI-based ASGI server for rotki"""
    
    def __init__(
        self,
        rest_api: RestAPI,
        ws_notifier: AsyncRotkiNotifier,
        cors_domain_list: list[str] | None = None,
    ) -> None:
        self.rest_api = rest_api
        self.ws_notifier = ws_notifier
        self.ws_handler = AsyncRotkiWSHandler(ws_notifier)
        
        # Create FastAPI app with lifespan management
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            log.info(f'Starting rotki ASGI server {get_current_version().our_version}')
            yield
            # Shutdown
            log.info('Stopping rotki ASGI server')
            self.rest_api.stop()
        
        self.app = FastAPI(
            title="rotki API",
            version=get_current_version().our_version,
            lifespan=lifespan,
            docs_url="/api/1/docs",
            redoc_url="/api/1/redoc",
            openapi_url="/api/1/openapi.json",
        )
        
        # Configure CORS
        if cors_domain_list:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_domain_list,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Add exception handlers
        self.app.add_exception_handler(StarletteHTTPException, self.http_exception_handler)
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_exception_handler(Exception, self.general_exception_handler)
        
        # Add middleware for logging
        self.app.middleware("http")(self.log_requests)
        
        # Include routers
        self._setup_routes()
        
        # WebSocket endpoint
        self.app.websocket("/ws")(self.websocket_endpoint)
        
    def _setup_routes(self) -> None:
        """Setup all API routes"""
        # Include async routers as they become available
        self.app.include_router(base_router)
        self.app.include_router(transactions_router)
        self.app.include_router(balances_router)
        self.app.include_router(exchanges_router)
        self.app.include_router(assets_extended_router)
        self.app.include_router(users_router)
        self.app.include_router(database_router)
        self.app.include_router(statistics_router)
        self.app.include_router(history_router)
        self.app.include_router(accounting_router)
        self.app.include_router(blockchain_router)
        self.app.include_router(nfts_router)
        self.app.include_router(eth2_router)
        self.app.include_router(defi_router)
        self.app.include_router(utils_router)
        self.app.include_router(addressbook_router)
        self.app.include_router(calendar_router)
        self.app.include_router(spam_router)
        self.app.include_router(misc_router)
        
        # TODO: As we migrate endpoints to FastAPI, include their routers here
        
        # For now, we can also mount the Flask app for non-migrated endpoints
        # This allows gradual migration
        # from fastapi.middleware.wsgi import WSGIMiddleware
        # self.app.mount("/api/1", WSGIMiddleware(flask_app))
    
    async def websocket_endpoint(self, websocket: WebSocket) -> None:
        """Handle WebSocket connections"""
        await websocket.accept()
        await self.ws_handler.handle_connection(websocket, str(websocket.url.path))
    
    async def log_requests(self, request: Request, call_next):
        """Middleware to log all requests"""
        # Log request
        log.debug(
            f'start rotki api {request.method} {request.url.path}',
            query_params=dict(request.query_params),
            headers=dict(request.headers),
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        log.debug(
            f'end rotki api {request.method} {request.url.path}',
            status_code=response.status_code,
        )
        
        return response
    
    async def http_exception_handler(self, request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(exc.detail),
        )
    
    async def validation_exception_handler(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors"""
        # Format validation errors
        errors = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error["loc"])
            errors.append(f"{loc}: {error['msg']}")
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(", ".join(errors)),
        )
    
    async def general_exception_handler(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions"""
        if __debug__:
            logger.exception(exc)
        log.critical(
            'Unhandled exception when processing endpoint request',
            exc_info=True,
            exception=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(str(exc)),
        )
    
    def run(self, host: str = '127.0.0.1', port: int = 5042) -> None:
        """Run the server using uvicorn
        
        This is the main entry point for production use.
        """
        import uvicorn
        
        log_level = "debug" if __debug__ else "info"
        
        if 'pytest' not in sys.modules:
            if __debug__:
                msg = 'rotki is running in __debug__ mode'
                print(msg)
                log.info(msg)
            log.info(f'Starting rotki {get_current_version().our_version}')
            msg = f'rotki REST API server is running at: {host}:{port} with loglevel {logging.getLevelName(logging.root.level)}'
            print(msg)
            log.info(msg)
        
        # Run with uvicorn
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=False,  # We handle logging ourselves
            lifespan="on",
        )


# Dependency injection helpers that will be overridden by the app
_rest_api_instance: RestAPI | None = None
_ws_notifier_instance: AsyncRotkiNotifier | None = None


def set_global_dependencies(rest_api: RestAPI, ws_notifier: AsyncRotkiNotifier) -> None:
    """Set global instances for dependency injection"""
    global _rest_api_instance, _ws_notifier_instance
    _rest_api_instance = rest_api
    _ws_notifier_instance = ws_notifier


async def get_rest_api() -> RestAPI:
    """Dependency to get RestAPI instance"""
    if _rest_api_instance is None:
        raise RuntimeError("RestAPI not initialized")
    return _rest_api_instance


async def get_ws_notifier() -> AsyncRotkiNotifier:
    """Dependency to get WebSocket notifier"""
    if _ws_notifier_instance is None:
        raise RuntimeError("WebSocket notifier not initialized") 
    return _ws_notifier_instance


# Override the dependency in the routers
from rotkehlchen.api.v1 import (
    async_transactions, async_base, async_balances, async_exchanges,
    async_assets_extended, async_users, async_database,
    async_statistics, async_history, async_accounting,
    async_blockchain, async_nfts, async_eth2, async_defi, async_utils,
    async_addressbook, async_calendar, async_spam, async_misc
)

# Set up dependency injection for all routers
for module in [
    async_transactions, async_base, async_balances, async_exchanges,
    async_assets_extended, async_users, async_database,
    async_statistics, async_history, async_accounting,
    async_blockchain, async_nfts, async_eth2, async_defi, async_utils,
    async_addressbook, async_calendar, async_spam, async_misc
]:
    module.get_rest_api = get_rest_api

# Special dependencies for transactions
async_transactions.get_task_manager = lambda: _rest_api_instance.rotkehlchen.task_manager if _rest_api_instance else None
async_transactions.get_async_db = lambda: _rest_api_instance.rotkehlchen.data.db if _rest_api_instance else None