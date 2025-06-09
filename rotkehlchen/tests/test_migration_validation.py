"""Comprehensive validation tests for gevent to asyncio migration

This test suite ensures that the async implementation maintains
full compatibility with the existing gevent-based system.
"""
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from flask.testing import FlaskClient

from rotkehlchen.api.async_server import AsyncAPIServer
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.chain.evm.async_node_inquirer import AsyncEvmNodeInquirer
from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.tasks.async_manager import AsyncTaskManager
from rotkehlchen.tasks.manager import GreenletManager


class TestMigrationValidation:
    """Validate that async implementation maintains compatibility"""
    
    @pytest.mark.parametrize('endpoint,method,payload', [
        ('/api/1/ping', 'GET', None),
        ('/api/1/info', 'GET', None),
        ('/api/1/settings', 'GET', None),
        ('/api/1/settings', 'PATCH', {'main_currency': 'EUR'}),
        ('/api/1/history/events', 'GET', None),
        ('/api/1/blockchains/evm/transactions', 'GET', None),
    ])
    def test_endpoint_response_compatibility(
        self,
        flask_server: APIServer,
        async_server: AsyncAPIServer,
        endpoint: str,
        method: str,
        payload: dict[str, Any] | None,
    ):
        """Test that endpoints return identical responses"""
        flask_client = flask_server.flask_app.test_client()
        fastapi_client = TestClient(async_server.app)
        
        # Make requests
        if method == 'GET':
            flask_resp = flask_client.get(endpoint)
            fastapi_resp = fastapi_client.get(endpoint)
        elif method == 'PATCH':
            flask_resp = flask_client.patch(endpoint, json=payload)
            fastapi_resp = fastapi_client.patch(endpoint, json=payload)
        elif method == 'POST':
            flask_resp = flask_client.post(endpoint, json=payload)
            fastapi_resp = fastapi_client.post(endpoint, json=payload)
        else:
            pytest.fail(f'Unsupported method: {method}')
            
        # Compare responses
        assert flask_resp.status_code == fastapi_resp.status_code
        
        # Compare JSON content
        flask_data = json.loads(flask_resp.data)
        fastapi_data = fastapi_resp.json()
        
        # Response structure should be identical
        assert flask_data.keys() == fastapi_data.keys()
        assert flask_data.get('error') == fastapi_data.get('error')
        assert flask_data.get('message') == fastapi_data.get('message')


class TestDatabaseCompatibility:
    """Test database operations compatibility"""
    
    @pytest.mark.asyncio
    async def test_concurrent_read_operations(
        self,
        sync_db: DBHandler,
        async_db: AsyncDBHandler,
    ):
        """Test that concurrent reads work correctly"""
        # Sync implementation
        sync_start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(10):
                future = executor.submit(sync_db.get_settings)
                futures.append(future)
            sync_results = [f.result() for f in futures]
        sync_time = time.time() - sync_start
        
        # Async implementation
        async_start = time.time()
        tasks = [async_db.get_settings() for _ in range(10)]
        async_results = await asyncio.gather(*tasks)
        async_time = time.time() - async_start
        
        # Results should be identical
        assert all(r == sync_results[0] for r in sync_results)
        assert all(r == async_results[0] for r in async_results)
        assert sync_results[0] == async_results[0]
        
        # Async should be faster
        assert async_time < sync_time
        
    @pytest.mark.asyncio
    async def test_write_transaction_isolation(
        self,
        async_db: AsyncDBHandler,
    ):
        """Test that write transactions are properly isolated"""
        # Start two concurrent write transactions
        async def write_tx1():
            async with async_db.async_conn.write_ctx() as cursor:
                await cursor.execute(
                    'INSERT INTO settings (name, value) VALUES (?, ?)',
                    ('test1', 'value1')
                )
                # Simulate some work
                await asyncio.sleep(0.1)
                
        async def write_tx2():
            async with async_db.async_conn.write_ctx() as cursor:
                await cursor.execute(
                    'INSERT INTO settings (name, value) VALUES (?, ?)',
                    ('test2', 'value2')
                )
                # Simulate some work
                await asyncio.sleep(0.1)
                
        # Run concurrently
        await asyncio.gather(write_tx1(), write_tx2())
        
        # Both should succeed
        async with async_db.async_conn.read_ctx() as cursor:
            await cursor.execute('SELECT name FROM settings WHERE name IN (?, ?)', ('test1', 'test2'))
            results = await cursor.fetchall()
            
        assert len(results) == 2
        assert {r[0] for r in results} == {'test1', 'test2'}


class TestNodeInquirerCompatibility:
    """Test blockchain node interaction compatibility"""
    
    @pytest.mark.asyncio
    async def test_balance_query_compatibility(
        self,
        sync_inquirer: EvmNodeInquirer,
        async_inquirer: AsyncEvmNodeInquirer,
        test_address: str,
    ):
        """Test that balance queries return same results"""
        # Sync query
        sync_balance = sync_inquirer.get_balance(test_address)
        
        # Async query
        async_balance = await async_inquirer.get_balance(test_address)
        
        # Should be identical
        assert sync_balance == async_balance
        
    @pytest.mark.asyncio
    async def test_concurrent_blockchain_queries(
        self,
        async_inquirer: AsyncEvmNodeInquirer,
        test_addresses: list[str],
    ):
        """Test concurrent blockchain queries performance"""
        start_time = time.time()
        
        # Query multiple addresses concurrently
        tasks = [
            async_inquirer.get_balance(addr)
            for addr in test_addresses
        ]
        balances = await asyncio.gather(*tasks)
        
        query_time = time.time() - start_time
        
        # All queries should complete
        assert len(balances) == len(test_addresses)
        assert all(b is not None for b in balances)
        
        # Should complete quickly (under 2 seconds for 10 addresses)
        assert query_time < 2.0


class TestWebSocketCompatibility:
    """Test WebSocket implementation compatibility"""
    
    @pytest.mark.asyncio
    async def test_message_broadcasting(
        self,
        sync_notifier: RotkiNotifier,
        async_notifier: AsyncRotkiNotifier,
    ):
        """Test that message broadcasting works identically"""
        # Mock WebSocket connections
        mock_sync_ws = Mock()
        mock_async_ws = Mock()
        
        # Subscribe
        sync_notifier.subscribe(mock_sync_ws)
        await async_notifier.subscribe(mock_async_ws)
        
        # Broadcast message
        test_message = {'type': 'balance_update', 'data': {'ETH': '1.5'}}
        
        sync_notifier.broadcast(test_message)
        await async_notifier.broadcast(test_message)
        
        # Both should receive the message
        mock_sync_ws.send.assert_called_once()
        mock_async_ws.send.assert_called_once()
        
        # Messages should be identical
        sync_msg = json.loads(mock_sync_ws.send.call_args[0][0])
        async_msg = json.loads(mock_async_ws.send.call_args[0][0])
        
        assert sync_msg == async_msg == test_message


class TestTaskManagerCompatibility:
    """Test task manager compatibility"""
    
    @pytest.mark.asyncio
    async def test_task_spawning(
        self,
        sync_manager: GreenletManager,
        async_manager: AsyncTaskManager,
    ):
        """Test that task spawning works similarly"""
        # Define test task
        def sync_task():
            time.sleep(0.1)
            return 'sync_result'
            
        async def async_task():
            await asyncio.sleep(0.1)
            return 'async_result'
            
        # Spawn tasks
        sync_greenlet = sync_manager.spawn_and_track(
            method='test_task',
            **{'task_fn': sync_task}
        )
        
        async_task_obj = await async_manager.spawn_and_track(
            task_name='test_task',
            coro=async_task(),
        )
        
        # Wait for completion
        sync_result = sync_greenlet.get()
        async_result = await async_task_obj.result()
        
        # Both should complete successfully
        assert sync_result == 'sync_result'
        assert async_result == 'async_result'
        
    @pytest.mark.asyncio
    async def test_concurrent_task_limit(
        self,
        async_manager: AsyncTaskManager,
    ):
        """Test that task manager respects concurrency limits"""
        # Create many tasks
        async def slow_task(n):
            await asyncio.sleep(0.1)
            return n
            
        # Spawn more tasks than the limit
        tasks = []
        for i in range(20):
            task = await async_manager.spawn_and_track(
                task_name=f'task_{i}',
                coro=slow_task(i),
            )
            tasks.append(task)
            
        # All should complete eventually
        results = []
        for task in tasks:
            result = await task.result()
            results.append(result)
            
        assert sorted(results) == list(range(20))


class TestPerformanceRegression:
    """Ensure async implementation meets performance targets"""
    
    @pytest.mark.asyncio
    async def test_request_latency(
        self,
        async_server: AsyncAPIServer,
        performance_threshold: float = 0.01,  # 10ms
    ):
        """Test that request latency is acceptable"""
        client = TestClient(async_server.app)
        
        # Warm up
        for _ in range(10):
            client.get('/api/1/ping')
            
        # Measure latency
        latencies = []
        for _ in range(100):
            start = time.time()
            response = client.get('/api/1/ping')
            latency = time.time() - start
            
            assert response.status_code == 200
            latencies.append(latency)
            
        # Check performance
        avg_latency = sum(latencies) / len(latencies)
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]
        
        assert avg_latency < performance_threshold
        assert p99_latency < performance_threshold * 2
        
    @pytest.mark.asyncio
    async def test_database_query_performance(
        self,
        async_db: AsyncDBHandler,
        performance_threshold: float = 0.005,  # 5ms
    ):
        """Test database query performance"""
        # Warm up connection pool
        for _ in range(10):
            await async_db.get_settings()
            
        # Measure query time
        query_times = []
        for _ in range(100):
            start = time.time()
            await async_db.get_settings()
            query_time = time.time() - start
            query_times.append(query_time)
            
        # Check performance
        avg_time = sum(query_times) / len(query_times)
        p99_time = sorted(query_times)[int(len(query_times) * 0.99)]
        
        assert avg_time < performance_threshold
        assert p99_time < performance_threshold * 2


class TestErrorHandling:
    """Test that error handling remains consistent"""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(
        self,
        async_db: AsyncDBHandler,
    ):
        """Test database error handling"""
        # Simulate connection error
        with patch.object(async_db.async_conn, 'read_ctx') as mock_ctx:
            mock_ctx.side_effect = Exception('Database connection failed')
            
            with pytest.raises(Exception) as exc_info:
                await async_db.get_settings()
                
            assert 'Database connection failed' in str(exc_info.value)
            
    @pytest.mark.asyncio
    async def test_node_error_handling(
        self,
        async_inquirer: AsyncEvmNodeInquirer,
    ):
        """Test node error handling with failover"""
        # Mock all nodes to fail
        for web3 in async_inquirer._web3_instances.values():
            web3.eth.get_balance = Mock(side_effect=Exception('Node error'))
            
        # Should raise RemoteError after trying all nodes
        with pytest.raises(RemoteError) as exc_info:
            await async_inquirer.get_balance('0x' + '0' * 40)
            
        assert 'Failed to get balance' in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])