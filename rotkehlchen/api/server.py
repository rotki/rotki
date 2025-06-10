"""FastAPI-based ASGI server for rotki

This is the async replacement for the Flask/WSGI server.
It uses FastAPI with uvicorn for high-performance async operation.
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocket

from rotkehlchen.api.v1.accounting import router as accounting_router
from rotkehlchen.api.v1.addressbook import router as addressbook_router
from rotkehlchen.api.v1.assets_extended import router as assets_extended_router
from rotkehlchen.api.v1.balances import router as balances_router
from rotkehlchen.api.v1.base import router as base_router
from rotkehlchen.api.v1.blockchain import router as blockchain_router
from rotkehlchen.api.v1.calendar import router as calendar_router
from rotkehlchen.api.v1.database import router as database_router
from rotkehlchen.api.v1.defi import router as defi_router
from rotkehlchen.api.v1.eth2 import router as eth2_router
from rotkehlchen.api.v1.exchanges import router as exchanges_router
from rotkehlchen.api.v1.history import router as history_router
from rotkehlchen.api.v1.misc import router as misc_router
from rotkehlchen.api.v1.nfts import router as nfts_router
from rotkehlchen.api.v1.spam import router as spam_router
from rotkehlchen.api.v1.statistics import router as statistics_router

# Import all route modules
from rotkehlchen.api.v1.transactions import router as transactions_router
from rotkehlchen.api.v1.users import router as users_router
from rotkehlchen.api.v1.utils import router as utils_router
from rotkehlchen.api.v1.dependencies import set_rotkehlchen_instance
from rotkehlchen.api.v1.schemas_fastapi import create_error_response
from rotkehlchen.api.websockets.notifier import RotkiNotifier, RotkiWSHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.version_check import get_current_version

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class APIServer:
    """FastAPI-based ASGI server for rotki"""

    def __init__(
        self,
        rotkehlchen: 'Rotkehlchen',
        cors_domain_list: list[str] | None = None,
    ) -> None:

        self.rotkehlchen = rotkehlchen
        self.rest_api = self  # Backward compatibility
        self.ws_notifier = RotkiNotifier()
        self.ws_handler = RotkiWSHandler(self.ws_notifier)
        self.rest_port = None  # Will be set when started
        self.version = '1'  # API version

        # Set up dependency injection for FastAPI endpoints
        set_rotkehlchen_instance(rotkehlchen)

        # Create FastAPI app with lifespan management
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            log.info(f'Starting rotki ASGI server {get_current_version().our_version}')
            yield
            # Shutdown
            log.info('Stopping rotki ASGI server')
            self.rotkehlchen.shutdown()

        self.app = FastAPI(
            title='rotki API',
            version=get_current_version().our_version,
            lifespan=lifespan,
            docs_url='/api/1/docs',
            redoc_url='/api/1/redoc',
            openapi_url='/api/1/openapi.json',
        )

        # Configure CORS
        if cors_domain_list:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_domain_list,
                allow_credentials=True,
                allow_methods=['*'],
                allow_headers=['*'],
            )

        # Add exception handlers
        self.app.add_exception_handler(StarletteHTTPException, self.http_exception_handler)
        self.app.add_exception_handler(RequestValidationError, self.validation_exception_handler)
        self.app.add_exception_handler(Exception, self.general_exception_handler)

        # Add middleware for logging
        self.app.middleware('http')(self.log_requests)

        # Include routers
        self._setup_routes()

        # WebSocket endpoint
        self.app.websocket('/ws')(self.websocket_endpoint)

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
            loc = ' -> '.join(str(l) for l in error['loc'])
            errors.append(f"{loc}: {error['msg']}")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(', '.join(errors)),
        )

    async def general_exception_handler(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions"""
        if __debug__:
            logger.error(exc)
        log.critical(
            'Unhandled exception when processing endpoint request',
            exception=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(str(exc)),
        )

    def start(self, host: str = '127.0.0.1', rest_port: int = 5042) -> None:
        """Start the server for tests - non-blocking"""
        self.rest_port = rest_port
        # For tests, we don't actually start the server here
        # The test framework will handle running the app
        
    def stop(self) -> None:
        """Stop the server for tests"""
        # Cleanup if needed
        pass

    def run(self, host: str = '127.0.0.1', port: int = 5042) -> None:
        """Run the server using uvicorn

        This is the main entry point for production use.
        """
        import uvicorn

        log_level = 'debug' if __debug__ else 'info'

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
            lifespan='on',
        )

