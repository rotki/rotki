"""Async SQLCipher driver implementation using thread pool

Since SQLCipher doesn't have native async support, we use a thread pool
to run synchronous operations without blocking the event loop.
"""
import asyncio
import logging
import queue
import threading
from collections.abc import AsyncGenerator, Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, ContextManager

import sqlcipher3
from sqlcipher3 import Connection, Cursor

from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncDBConnection:
    """Async wrapper for SQLCipher connection using thread pool

    This replaces the gevent-based DBConnection without the progress handler hack.
    All database operations run in a thread pool to avoid blocking the event loop.
    """

    def __init__(
        self,
        path: Path,
        password: str,
        timeout: float = 30.0,
        max_connections: int = 10,
    ):
        self.path = path
        self.password = password
        self.timeout = timeout
        self.max_connections = max_connections

        # Thread pool for database operations
        self._executor = ThreadPoolExecutor(
            max_workers=max_connections,
            thread_name_prefix='sqlcipher',
        )

        # Connection pool
        self._connections: queue.Queue[Connection] = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._initialized = False

    def _create_connection(self) -> Connection:
        """Create a new SQLCipher connection"""
        connection = sqlcipher3.connect(
            str(self.path),
            timeout=self.timeout,
            check_same_thread=False,  # Allow multi-threading
        )

        # Set up SQLCipher
        cursor = connection.cursor()
        cursor.execute(f'PRAGMA key="{self.password}"')
        cursor.execute('PRAGMA cipher_version')
        version = cursor.fetchone()

        if not version:
            raise DBUpgradeError('Failed to unlock database')

        # Set pragmas
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA foreign_keys=ON')

        log.debug(f'Created SQLCipher connection, version: {version[0]}')
        return connection

    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return

        loop = asyncio.get_event_loop()

        def _init_pool():
            with self._lock:
                if self._initialized:
                    return

                # Create initial connections
                for _ in range(min(3, self.max_connections)):
                    conn = self._create_connection()
                    self._connections.put(conn)

                self._initialized = True
                log.info(f'Initialized async database pool with {self._connections.qsize()} connections')

        await loop.run_in_executor(self._executor, _init_pool)

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Connection, None]:
        """Get a connection from the pool"""
        await self.initialize()

        loop = asyncio.get_event_loop()

        # Get connection from pool
        connection = await loop.run_in_executor(
            self._executor,
            self._connections.get,
            True,  # block
            self.timeout,
        )

        try:
            yield connection
        finally:
            # Return connection to pool
            await loop.run_in_executor(
                self._executor,
                self._connections.put,
                connection,
            )

    @asynccontextmanager
    async def read_ctx(self) -> AsyncGenerator['AsyncDBCursor', None]:
        """Async context manager for read operations"""
        async with self.get_connection() as conn:
            cursor = AsyncDBCursor(conn, self._executor)
            try:
                yield cursor
            finally:
                await cursor.close()

    @asynccontextmanager
    async def write_ctx(self) -> AsyncGenerator['AsyncDBCursor', None]:
        """Async context manager for write operations"""
        async with self.get_connection() as conn:
            cursor = AsyncDBCursor(conn, self._executor)
            try:
                # Begin transaction
                await cursor.execute('BEGIN')
                yield cursor
                # Commit on success
                await cursor.execute('COMMIT')
            except Exception:
                # Rollback on error
                await cursor.execute('ROLLBACK')
                raise
            finally:
                await cursor.close()

    @contextmanager
    def sync_read_ctx(self) -> Generator[Cursor, None, None]:
        """Synchronous read context for compatibility"""
        # Get connection synchronously
        conn = self._connections.get(block=True, timeout=self.timeout)
        try:
            cursor = conn.cursor()
            yield cursor
        finally:
            cursor.close()
            self._connections.put(conn)

    @contextmanager
    def sync_write_ctx(self) -> Generator[Cursor, None, None]:
        """Synchronous write context for compatibility"""
        conn = self._connections.get(block=True, timeout=self.timeout)
        try:
            cursor = conn.cursor()
            cursor.execute('BEGIN')
            yield cursor
            cursor.execute('COMMIT')
        except Exception:
            cursor.execute('ROLLBACK')
            raise
        finally:
            cursor.close()
            self._connections.put(conn)

    async def execute(self, query: str, *args) -> list[Any] | None:
        """Execute a query and return results"""
        async with self.read_ctx() as cursor:
            await cursor.execute(query, args)
            return await cursor.fetchall()

    async def executemany(self, query: str, params: list[tuple]) -> None:
        """Execute a query with multiple parameter sets"""
        async with self.write_ctx() as cursor:
            await cursor.executemany(query, params)

    async def close(self):
        """Close all connections and shutdown executor"""
        loop = asyncio.get_event_loop()

        def _close_all():
            # Close all connections
            while not self._connections.empty():
                try:
                    conn = self._connections.get_nowait()
                    conn.close()
                except queue.Empty:
                    break

        await loop.run_in_executor(self._executor, _close_all)
        self._executor.shutdown(wait=True)


class AsyncDBCursor:
    """Async wrapper for database cursor operations"""

    def __init__(self, connection: Connection, executor: ThreadPoolExecutor):
        self.connection = connection
        self.executor = executor
        self.cursor: Cursor | None = None
        self._closed = False

    async def _ensure_cursor(self):
        """Ensure cursor is created"""
        if self.cursor is None and not self._closed:
            loop = asyncio.get_event_loop()
            self.cursor = await loop.run_in_executor(
                self.executor,
                self.connection.cursor,
            )

    async def execute(self, query: str, params: tuple | None = None) -> 'AsyncDBCursor':
        """Execute a query"""
        await self._ensure_cursor()
        loop = asyncio.get_event_loop()

        if params:
            await loop.run_in_executor(
                self.executor,
                self.cursor.execute,
                query,
                params,
            )
        else:
            await loop.run_in_executor(
                self.executor,
                self.cursor.execute,
                query,
            )

        return self

    async def executemany(self, query: str, params: list[tuple]) -> 'AsyncDBCursor':
        """Execute a query with multiple parameter sets"""
        await self._ensure_cursor()
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            self.executor,
            self.cursor.executemany,
            query,
            params,
        )

        return self

    async def fetchone(self) -> tuple | None:
        """Fetch one row"""
        await self._ensure_cursor()
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            self.executor,
            self.cursor.fetchone,
        )

    async def fetchall(self) -> list[tuple]:
        """Fetch all rows"""
        await self._ensure_cursor()
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            self.executor,
            self.cursor.fetchall,
        )

    async def fetchmany(self, size: int | None = None) -> list[tuple]:
        """Fetch many rows"""
        await self._ensure_cursor()
        loop = asyncio.get_event_loop()

        if size is None:
            size = self.cursor.arraysize

        return await loop.run_in_executor(
            self.executor,
            self.cursor.fetchmany,
            size,
        )

    @property
    def lastrowid(self) -> int | None:
        """Get last inserted row ID"""
        if self.cursor:
            return self.cursor.lastrowid
        return None

    @property
    def rowcount(self) -> int:
        """Get number of affected rows"""
        if self.cursor:
            return self.cursor.rowcount
        return -1

    async def close(self):
        """Close the cursor"""
        if self.cursor and not self._closed:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self.cursor.close,
            )
            self._closed = True


# Compatibility layer for gradual migration
class DBConnectionWrapper:
    """Wrapper to provide both sync and async interfaces during migration"""

    def __init__(self, async_conn: AsyncDBConnection):
        self.async_conn = async_conn

    # Sync methods for compatibility
    @property
    def conn(self):
        """Compatibility property"""
        return self

    def read_ctx(self) -> ContextManager[Cursor]:
        """Sync read context"""
        return self.async_conn.sync_read_ctx()

    def write_ctx(self) -> ContextManager[Cursor]:
        """Sync write context"""
        return self.async_conn.sync_write_ctx()

    # Async methods
    def async_read_ctx(self) -> AsyncGenerator['AsyncDBCursor', None]:
        """Async read context"""
        return self.async_conn.read_ctx()

    def async_write_ctx(self) -> AsyncGenerator['AsyncDBCursor', None]:
        """Async write context"""
        return self.async_conn.write_ctx()


# Compatibility exports for gradual migration
DBConnection = AsyncDBConnection
DBCursor = AsyncDBCursor
