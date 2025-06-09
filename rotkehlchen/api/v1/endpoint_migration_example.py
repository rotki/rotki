"""Example of migrating endpoints from Flask to FastAPI

This file demonstrates how to migrate real endpoints while maintaining
API compatibility and gradual migration capabilities.
"""
import asyncio
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from flask import Response

from rotkehlchen.api.rest import RestAPI, api_response, process_result
from rotkehlchen.api.v1.schemas_fastapi import (
    SettingsModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter

import logging
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Original Flask implementation (for reference)
class FlaskSettingsResource:
    """Original Flask implementation of settings endpoint"""
    
    def __init__(self, rest_api: RestAPI):
        self.rest_api = rest_api
        
    def get(self) -> Response:
        """Flask GET /api/1/settings"""
        with self.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = process_result(self.rest_api.rotkehlchen.get_settings(cursor))
            cache = self.rest_api.rotkehlchen.data.db.get_cache_for_api(cursor)
        result_dict = {'result': settings | cache, 'message': ''}
        return api_response(result=result_dict, status_code=HTTPStatus.OK)


# New FastAPI implementation
class AsyncSettingsEndpoint:
    """FastAPI implementation of settings endpoint with async support"""
    
    def __init__(self):
        self.router = APIRouter()
        self._setup_routes()
        
    def _setup_routes(self):
        self.router.add_api_route(
            "/settings",
            self.get_settings,
            methods=["GET"],
            response_model=dict,
            summary="Get application settings",
            description="Returns all user settings and cached values",
        )
        
    async def get_settings(self, rest_api: RestAPI = Depends(lambda: None)) -> dict:
        """FastAPI GET /api/1/settings
        
        This demonstrates several migration patterns:
        1. Running sync database operations in thread pool
        2. Maintaining response format compatibility
        3. Error handling that matches Flask behavior
        """
        try:
            # Run sync database operations in thread pool
            loop = asyncio.get_event_loop()
            
            def _get_settings_sync():
                with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
                    settings = process_result(rest_api.rotkehlchen.get_settings(cursor))
                    cache = rest_api.rotkehlchen.data.db.get_cache_for_api(cursor)
                return settings | cache
            
            # Execute in thread pool to avoid blocking
            result = await loop.run_in_executor(None, _get_settings_sync)
            
            # Return in same format as Flask for compatibility
            return create_success_response(result)
            
        except Exception as e:
            log.error(f"Error getting settings: {e}")
            # Match Flask error response format
            return create_error_response(str(e), HTTPStatus.INTERNAL_SERVER_ERROR.value)


# Migration wrapper that supports both implementations
class SettingsMigrationWrapper:
    """Allows gradual migration from Flask to FastAPI
    
    This wrapper can serve both implementations based on configuration,
    allowing A/B testing and gradual rollout.
    """
    
    def __init__(self, rest_api: RestAPI, use_async: bool = False):
        self.rest_api = rest_api
        self.use_async = use_async
        self.flask_impl = FlaskSettingsResource(rest_api)
        self.async_impl = AsyncSettingsEndpoint()
        
    def handle_request(self, request_type: str = "GET") -> Any:
        """Route request to appropriate implementation"""
        if self.use_async:
            # In production, this would be handled by FastAPI routing
            return self.async_impl.router
        else:
            # Use Flask implementation
            if request_type == "GET":
                return self.flask_impl.get()
            raise ValueError(f"Unsupported request type: {request_type}")


# More complex example: Async query endpoint
class AsyncQueryEndpoint:
    """Example of converting an async query endpoint"""
    
    def __init__(self):
        self.router = APIRouter()
        self._setup_routes()
        
    def _setup_routes(self):
        self.router.add_api_route(
            "/history/events",
            self.query_history_events,
            methods=["POST"],
            summary="Query history events",
            description="Query history events with optional async processing",
        )
    
    async def query_history_events(
        self,
        async_query: bool = False,
        filters: dict | None = None,
        rest_api: RestAPI = Depends(lambda: None),
    ) -> dict:
        """Demonstrates async query pattern migration"""
        
        if async_query:
            # Start async task using new task manager
            from rotkehlchen.tasks.async_manager import AsyncTaskManager
            
            task_manager: AsyncTaskManager = rest_api.rotkehlchen.task_manager
            
            async def _query_task():
                # Simulate long-running query
                await asyncio.sleep(2.0)
                return {"events": [], "total": 0}
            
            task = await task_manager.spawn_and_track(
                task_name="query_history_events",
                coro=_query_task(),
                exception_is_error=True,
            )
            
            # Return task ID for status checking
            return create_success_response({
                "task_id": id(task),
                "status": "pending",
            })
        
        # Synchronous query
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: {"events": [], "total": 0}  # Placeholder
        )
        
        return create_success_response(result)


# Performance comparison utilities
class EndpointPerformanceMonitor:
    """Monitor performance during migration to ensure no regression"""
    
    def __init__(self):
        self.metrics = {
            "flask": {"count": 0, "total_time": 0.0},
            "fastapi": {"count": 0, "total_time": 0.0},
        }
    
    async def measure_endpoint(self, impl_type: str, endpoint_func):
        """Measure endpoint performance"""
        import time
        
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(endpoint_func):
                result = await endpoint_func()
            else:
                result = endpoint_func()
        finally:
            duration = time.time() - start
            self.metrics[impl_type]["count"] += 1
            self.metrics[impl_type]["total_time"] += duration
        
        return result
    
    def get_comparison(self) -> dict:
        """Get performance comparison between implementations"""
        comparison = {}
        for impl_type, metrics in self.metrics.items():
            if metrics["count"] > 0:
                avg_time = metrics["total_time"] / metrics["count"]
                comparison[impl_type] = {
                    "avg_response_time": avg_time,
                    "total_requests": metrics["count"],
                }
        return comparison


# Migration checklist for endpoints
"""
Endpoint Migration Checklist:

1. [ ] Identify endpoint dependencies
   - Database operations
   - External API calls
   - Background tasks
   - WebSocket notifications

2. [ ] Create Pydantic models for request/response
   - Match existing schema exactly
   - Add validation where appropriate

3. [ ] Implement async version
   - Use thread pool for sync operations
   - Convert I/O operations to async where possible
   - Maintain error handling behavior

4. [ ] Test compatibility
   - Response format matches exactly
   - Error responses are consistent
   - Status codes are preserved

5. [ ] Performance testing
   - No regression in response times
   - Memory usage is acceptable
   - Concurrent request handling improves

6. [ ] Update documentation
   - OpenAPI schema is accurate
   - Migration notes added

7. [ ] Feature flag integration
   - Can toggle between implementations
   - Metrics collection enabled

8. [ ] Gradual rollout
   - Start with read-only endpoints
   - Monitor error rates
   - Collect user feedback
"""


# Example usage
async def migration_example():
    """Demonstrate endpoint migration"""
    
    # Mock RestAPI
    class MockRestAPI:
        class Rotkehlchen:
            class Data:
                class DB:
                    class Conn:
                        @staticmethod
                        def read_ctx():
                            from contextlib import contextmanager
                            @contextmanager
                            def ctx():
                                yield None
                            return ctx()
                    conn = Conn()
                db = DB()
            
            data = Data()
            
            @staticmethod
            def get_settings(cursor):
                return {"main_currency": "USD", "version": "1.35.0"}
        
        rotkehlchen = Rotkehlchen()
    
    rest_api = MockRestAPI()
    
    # Test Flask implementation
    flask_endpoint = FlaskSettingsResource(rest_api)
    flask_response = flask_endpoint.get()
    print(f"Flask response: {flask_response}")
    
    # Test FastAPI implementation
    async_endpoint = AsyncSettingsEndpoint()
    # Inject dependency
    async_endpoint.get_settings.__wrapped__.__defaults__ = (rest_api,)
    fastapi_response = await async_endpoint.get_settings()
    print(f"FastAPI response: {fastapi_response}")
    
    # Performance comparison
    monitor = EndpointPerformanceMonitor()
    
    # Measure Flask
    await monitor.measure_endpoint("flask", flask_endpoint.get)
    
    # Measure FastAPI
    await monitor.measure_endpoint("fastapi", async_endpoint.get_settings)
    
    print(f"Performance comparison: {monitor.get_comparison()}")


if __name__ == "__main__":
    asyncio.run(migration_example())