#!/usr/bin/env python
"""Example showing how to use the new async components during migration"""
import asyncio
import logging
from pathlib import Path

from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.db.drivers.sqlcipher_sync import SyncSQLCipherConnection, DBConnectionType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.async_manager import AsyncTaskManager
from rotkehlchen.user_messages import MessagesAggregator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


async def example_async_task(name: str, duration: float) -> str:
    """Example async task that simulates work"""
    log.info(f"Task {name} starting, will run for {duration}s")
    await asyncio.sleep(duration)
    log.info(f"Task {name} completed")
    return f"Result from {name}"


async def example_websocket_server():
    """Example WebSocket server using the new async notifier"""
    import websockets
    
    # Create notifier
    notifier = AsyncRotkiNotifier()
    
    async def handle_connection(websocket, path):
        # This would be handled by AsyncRotkiWSHandler in production
        await notifier.subscribe(websocket)
        try:
            async for message in websocket:
                log.info(f"Received: {message}")
        finally:
            await notifier.unsubscribe(websocket)
    
    # Start server
    async with websockets.serve(handle_connection, "localhost", 8765):
        log.info("WebSocket server started on ws://localhost:8765")
        
        # Simulate broadcasting messages
        for i in range(5):
            await asyncio.sleep(2)
            await notifier.broadcast(
                message_type=WSMessageType.PROGRESS_UPDATES,
                to_send_data={
                    'status': f'Update {i}',
                    'progress': i * 20,
                }
            )
        
        await asyncio.sleep(1)


async def example_task_manager():
    """Example of using the async task manager"""
    # Create message aggregator (normally from rotki instance)
    msg_aggregator = MessagesAggregator()
    
    # Create task manager
    task_manager = AsyncTaskManager(msg_aggregator)
    
    # Spawn some tasks
    tasks = []
    for i in range(3):
        task = await task_manager.spawn_and_track(
            task_name=f"example_task_{i}",
            coro=example_async_task(f"Task-{i}", 2.0 + i),
            exception_is_error=True,
            delay=i * 0.5,  # Stagger start times
        )
        tasks.append(task)
    
    # Check running tasks
    log.info(f"Running tasks: {task_manager.task_count}")
    
    # Wait for all to complete
    await task_manager.wait_for_all(timeout=10.0)
    
    # Clean up finished tasks
    task_manager.clear_finished()
    log.info("All tasks completed")


def example_sync_database():
    """Example of using sync SQLCipher wrapper"""
    # Create in-memory SQLite database for example
    db = SyncSQLCipherConnection(":memory:", DBConnectionType.GLOBAL)
    
    # Create a table
    with db.write_ctx() as cursor:
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                balance REAL DEFAULT 0
            )
        ''')
        
        # Insert some data
        cursor.execute(
            "INSERT INTO users (name, balance) VALUES (?, ?)",
            ("Alice", 100.50)
        )
    
    # Read data
    with db.read_ctx() as cursor:
        cursor.execute("SELECT * FROM users")
        for row in cursor.fetchall():
            log.info(f"User: {row}")
    
    # Use savepoint
    with db.write_ctx() as cursor:
        cursor.execute("UPDATE users SET balance = balance + 50")
        
        with db.savepoint_ctx() as sp_cursor:
            sp_cursor.execute("UPDATE users SET balance = balance + 1000")
            # This will rollback due to exception
            raise Exception("Oops, too much!")
    
    # Check final balance (should be 150.50, not 1150.50)
    with db.read_ctx() as cursor:
        cursor.execute("SELECT balance FROM users WHERE name = ?", ("Alice",))
        balance = cursor.fetchone()[0]
        log.info(f"Final balance: {balance}")
    
    db.close()


async def main():
    """Main async function showing different components"""
    log.info("Starting async migration examples")
    
    # Run task manager example
    log.info("\n=== Task Manager Example ===")
    await example_task_manager()
    
    # Run database example (sync in thread)
    log.info("\n=== Database Example ===")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, example_sync_database)
    
    # Uncomment to run WebSocket server example
    # log.info("\n=== WebSocket Server Example ===")
    # await example_websocket_server()
    
    log.info("\nAll examples completed!")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())