"""Integration tests for mixed sync/async operation

These tests ensure that sync and async components can work together
during the migration period.
"""
import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from rotkehlchen.utils.gevent_compat import sleep
import pytest
from flask.testing import FlaskClient
from fastapi.testclient import TestClient

from rotkehlchen.api.async_server import AsyncAPIServer
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.tasks.async_manager import AsyncTaskManager
from rotkehlchen.tasks.manager import TaskManager


class TestMixedOperation:
    """Test sync and async components operating together"""
    
    def test_concurrent_database_access(
        self,
        sync_db: DBHandler,
        async_db: AsyncDBHandler,
        event_loop,
    ):
        """Test that sync and async DB access work concurrently"""
        results = {'sync': [], 'async': []}
        errors = {'sync': [], 'async': []}
        
        # Sync database operations in thread
        def sync_operations():
            try:
                for i in range(10):
                    with sync_db.conn.read_ctx() as cursor:
                        cursor.execute('SELECT COUNT(*) FROM settings')
                        count = cursor.fetchone()[0]
                        results['sync'].append(count)
                    time.sleep(0.01)  # Small delay
            except Exception as e:
                errors['sync'].append(str(e))
                
        # Async database operations
        async def async_operations():
            try:
                for i in range(10):
                    async with async_db.async_conn.read_ctx() as cursor:
                        await cursor.execute('SELECT COUNT(*) FROM settings')
                        count = (await cursor.fetchone())[0]
                        results['async'].append(count)
                    await asyncio.sleep(0.01)  # Small delay
            except Exception as e:
                errors['async'].append(str(e))
                
        # Run both concurrently
        sync_thread = threading.Thread(target=sync_operations)
        sync_thread.start()
        
        event_loop.run_until_complete(async_operations())
        
        sync_thread.join()
        
        # Both should complete successfully
        assert len(results['sync']) == 10
        assert len(results['async']) == 10
        assert not errors['sync']
        assert not errors['async']
        
        # Results should be consistent
        assert all(r == results['sync'][0] for r in results['sync'])
        assert all(r == results['async'][0] for r in results['async'])
        
    def test_mixed_api_requests(
        self,
        flask_server: APIServer,
        async_server: AsyncAPIServer,
    ):
        """Test Flask and FastAPI handling requests simultaneously"""
        # Enable some async endpoints
        async_features.enable(AsyncFeature.PING_ENDPOINT)
        async_features.enable(AsyncFeature.INFO_ENDPOINT)
        
        flask_client = flask_server.flask_app.test_client()
        fastapi_client = TestClient(async_server.app)
        
        # Make concurrent requests to both servers
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            
            # Mix of Flask and FastAPI requests
            for i in range(20):
                if i % 2 == 0:
                    # Flask request
                    future = executor.submit(
                        flask_client.get,
                        '/api/1/settings',  # Not migrated
                    )
                else:
                    # FastAPI request
                    future = executor.submit(
                        fastapi_client.get,
                        '/api/1/ping',  # Migrated
                    )
                futures.append(future)
                
            # Wait for all to complete
            results = [f.result() for f in futures]
            
        # All requests should succeed
        assert all(r.status_code == 200 for r in results)
        
    def test_websocket_migration_bridge(
        self,
        sync_notifier: RotkiNotifier,
        async_notifier: AsyncRotkiNotifier,
        event_loop,
    ):
        """Test WebSocket migration bridge functionality"""
        received_messages = {'sync': [], 'async': []}
        
        # Mock WebSocket connections
        class MockSyncWS:
            def __init__(self):
                self.messages = []
                
            def send(self, message):
                self.messages.append(json.loads(message))
                
        class MockAsyncWS:
            def __init__(self):
                self.messages = []
                
            async def send(self, message):
                self.messages.append(json.loads(message))
                
        sync_ws = MockSyncWS()
        async_ws = MockAsyncWS()
        
        # Subscribe connections
        sync_notifier.subscribe(sync_ws)
        
        async def subscribe_async():
            await async_notifier.subscribe(async_ws)
            
        event_loop.run_until_complete(subscribe_async())
        
        # Send messages from both notifiers
        test_message = {'type': 'test', 'data': 'message'}
        
        # Sync broadcast
        sync_notifier.broadcast('test_type', test_message)
        
        # Async broadcast
        async def broadcast_async():
            await async_notifier.broadcast('test_type', test_message)
            
        event_loop.run_until_complete(broadcast_async())
        
        # Both should receive messages
        assert len(sync_ws.messages) > 0
        assert len(async_ws.messages) > 0
        
    def test_task_manager_coexistence(
        self,
        sync_task_manager: GreenletManager,
        async_task_manager: AsyncTaskManager,
        event_loop,
    ):
        """Test sync and async task managers working together"""
        results = {'sync': None, 'async': None}
        
        # Define tasks
        def sync_task():
            sleep(0.1)
            return 'sync_complete'
            
        async def async_task():
            await asyncio.sleep(0.1)
            return 'async_complete'
            
        # Start sync task
        sync_greenlet = sync_task_manager.spawn_and_track(
            method='sync_test',
            module_name='test',
            **{'task_fn': sync_task}
        )
        
        # Start async task
        async def run_async_task():
            task = await async_task_manager.spawn_and_track(
                task_name='async_test',
                coro=async_task(),
            )
            return await task.result()
            
        # Run both
        async_result = event_loop.run_until_complete(run_async_task())
        sync_result = sync_greenlet.get()
        
        # Both should complete
        assert sync_result == 'sync_complete'
        assert async_result == 'async_complete'


class TestFeatureFlagIntegration:
    """Test feature flag system in mixed operation"""
    
    def test_gradual_endpoint_migration(
        self,
        flask_server: APIServer,
        async_server: AsyncAPIServer,
    ):
        """Test gradual endpoint migration with feature flags"""
        flask_client = flask_server.flask_app.test_client()
        fastapi_client = TestClient(async_server.app)
        
        # Initially all async endpoints are disabled
        for feature in AsyncFeature:
            async_features.disable(feature)
            
        # Test that async endpoints return 404
        assert fastapi_client.get('/api/1/ping').status_code == 404
        
        # Enable ping endpoint
        async_features.enable(AsyncFeature.PING_ENDPOINT)
        
        # Now it should work
        response = fastapi_client.get('/api/1/ping')
        assert response.status_code == 200
        assert response.json() == {'result': True, 'message': ''}
        
        # Flask endpoint should still work
        flask_response = flask_client.get('/api/1/ping')
        assert flask_response.status_code == 200
        
    def test_runtime_feature_toggle(
        self,
        async_server: AsyncAPIServer,
    ):
        """Test toggling features at runtime"""
        client = TestClient(async_server.app)
        
        # Check initial status
        response = client.get('/api/1/async/features')
        assert response.status_code == 200
        initial_status = response.json()['result']['status']
        
        # Toggle a feature
        response = client.put(
            '/api/1/async/features/ping',
            params={'enabled': True}
        )
        assert response.status_code == 200
        
        # Verify it's enabled
        response = client.get('/api/1/async/features')
        new_status = response.json()['result']['status']
        assert new_status['ping'] is True
        
        # Test the endpoint works
        response = client.get('/api/1/ping')
        assert response.status_code == 200


class TestDataMigration:
    """Test data migration between sync and async systems"""
    
    @pytest.mark.asyncio
    async def test_settings_consistency(
        self,
        sync_db: DBHandler,
        async_db: AsyncDBHandler,
    ):
        """Test that settings remain consistent"""
        # Set a value using sync DB
        test_settings = {'test_key': 'test_value'}
        with sync_db.conn.write_ctx() as cursor:
            cursor.execute(
                'INSERT OR REPLACE INTO settings (name, value) VALUES (?, ?)',
                ('test_key', json.dumps('test_value'))
            )
            
        # Read using async DB
        async_settings = await async_db.get_settings()
        assert async_settings.get('test_key') == 'test_value'
        
        # Set using async DB
        await async_db.set_settings({'async_key': 'async_value'})
        
        # Read using sync DB
        with sync_db.conn.read_ctx() as cursor:
            cursor.execute('SELECT value FROM settings WHERE name = ?', ('async_key',))
            result = cursor.fetchone()
            
        assert json.loads(result[0]) == 'async_value'
        
    @pytest.mark.asyncio
    async def test_concurrent_writes(
        self,
        sync_db: DBHandler,
        async_db: AsyncDBHandler,
    ):
        """Test concurrent writes don't cause conflicts"""
        # Prepare test data
        sync_values = [f'sync_{i}' for i in range(10)]
        async_values = [f'async_{i}' for i in range(10)]
        
        # Define write functions
        def sync_writes():
            for i, value in enumerate(sync_values):
                with sync_db.conn.write_ctx() as cursor:
                    cursor.execute(
                        'INSERT INTO test_table (id, value) VALUES (?, ?)',
                        (i * 2, value)  # Even IDs
                    )
                time.sleep(0.01)
                
        async def async_writes():
            for i, value in enumerate(async_values):
                async with async_db.async_conn.write_ctx() as cursor:
                    await cursor.execute(
                        'INSERT INTO test_table (id, value) VALUES (?, ?)',
                        (i * 2 + 1, value)  # Odd IDs
                    )
                await asyncio.sleep(0.01)
                
        # Create test table
        with sync_db.conn.write_ctx() as cursor:
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)'
            )
            
        # Run concurrent writes
        sync_thread = threading.Thread(target=sync_writes)
        sync_thread.start()
        
        await async_writes()
        
        sync_thread.join()
        
        # Verify all writes succeeded
        async with async_db.async_conn.read_ctx() as cursor:
            await cursor.execute('SELECT COUNT(*) FROM test_table')
            count = (await cursor.fetchone())[0]
            
        assert count == 20  # 10 sync + 10 async


class TestPerformanceComparison:
    """Compare performance of sync vs async operations"""
    
    @pytest.mark.asyncio
    async def test_bulk_query_performance(
        self,
        sync_db: DBHandler,
        async_db: AsyncDBHandler,
    ):
        """Test bulk query performance"""
        # Prepare test data
        with sync_db.conn.write_ctx() as cursor:
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS perf_test (id INTEGER PRIMARY KEY, data TEXT)'
            )
            for i in range(1000):
                cursor.execute(
                    'INSERT INTO perf_test (id, data) VALUES (?, ?)',
                    (i, f'test_data_{i}')
                )
                
        # Sync queries
        sync_start = time.time()
        sync_results = []
        for i in range(100):
            with sync_db.conn.read_ctx() as cursor:
                cursor.execute('SELECT COUNT(*) FROM perf_test WHERE id < ?', (i * 10,))
                sync_results.append(cursor.fetchone()[0])
        sync_time = time.time() - sync_start
        
        # Async queries
        async_start = time.time()
        async_results = []
        tasks = []
        for i in range(100):
            async def query(idx):
                async with async_db.async_conn.read_ctx() as cursor:
                    await cursor.execute('SELECT COUNT(*) FROM perf_test WHERE id < ?', (idx * 10,))
                    return (await cursor.fetchone())[0]
            tasks.append(query(i))
            
        async_results = await asyncio.gather(*tasks)
        async_time = time.time() - async_start
        
        # Results should match
        assert sync_results == async_results
        
        # Async should be faster for concurrent queries
        assert async_time < sync_time * 0.7  # At least 30% faster
        
        print(f'Sync time: {sync_time:.3f}s, Async time: {async_time:.3f}s')
        print(f'Performance improvement: {((sync_time - async_time) / sync_time) * 100:.1f}%')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])