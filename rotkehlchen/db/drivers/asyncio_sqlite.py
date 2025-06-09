"""AsyncIO-based SQLite driver to replace the gevent implementation

This implementation doesn't need progress handlers because asyncio naturally
yields control at await points. Long-running queries are handled by running
them in a thread pool executor.
"""
import asyncio
import logging
import sqlite3
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

import aiosqlite
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.checks import sanity_check_impl
from rotkehlchen.db.drivers.gevent import DBConnectionType
from rotkehlchen.db.minimized_schema import MINIMIZED_USER_DB_SCHEMA
from rotkehlchen.globaldb.minimized_schema import MINIMIZED_GLOBAL_DB_SCHEMA
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore


class AsyncDBCursor:
    """Async wrapper for database cursor operations"""
    
    def __init__(self, cursor: aiosqlite.Cursor, connection: 'AsyncDBConnection'):
        self._cursor = cursor
        self.connection = connection
        
    async def execute(self, statement: str, *bindings: Sequence) -> 'AsyncDBCursor':
        """Execute a SQL statement
        
        Unlike gevent version, this naturally yields control during execution
        without needing progress callbacks.
        """
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'ASYNC EXECUTE {statement}')  # type: ignore[attr-defined]
        
        await self._cursor.execute(statement, *bindings)
        
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'FINISH ASYNC EXECUTE {statement}')  # type: ignore[attr-defined]
        return self
    
    async def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> 'AsyncDBCursor':
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'ASYNC EXECUTEMANY {statement}')  # type: ignore[attr-defined]
            
        await self._cursor.executemany(statement, *bindings)
        
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'FINISH ASYNC EXECUTEMANY {statement}')  # type: ignore[attr-defined]
        return self
    
    async def executescript(self, script: str) -> 'AsyncDBCursor':
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'ASYNC EXECUTESCRIPT {script}')  # type: ignore[attr-defined]
            
        await self._cursor.executescript(script)
        
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'FINISH ASYNC EXECUTESCRIPT {script}')  # type: ignore[attr-defined]
        return self
    
    async def fetchone(self) -> Any:
        return await self._cursor.fetchone()
    
    async def fetchmany(self, size: int | None = None) -> list[Any]:
        return await self._cursor.fetchmany(size or self._cursor.arraysize)
    
    async def fetchall(self) -> list[Any]:
        return await self._cursor.fetchall()
    
    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount
    
    @property
    def lastrowid(self) -> int:
        return self._cursor.lastrowid
    
    async def close(self) -> None:
        await self._cursor.close()


class AsyncDBConnection:
    """Asyncio replacement for gevent DBConnection
    
    Key differences from gevent version:
    1. No progress handler needed - asyncio yields naturally at await points
    2. No complex callback mechanism or CONNECTION_MAP
    3. Uses asyncio locks instead of gevent semaphores
    4. Thread pool executor for SQLCipher (until async version available)
    """
    
    def __init__(
            self,
            path: str | Path,
            connection_type: DBConnectionType,
            sql_vm_instructions_cb: int | None = None,  # Kept for compatibility, ignored
    ) -> None:
        self.path = str(path)
        self.connection_type = connection_type
        self._conn: aiosqlite.Connection | None = None
        
        # Async locks instead of gevent semaphores
        self.transaction_lock = asyncio.Lock()
        
        # Savepoint tracking (same as gevent version)
        self.savepoints: dict[str, None] = {}
        self.savepoint_task_id: int | None = None
        self.write_task_id: int | None = None
        
        # Schema for validation
        self.minimized_schema = None
        if connection_type == DBConnectionType.USER:
            self.minimized_schema = MINIMIZED_USER_DB_SCHEMA
        elif connection_type == DBConnectionType.GLOBAL:
            self.minimized_schema = MINIMIZED_GLOBAL_DB_SCHEMA
    
    async def connect(self) -> None:
        """Establish database connection"""
        if self.connection_type == DBConnectionType.GLOBAL:
            # Regular SQLite for global DB
            self._conn = await aiosqlite.connect(
                self.path,
                isolation_level=None,
            )
        else:
            # For user/transient DB with SQLCipher, we need a different approach
            # Since aiosqlcipher doesn't exist, we'll use thread pool
            # This is handled in a separate implementation
            raise NotImplementedError(
                "SQLCipher support requires thread pool implementation. "
                "Use AsyncSQLCipherWrapper from sqlcipher_sync.py"
            )
        
        # Set pragmas for performance (similar to gevent version)
        await self._conn.execute('PRAGMA journal_mode=WAL')
        await self._conn.execute('PRAGMA synchronous=NORMAL')
        await self._conn.execute('PRAGMA cache_size=10000')
        await self._conn.execute('PRAGMA page_size=4096')
    
    async def execute(self, statement: str, *bindings: Sequence) -> AsyncDBCursor:
        """Execute a SQL statement"""
        if not self._conn:
            raise RuntimeError("Database not connected")
        
        cursor = await self._conn.execute(statement, *bindings)
        return AsyncDBCursor(cursor, self)
    
    async def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> AsyncDBCursor:
        """Execute a SQL statement with multiple parameter sets"""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        cursor = await self._conn.executemany(statement, *bindings)
        return AsyncDBCursor(cursor, self)
    
    async def executescript(self, script: str) -> AsyncDBCursor:
        """Execute a SQL script"""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        cursor = await self._conn.executescript(script)
        return AsyncDBCursor(cursor, self)
    
    async def commit(self) -> None:
        """Commit the current transaction"""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace('ASYNC DB COMMIT')  # type: ignore[attr-defined]
            
        await self._conn.commit()
    
    async def rollback(self) -> None:
        """Rollback the current transaction"""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace('ASYNC DB ROLLBACK')  # type: ignore[attr-defined]
            
        await self._conn.rollback()
    
    async def close(self) -> None:
        """Close the database connection"""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    @asynccontextmanager
    async def read_ctx(self) -> AsyncGenerator[AsyncDBCursor, None]:
        """Context manager for read operations"""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        cursor = await self._conn.cursor()
        async_cursor = AsyncDBCursor(cursor, self)
        try:
            yield async_cursor
        finally:
            await async_cursor.close()
    
    @asynccontextmanager
    async def write_ctx(self, commit_ts: bool = False) -> AsyncGenerator[AsyncDBCursor, None]:
        """Context manager for write operations with transaction
        
        This replaces the complex gevent version with simpler async logic.
        No need for greenlet tracking or complex locking.
        """
        if not self._conn:
            raise RuntimeError("Database not connected")
        
        current_task_id = id(asyncio.current_task())
        
        # Handle nested savepoints (same logic as gevent version)
        if len(self.savepoints) != 0:
            if current_task_id != self.savepoint_task_id:
                # Wait for other task's savepoint
                while self.savepoint_task_id is not None:
                    await asyncio.sleep(0.01)
            else:
                # Use savepoint instead
                async with self.savepoint_ctx() as cursor:
                    yield cursor
                    return
        
        async with self.transaction_lock:
            cursor = await self._conn.cursor()
            async_cursor = AsyncDBCursor(cursor, self)
            self.write_task_id = current_task_id
            
            await async_cursor.execute('BEGIN TRANSACTION')
            
            try:
                yield async_cursor
            except Exception:
                await self.rollback()
                raise
            else:
                if commit_ts:
                    await async_cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        ('last_write_ts', str(ts_now())),
                    )
                await self.commit()
            finally:
                await async_cursor.close()
                self.write_task_id = None
    
    @asynccontextmanager
    async def savepoint_ctx(
            self,
            savepoint_name: str | None = None,
    ) -> AsyncGenerator[AsyncDBCursor, None]:
        """Context manager for savepoint operations"""
        if not self._conn:
            raise RuntimeError("Database not connected")
            
        if savepoint_name is None:
            savepoint_name = str(uuid4())
        
        cursor = await self._conn.cursor()
        async_cursor = AsyncDBCursor(cursor, self)
        
        # Create savepoint
        await async_cursor.execute(f"SAVEPOINT '{savepoint_name}'")
        self.savepoints[savepoint_name] = None
        self.savepoint_task_id = id(asyncio.current_task())
        
        try:
            yield async_cursor
        except Exception:
            # Rollback to savepoint
            await self.execute(f"ROLLBACK TO SAVEPOINT '{savepoint_name}'")
            raise
        else:
            # Release savepoint
            await self.execute(f"RELEASE SAVEPOINT '{savepoint_name}'")
        finally:
            await async_cursor.close()
            self.savepoints.pop(savepoint_name, None)
            if len(self.savepoints) == 0:
                self.savepoint_task_id = None
    
    @property
    def total_changes(self) -> int:
        """Total number of database rows that have been modified"""
        if not self._conn:
            return 0
        return self._conn.total_changes
    
    async def schema_sanity_check(self) -> None:
        """Check database schema integrity"""
        assert (
            self.connection_type != DBConnectionType.TRANSIENT and
            self.minimized_schema is not None
        )
        
        async with self.read_ctx() as cursor:
            # Would need async version of sanity_check_impl
            # For now, run in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                sanity_check_impl,
                cursor._cursor,  # Pass underlying sync cursor
                self.connection_type.name.lower(),
                self.minimized_schema,
            )


# Migration comparison example
"""
Key differences from gevent implementation:

1. Progress Handler Removal:
   Gevent: Uses sqlite3 progress_handler with callbacks for context switching
   AsyncIO: Natural yielding at await points, no callbacks needed

2. Connection Management:
   Gevent: Global CONNECTION_MAP and callback routing
   AsyncIO: Simple connection instances, no global state

3. Concurrency Control:
   Gevent: Semaphores and greenlet IDs
   AsyncIO: Native async locks and task IDs

4. Context Switching:
   Gevent: gevent.sleep(0) in callbacks
   AsyncIO: await naturally yields control

5. Critical Sections:
   Gevent: Complex progress handler manipulation
   AsyncIO: Not needed - async operations are naturally cooperative
"""