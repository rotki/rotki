"""Bridge layer to run Flask and FastAPI together during migration"""
import asyncio
import logging
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request as FastAPIRequest
from flask import Flask, Request as FlaskRequest, Response as FlaskResponse
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.responses import Response as StarletteResponse

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class FlaskFastAPIBridge:
    """Allows running Flask and FastAPI together with shared context"""
    
    def __init__(
            self,
            flask_app: Flask,
            fastapi_app: FastAPI,
            rest_api: RestAPI,
    ):
        self.flask_app = flask_app
        self.fastapi_app = fastapi_app
        self.rest_api = rest_api
        
        # Mount Flask app as WSGI middleware for non-migrated routes
        self.flask_middleware = WSGIMiddleware(flask_app)
        
        # Track which routes are migrated to FastAPI
        self.migrated_routes: set[str] = set()
        
        # Setup routing logic
        self._setup_routing()
    
    def _setup_routing(self):
        """Setup smart routing between Flask and FastAPI"""
        
        @self.fastapi_app.middleware("http")
        async def route_middleware(request: FastAPIRequest, call_next):
            # Check if this route is migrated to FastAPI
            path = request.url.path
            
            # Let FastAPI handle its registered routes
            for route in self.fastapi_app.routes:
                if hasattr(route, 'path') and route.path == path:
                    response = await call_next(request)
                    return response
            
            # WebSocket routes always go to FastAPI
            if path == "/ws":
                response = await call_next(request)
                return response
            
            # All other routes go to Flask
            response = await self.flask_middleware(request.scope, request.receive, request._send)
            return response
    
    def mark_route_migrated(self, path: str):
        """Mark a route as migrated to FastAPI"""
        self.migrated_routes.add(path)
        log.info(f"Route {path} migrated to FastAPI")
    
    def get_app(self) -> FastAPI:
        """Get the combined application"""
        return self.fastapi_app


def create_rest_api_decorator(rest_api: RestAPI):
    """Create decorator to inject RestAPI into FastAPI endpoints"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Inject rest_api if needed
            if 'rest_api' in func.__code__.co_varnames:
                kwargs['rest_api'] = rest_api
            return await func(*args, **kwargs)
        
        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


class ResponseAdapter:
    """Adapt Flask responses to FastAPI responses"""
    
    @staticmethod
    def flask_to_fastapi(flask_response: FlaskResponse) -> StarletteResponse:
        """Convert Flask Response to FastAPI Response"""
        return StarletteResponse(
            content=flask_response.get_data(as_text=True),
            status_code=flask_response.status_code,
            headers=dict(flask_response.headers),
            media_type=flask_response.content_type,
        )
    
    @staticmethod
    def adapt_rest_api_method(method: Callable) -> Callable:
        """Adapt a RestAPI method to work with FastAPI"""
        if asyncio.iscoroutinefunction(method):
            return method
        
        async def async_wrapper(*args, **kwargs):
            # Run sync method in thread pool
            loop = asyncio.get_event_loop()
            flask_response = await loop.run_in_executor(None, method, *args, **kwargs)
            return ResponseAdapter.flask_to_fastapi(flask_response)
        
        return async_wrapper


def require_loggedin_user_fastapi():
    """FastAPI version of require_loggedin_user decorator"""
    def decorator(func: Callable) -> Callable:
        async def wrapper(request: FastAPIRequest, *args, **kwargs):
            # Check if user is logged in (adapt from Flask version)
            # This is simplified - real implementation would check session/auth
            if not hasattr(request.state, 'user') or request.state.user is None:
                return StarletteResponse(
                    content='{"result": null, "message": "No user is currently logged in", "error": true}',
                    status_code=401,
                    media_type="application/json"
                )
            return await func(request, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator