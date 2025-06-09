"""Test migrated endpoints to ensure compatibility"""
import json
import os
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from flask import Flask
from flask.testing import FlaskClient

from rotkehlchen.api.async_server import AsyncAPIServer
from rotkehlchen.api.rest import RestAPI, api_response, process_result
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.notifier import RotkiNotifier


class TestEndpointMigrationCompatibility:
    """Test that migrated endpoints maintain exact compatibility with Flask versions"""
    
    @pytest.fixture
    def mock_rotkehlchen(self):
        """Create mock Rotkehlchen instance"""
        mock = Mock()
        mock.data.db.conn.read_ctx = Mock()
        mock.data.db.conn.read_ctx().__enter__ = Mock()
        mock.data.db.conn.read_ctx().__exit__ = Mock()
        mock.get_settings = Mock(return_value={"main_currency": "USD", "version": 1})
        mock.data.db.get_cache_for_api = Mock(return_value={"last_data_upload_ts": 12345})
        return mock
    
    @pytest.fixture
    def rest_api(self, mock_rotkehlchen):
        """Create RestAPI instance with mocks"""
        rest_api = Mock(spec=RestAPI)
        rest_api.rotkehlchen = mock_rotkehlchen
        
        # Mock the get_info method to return Flask-style response
        rest_api.get_info = Mock(return_value=api_response({
            "result": {
                "version": "1.35.0",
                "data_directory": "/home/user/.rotki",
                "log_level": "debug",
                "backend_default_arguments": {},
            },
            "message": ""
        }, status_code=200))
        
        # Mock settings methods
        rest_api.get_settings = Mock(return_value=api_response({
            "result": {"main_currency": "USD", "version": 1, "last_data_upload_ts": 12345},
            "message": ""
        }, status_code=200))
        
        rest_api.set_settings = Mock(return_value=api_response({
            "result": True,
            "message": ""
        }, status_code=200))
        
        return rest_api
    
    @pytest.fixture
    def flask_server(self, rest_api):
        """Create Flask server"""
        notifier = RotkiNotifier()
        server = APIServer(
            rest_api=rest_api,
            ws_notifier=notifier,
        )
        return server
    
    @pytest.fixture
    def async_server(self, rest_api):
        """Create FastAPI server"""
        notifier = AsyncRotkiNotifier()
        server = AsyncAPIServer(
            rest_api=rest_api,
            ws_notifier=notifier,
        )
        # Override dependency
        server.app.dependency_overrides[server._get_rest_api] = lambda: rest_api
        return server
    
    def test_ping_endpoint_compatibility(self, flask_server, async_server):
        """Test /ping endpoint returns identical responses"""
        # Enable async ping endpoint
        async_features.enable(AsyncFeature.PING_ENDPOINT)
        
        # Test Flask response
        flask_client = flask_server.flask_app.test_client()
        flask_response = flask_client.get('/api/1/ping')
        flask_data = json.loads(flask_response.data)
        
        # Test FastAPI response
        fastapi_client = TestClient(async_server.app)
        fastapi_response = fastapi_client.get('/api/1/ping')
        fastapi_data = fastapi_response.json()
        
        # Responses should be identical
        assert flask_response.status_code == fastapi_response.status_code == 200
        assert flask_data == fastapi_data
        assert flask_data == {"result": True, "message": ""}
    
    def test_info_endpoint_compatibility(self, flask_server, async_server, rest_api):
        """Test /info endpoint returns identical responses"""
        # Enable async info endpoint
        async_features.enable(AsyncFeature.INFO_ENDPOINT)
        
        # Test without check_for_updates
        flask_client = flask_server.flask_app.test_client()
        flask_response = flask_client.get('/api/1/info')
        flask_data = json.loads(flask_response.data)
        
        fastapi_client = TestClient(async_server.app)
        fastapi_response = fastapi_client.get('/api/1/info')
        fastapi_data = fastapi_response.json()
        
        assert flask_response.status_code == fastapi_response.status_code == 200
        assert flask_data == fastapi_data
        
        # Test with check_for_updates
        flask_response = flask_client.get('/api/1/info?check_for_updates=true')
        fastapi_response = fastapi_client.get('/api/1/info?check_for_updates=true')
        
        assert json.loads(flask_response.data) == fastapi_response.json()
    
    def test_settings_endpoint_compatibility(self, flask_server, async_server, mock_rotkehlchen):
        """Test /settings endpoints return identical responses"""
        # Enable async settings endpoint
        async_features.enable(AsyncFeature.SETTINGS_ENDPOINT)
        
        # Setup mock to work with context manager
        mock_cursor = Mock()
        mock_rotkehlchen.data.db.conn.read_ctx.return_value.__enter__.return_value = mock_cursor
        
        # Test GET /settings
        flask_client = flask_server.flask_app.test_client()
        flask_response = flask_client.get('/api/1/settings')
        flask_data = json.loads(flask_response.data)
        
        fastapi_client = TestClient(async_server.app)
        fastapi_response = fastapi_client.get('/api/1/settings')
        fastapi_data = fastapi_response.json()
        
        assert flask_response.status_code == fastapi_response.status_code == 200
        # Both should have result with settings and cache merged
        assert "result" in flask_data and "result" in fastapi_data
        assert flask_data["result"]["main_currency"] == fastapi_data["result"]["main_currency"]
    
    def test_feature_flag_disabled(self, async_server):
        """Test that endpoints return 404 when feature flag is disabled"""
        # Disable all features
        for feature in AsyncFeature:
            async_features.disable(feature)
        
        client = TestClient(async_server.app)
        
        # All async endpoints should return 404
        assert client.get('/api/1/ping').status_code == 404
        assert client.get('/api/1/info').status_code == 404
        assert client.get('/api/1/settings').status_code == 404
    
    def test_error_handling_compatibility(self, flask_server, async_server, rest_api):
        """Test that error responses are identical"""
        # Enable endpoints
        async_features.enable(AsyncFeature.INFO_ENDPOINT)
        
        # Make get_info raise an exception
        rest_api.get_info.side_effect = Exception("Test error")
        
        # Test Flask error response
        flask_client = flask_server.flask_app.test_client()
        flask_response = flask_client.get('/api/1/info')
        flask_data = json.loads(flask_response.data)
        
        # Test FastAPI error response
        fastapi_client = TestClient(async_server.app)
        fastapi_response = fastapi_client.get('/api/1/info')
        fastapi_data = fastapi_response.json()
        
        # Error responses should have same structure
        assert flask_response.status_code == fastapi_response.status_code == 500
        assert flask_data.get("error") == fastapi_data.get("error") == True
        assert flask_data.get("result") == fastapi_data.get("result") == None
        assert "message" in flask_data and "message" in fastapi_data


class TestFeatureFlagSystem:
    """Test the feature flag system"""
    
    def test_environment_variable_loading(self):
        """Test feature flags load from environment"""
        # Set environment variables
        os.environ["ASYNC_FEATURE_PING"] = "true"
        os.environ["ASYNC_FEATURE_INFO"] = "false"
        
        # Create new instance to load from env
                flags = FeatureFlags()
        
        assert flags.is_enabled(AsyncFeature.PING_ENDPOINT) is True
        assert flags.is_enabled(AsyncFeature.INFO_ENDPOINT) is False
        
        # Cleanup
        del os.environ["ASYNC_FEATURE_PING"]
        del os.environ["ASYNC_FEATURE_INFO"]
    
    def test_async_mode_settings(self):
        """Test ASYNC_MODE environment variable"""
        # Test full mode
        os.environ["ASYNC_MODE"] = "full"
                flags = FeatureFlags()
        
        # All features should be enabled
        for feature in AsyncFeature:
            assert flags.is_enabled(feature) is True
        
        # Cleanup
        del os.environ["ASYNC_MODE"]
    
    def test_runtime_toggle(self):
        """Test runtime feature toggling"""
        # Start with feature disabled
        async_features.disable(AsyncFeature.SETTINGS_ENDPOINT)
        assert async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT) is False
        
        # Enable at runtime
        async_features.enable(AsyncFeature.SETTINGS_ENDPOINT)
        assert async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT) is True
    
    def test_migration_metrics(self):
        """Test migration metrics calculation"""
                
        # Enable some features
        async_features.enable(AsyncFeature.PING_ENDPOINT)
        async_features.enable(AsyncFeature.INFO_ENDPOINT)
        
        metrics = get_migration_metrics()
        
        assert "total_features" in metrics
        assert "enabled_features" in metrics
        assert "progress_percentage" in metrics
        assert "endpoint_migration" in metrics
        assert metrics["enabled_features"] >= 2  # At least ping and info


class TestAsyncPerformance:
    """Basic performance tests for migrated endpoints"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_server):
        """Test handling multiple concurrent requests"""
        import asyncio
        import httpx
        
        # Enable endpoints
        async_features.enable(AsyncFeature.PING_ENDPOINT)
        
        client = TestClient(async_server.app)
        
        # Make 10 concurrent requests
        async def make_request():
            return client.get('/api/1/ping')
        
        # Run requests concurrently
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*[asyncio.create_task(t) for t in tasks])
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json() == {"result": True, "message": ""} for r in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])