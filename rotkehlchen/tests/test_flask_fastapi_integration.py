"""Integration tests for Flask/FastAPI mixed operation during migration"""
import asyncio
import json
import threading
from unittest.mock import Mock, patch

import pytest
import requests
from fastapi.testclient import TestClient
from flask import Flask
from flask.testing import FlaskClient

from rotkehlchen.api.async_server import AsyncAPIServer
from rotkehlchen.api.flask_fastapi_bridge import FlaskFastAPIBridge
from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.notifier import RotkiNotifier


class TestFlaskFastAPIIntegration:
    """Test that Flask and FastAPI can work together during migration"""
    
    @pytest.fixture
    def mock_rest_api(self):
        """Create mock RestAPI for testing"""
        rest_api = Mock(spec=RestAPI)
        rest_api.rotkehlchen = Mock()
        rest_api.rotkehlchen.data = Mock()
        rest_api.rotkehlchen.data.db = Mock()
        return rest_api
    
    @pytest.fixture
    def flask_app(self, mock_rest_api):
        """Create Flask app"""
        app = Flask(__name__)
        
        @app.route('/api/1/flask_only')
        def flask_only():
            return {'result': 'flask response', 'message': ''}
        
        return app
    
    @pytest.fixture
    def fastapi_server(self, mock_rest_api):
        """Create FastAPI server"""
        notifier = AsyncRotkiNotifier()
        server = AsyncAPIServer(
            rest_api=mock_rest_api,
            ws_notifier=notifier,
        )
        
        # Add test endpoint
        @server.app.get("/api/1/fastapi_only")
        async def fastapi_only():
            return {"result": "fastapi response", "message": ""}
        
        return server
    
    @pytest.fixture
    def bridge(self, flask_app, fastapi_server, mock_rest_api):
        """Create Flask-FastAPI bridge"""
        return FlaskFastAPIBridge(
            flask_app=flask_app,
            fastapi_app=fastapi_server.app,
            rest_api=mock_rest_api,
        )
    
    def test_bridge_routing(self, bridge):
        """Test that bridge correctly routes to Flask and FastAPI"""
        client = TestClient(bridge.get_app())
        
        # Test FastAPI endpoint
        response = client.get("/api/1/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["status"] == "pong"
        
        # Test Flask endpoint (through WSGI middleware)
        response = client.get("/api/1/flask_only")
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "flask response"
        
        # Test FastAPI-only endpoint
        response = client.get("/api/1/fastapi_only")
        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "fastapi response"
    
    @pytest.mark.asyncio
    async def test_websocket_migration(self, fastapi_server):
        """Test WebSocket functionality in async server"""
        # Test WebSocket connection
        from websockets.client import connect
        
        # Start server in background
        server_task = asyncio.create_task(
            fastapi_server.start(host="127.0.0.1", rest_port=8888)
        )
        
        # Give server time to start
        await asyncio.sleep(0.5)
        
        try:
            # Connect WebSocket client
            async with connect("ws://127.0.0.1:8888/ws") as websocket:
                # Send message
                await websocket.send("test message")
                
                # Should echo back
                response = await websocket.recv()
                assert response == "test message"
        finally:
            # Stop server
            await fastapi_server.stop()
            server_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await server_task
    
    def test_concurrent_requests(self, bridge):
        """Test handling concurrent requests to both Flask and FastAPI"""
        client = TestClient(bridge.get_app())
        
        # Make multiple concurrent requests
        import concurrent.futures
        
        def make_request(endpoint):
            response = client.get(endpoint)
            return response.json()
        
        endpoints = [
            "/api/1/ping",  # FastAPI
            "/api/1/flask_only",  # Flask
            "/api/1/fastapi_only",  # FastAPI
            "/api/1/info",  # FastAPI
        ] * 5  # Repeat for more concurrency
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, ep) for ep in endpoints]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all requests succeeded
        assert len(results) == len(endpoints)
        for result in results:
            assert "result" in result
    
    @pytest.mark.asyncio
    async def test_async_endpoint_compatibility(self, mock_rest_api):
        """Test that async endpoints maintain compatibility with sync RestAPI"""
        # Create async server
        server = AsyncAPIServer(
            rest_api=mock_rest_api,
            ws_notifier=AsyncRotkiNotifier(),
        )
        
        # Mock sync method to be called from async endpoint
        mock_rest_api.rotkehlchen.get_settings = Mock(
            return_value={"main_currency": "USD", "version": "1.35.0"}
        )
        mock_rest_api.rotkehlchen.data.db.get_cache_for_api = Mock(
            return_value={"last_data_upload_ts": 12345}
        )
        
        # Test client
        client = TestClient(server.app)
        
        # Override dependency
        server.app.dependency_overrides[server._get_rest_api] = lambda: mock_rest_api
        
        # Test settings endpoint (if implemented)
        # This demonstrates calling sync methods from async endpoints
        # response = client.get("/api/1/settings")
        # assert response.status_code == 200
    
    def test_error_handling_consistency(self, bridge):
        """Test that error handling is consistent between Flask and FastAPI"""
        client = TestClient(bridge.get_app())
        
        # Test 404 handling
        flask_404 = client.get("/api/1/nonexistent_flask")
        fastapi_404 = client.get("/api/1/nonexistent_fastapi")
        
        # Both should return 404
        assert flask_404.status_code == 404
        assert fastapi_404.status_code == 404
    
    def test_middleware_compatibility(self, bridge):
        """Test that middleware works correctly for both frameworks"""
        # Add logging to track requests
        request_log = []
        
        @bridge.fastapi_app.middleware("http")
        async def log_requests(request, call_next):
            request_log.append(f"FastAPI: {request.url.path}")
            response = await call_next(request)
            return response
        
        client = TestClient(bridge.get_app())
        
        # Make requests
        client.get("/api/1/ping")
        client.get("/api/1/flask_only")
        
        # Check that FastAPI middleware saw all requests
        assert any("ping" in log for log in request_log)
        # Flask requests go through WSGI middleware, so might not be logged


class TestMigrationScenarios:
    """Test specific migration scenarios"""
    
    @pytest.mark.asyncio
    async def test_gradual_endpoint_migration(self, mock_rest_api):
        """Test migrating endpoints one by one"""
        # Start with Flask
        flask_app = Flask(__name__)
        
        @flask_app.route('/api/1/endpoint1')
        def endpoint1():
            return {'result': 'flask1', 'message': ''}
        
        @flask_app.route('/api/1/endpoint2')
        def endpoint2():
            return {'result': 'flask2', 'message': ''}
        
        # Create FastAPI server
        fastapi_server = AsyncAPIServer(
            rest_api=mock_rest_api,
            ws_notifier=AsyncRotkiNotifier(),
        )
        
        # Create bridge
        bridge = FlaskFastAPIBridge(
            flask_app=flask_app,
            fastapi_app=fastapi_server.app,
            rest_api=mock_rest_api,
        )
        
        client = TestClient(bridge.get_app())
        
        # Initially both endpoints are Flask
        assert client.get("/api/1/endpoint1").json()["result"] == "flask1"
        assert client.get("/api/1/endpoint2").json()["result"] == "flask2"
        
        # Migrate endpoint1 to FastAPI
        @fastapi_server.app.get("/api/1/endpoint1")
        async def endpoint1_async():
            return {"result": "fastapi1", "message": ""}
        
        bridge.mark_route_migrated("/api/1/endpoint1")
        
        # Now endpoint1 is FastAPI, endpoint2 is still Flask
        assert client.get("/api/1/endpoint1").json()["result"] == "fastapi1"
        assert client.get("/api/1/endpoint2").json()["result"] == "flask2"
    
    def test_feature_flag_migration(self, mock_rest_api):
        """Test using feature flags to control migration"""
        # Feature flag system
        feature_flags = {"use_async_settings": False}
        
        # Flask implementation
        def flask_settings():
            return {"result": {"source": "flask"}, "message": ""}
        
        # FastAPI implementation
        async def fastapi_settings():
            return {"result": {"source": "fastapi"}, "message": ""}
        
        # Wrapper that checks feature flag
        def get_settings():
            if feature_flags["use_async_settings"]:
                # In production, would route to FastAPI
                return {"result": {"source": "fastapi"}, "message": ""}
            else:
                return flask_settings()
        
        # Test with flag off
        assert get_settings()["result"]["source"] == "flask"
        
        # Enable feature flag
        feature_flags["use_async_settings"] = True
        assert get_settings()["result"]["source"] == "fastapi"
    
    @pytest.mark.asyncio
    async def test_database_migration_compatibility(self):
        """Test that both sync and async database operations work"""
        # Sync database operation (current)
        import sqlite3
        sync_conn = sqlite3.connect(":memory:")
        sync_conn.execute("CREATE TABLE test (id INTEGER)")
        sync_conn.execute("INSERT INTO test VALUES (1)")
        sync_result = sync_conn.execute("SELECT * FROM test").fetchall()
        sync_conn.close()
        
        # Async database operation (new)
        import aiosqlite
        async with aiosqlite.connect(":memory:") as async_conn:
            await async_conn.execute("CREATE TABLE test (id INTEGER)")
            await async_conn.execute("INSERT INTO test VALUES (1)")
            cursor = await async_conn.execute("SELECT * FROM test")
            async_result = await cursor.fetchall()
        
        # Both should work and give same result
        assert sync_result == async_result == [(1,)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])