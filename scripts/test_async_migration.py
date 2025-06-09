#!/usr/bin/env python
"""Script to test the async migration components

This demonstrates how the new async components work together
and can be used for testing during migration.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rotkehlchen.api.async_server import AsyncAPIServer
from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.migration import ws_migration_bridge
from rotkehlchen.db.drivers.sqlcipher_sync import SyncSQLCipherConnection, DBConnectionType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.async_manager import AsyncTaskManager
from rotkehlchen.user_messages import MessagesAggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


async def test_websocket_server():
    """Test the async WebSocket implementation"""
    log.info("Testing AsyncRotkiNotifier...")
    
    # Create notifier
    notifier = AsyncRotkiNotifier()
    
    # Create a simple WebSocket server for testing
    import websockets
    
    connected_clients = set()
    
    async def handle_connection(websocket, path):
        log.info(f"Client connected from {websocket.remote_address}")
        await notifier.subscribe(websocket)
        connected_clients.add(websocket)
        
        try:
            async for message in websocket:
                log.info(f"Received message: {message}")
                # Echo back
                await websocket.send(f"Echo: {message}")
        except websockets.exceptions.ConnectionClosed:
            log.info("Client disconnected")
        finally:
            connected_clients.discard(websocket)
            await notifier.unsubscribe(websocket)
    
    # Start server
    server = await websockets.serve(handle_connection, "localhost", 8765)
    log.info("WebSocket server started on ws://localhost:8765")
    
    # Simulate some broadcasts
    for i in range(3):
        await asyncio.sleep(2)
        await notifier.broadcast(
            message_type='test_update',
            to_send_data={'iteration': i, 'message': f'Update {i}'}
        )
        log.info(f"Broadcast message {i}")
    
    await server.close()
    log.info("WebSocket server stopped")


async def test_task_manager():
    """Test the async task manager"""
    log.info("Testing AsyncTaskManager...")
    
    msg_aggregator = MessagesAggregator()
    task_manager = AsyncTaskManager(msg_aggregator)
    
    # Define some test tasks
    async def sample_task(name: str, duration: float):
        log.info(f"Task {name} started")
        await asyncio.sleep(duration)
        log.info(f"Task {name} completed")
        return f"Result from {name}"
    
    # Spawn multiple tasks
    tasks = []
    for i in range(3):
        task = await task_manager.spawn_and_track(
            task_name=f"test_task_{i}",
            coro=sample_task(f"Task-{i}", 1.0 + i * 0.5),
            exception_is_error=True,
        )
        tasks.append(task)
    
    log.info(f"Spawned {task_manager.task_count} tasks")
    
    # Wait for completion
    await task_manager.wait_for_all(timeout=10.0)
    
    log.info("All tasks completed")
    task_manager.clear_finished()


def test_sync_database():
    """Test the sync SQLCipher wrapper"""
    log.info("Testing SyncSQLCipherConnection...")
    
    # Create in-memory database
    db = SyncSQLCipherConnection(":memory:", DBConnectionType.GLOBAL)
    
    # Create test table
    with db.write_ctx() as cursor:
        cursor.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL
            )
        ''')
        
        # Insert test data
        test_data = [
            ("Alice", 100.5),
            ("Bob", 200.75),
            ("Charlie", 300.25),
        ]
        for name, value in test_data:
            cursor.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                (name, value)
            )
    
    # Read data back
    with db.read_ctx() as cursor:
        cursor.execute("SELECT * FROM test_table ORDER BY id")
        rows = cursor.fetchall()
        for row in rows:
            log.info(f"Row: {row}")
    
    # Test savepoint
    try:
        with db.write_ctx() as cursor:
            cursor.execute("UPDATE test_table SET value = value * 2")
            
            with db.savepoint_ctx() as sp_cursor:
                sp_cursor.execute("DELETE FROM test_table WHERE name = ?", ("Bob",))
                # Simulate error to trigger rollback
                raise Exception("Test rollback")
    except Exception:
        log.info("Savepoint rolled back as expected")
    
    # Verify Bob is still there
    with db.read_ctx() as cursor:
        cursor.execute("SELECT COUNT(*) FROM test_table WHERE name = ?", ("Bob",))
        count = cursor.fetchone()[0]
        log.info(f"Bob still exists: {count == 1}")
    
    db.close()
    log.info("Database test completed")


async def test_fastapi_server():
    """Test the FastAPI async server"""
    log.info("Testing AsyncAPIServer...")
    
    # Create mock RestAPI
    class MockRestAPI:
        def __init__(self):
            self.rotkehlchen = None
    
    rest_api = MockRestAPI()
    notifier = AsyncRotkiNotifier()
    
    # Create server
    server = AsyncAPIServer(
        rest_api=rest_api,
        ws_notifier=notifier,
        cors_domain_list=["http://localhost:3000"]
    )
    
    log.info("FastAPI server created with routes:")
    for route in server.app.routes:
        if hasattr(route, 'path'):
            log.info(f"  {route.methods} {route.path}")
    
    # Test a simple request using the test client
    from fastapi.testclient import TestClient
    
    with TestClient(server.app) as client:
        # Test ping endpoint
        response = client.get("/api/1/ping")
        log.info(f"Ping response: {response.json()}")
        
        # Test info endpoint
        response = client.get("/api/1/info?check_for_updates=false")
        log.info(f"Info response: {response.json()}")


async def test_migration_bridge():
    """Test the WebSocket migration bridge"""
    log.info("Testing WebSocket migration bridge...")
    
    # Enable async mode
    ws_migration_bridge.enable_async_mode()
    
    # Test broadcasting through bridge
    ws_migration_bridge.broadcast(
        message_type='test_bridge',
        to_send_data={'message': 'Testing migration bridge'}
    )
    
    log.info("Migration bridge test completed")


async def main():
    """Run all tests"""
    log.info("Starting async migration tests...")
    
    try:
        # Test components individually
        log.info("\n=== Testing Sync Database ===")
        test_sync_database()
        
        log.info("\n=== Testing Task Manager ===")
        await test_task_manager()
        
        log.info("\n=== Testing FastAPI Server ===")
        await test_fastapi_server()
        
        log.info("\n=== Testing Migration Bridge ===")
        await test_migration_bridge()
        
        # Uncomment to test WebSocket server (requires client connection)
        # log.info("\n=== Testing WebSocket Server ===")
        # await test_websocket_server()
        
        log.info("\n✅ All tests completed successfully!")
        
    except Exception as e:
        log.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())