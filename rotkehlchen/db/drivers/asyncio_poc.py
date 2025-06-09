"""Proof of concept for asyncio-based SQLite driver to replace gevent implementation"""

import asyncio
import logging
import sqlite3
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from enum import Enum, auto
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal, Optional, TypeAlias
from uuid import uuid4

import aiosqlite
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.checks import sanity_check_impl
from rotkehlchen.db.minimized_schema import MINIMIZED_USER_DB_SCHEMA
from rotkehlchen.globaldb.minimized_schema import MINIMIZED_GLOBAL_DB_SCHEMA
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor
UnderlyingConnection: TypeAlias = aiosqlite.Connection

logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore


class ContextError(Exception):
    """Raised when something is wrong with db context management"""


class AsyncDBCursor:
    """Async wrapper for database cursor operations"""
    
    def __init__(self, connection: 'AsyncDBConnection', cursor: aiosqlite.Cursor) -> None:
        self._cursor = cursor
        self.connection = connection

    def __aiter__(self) -> 'AsyncDBCursor':
        if __debug__:
            logger.trace(f'Getting async iterator for cursor {self._cursor}')
        return self

    async def __anext__(self) -> Any:
        if __debug__:
            logger.trace(f'Get next item for cursor {self._cursor}')
        result = await self._cursor.fetchone()
        if result is None:
            if __debug__:
                logger.trace(f'Stopping iteration for cursor {self._cursor}')
            raise StopAsyncIteration
        
        if __debug__:
            logger.trace(f'Got next item for cursor {self._cursor}')
        return result

    async def __aenter__(self) -> 'AsyncDBCursor':
        return self

    async def __aexit__(
            self,
            exctype: type[BaseException] | None,
            value: BaseException | None,
            traceback: TracebackType | None,
    ) -> Literal[False]:
        await self.close()
        return False

    async def execute(self, statement: str, *bindings: Sequence) -> 'AsyncDBCursor':
        if __debug__:
            logger.trace(f'EXECUTE {statement}')
        try:
            await self._cursor.execute(statement, *bindings)
        except sqlite3.InterfaceError:
            logger.debug(f'{statement} with {bindings} failed. Retrying')
            await self._cursor.execute(statement, *bindings)
        
        if __debug__:
            logger.trace(f'FINISH EXECUTE {statement}')
        return self

    async def executemany(
            self,
            statement: str,
            *bindings: Sequence[Sequence],
    ) -> 'AsyncDBCursor':
        if __debug__:
            logger.trace(f'EXECUTEMANY {statement}')
        await self._cursor.executemany(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH EXECUTEMANY {statement}')
        return self

    async def executescript(self, script: str) -> 'AsyncDBCursor':
        if __debug__:
            logger.trace(f'EXECUTESCRIPT {script}')
        await self._cursor.executescript(script)
        if __debug__:
            logger.trace(f'FINISH EXECUTESCRIPT {script}')
        return self

    async def switch_foreign_keys(
            self,
            on_or_off: Literal['ON', 'OFF'],
            restart_transaction: bool = True,
    ) -> None:
        await self.executescript(f'PRAGMA foreign_keys={on_or_off};')
        if restart_transaction is True:
            await self.execute('BEGIN TRANSACTION')

    async def fetchone(self) -> Any:
        if __debug__:
            logger.trace('CURSOR FETCHONE')
        result = await self._cursor.fetchone()
        if __debug__:
            logger.trace('FINISH CURSOR FETCHONE')
        return result

    async def fetchmany(self, size: int | None = None) -> list[Any]:
        if __debug__:
            logger.trace(f'CURSOR FETCHMANY with {size=}')
        if size is None:
            size = self._cursor.arraysize
        result = await self._cursor.fetchmany(size)
        if __debug__:
            logger.trace('FINISH CURSOR FETCHMANY')
        return result

    async def fetchall(self) -> list[Any]:
        if __debug__:
            logger.trace('CURSOR FETCHALL')
        result = await self._cursor.fetchall()
        if __debug__:
            logger.trace('FINISH CURSOR FETCHALL')
        return result

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def lastrowid(self) -> int:
        return self._cursor.lastrowid

    async def close(self) -> None:
        await self._cursor.close()


class DBConnectionType(Enum):
    USER = auto()
    TRANSIENT = auto()
    GLOBAL = auto()


class AsyncDBConnection:
    """Asyncio-based database connection replacing gevent implementation"""
    
    def __init__(
            self,
            path: str | Path,
            connection_type: DBConnectionType,
    ) -> None:
        self._conn: UnderlyingConnection | None = None
        self._path = path
        self.connection_type = connection_type
        self.transaction_lock = asyncio.Lock()
        self.savepoints: dict[str, None] = {}
        self.savepoint_task_id: int | None = None
        self.write_task_id: int | None = None
        self.minimized_schema = None
        if connection_type == DBConnectionType.USER:
            self.minimized_schema = MINIMIZED_USER_DB_SCHEMA
        elif connection_type == DBConnectionType.GLOBAL:
            self.minimized_schema = MINIMIZED_GLOBAL_DB_SCHEMA
    
    async def connect(self) -> None:
        """Establish the database connection"""
        if self.connection_type == DBConnectionType.GLOBAL:
            # For global DB, use regular SQLite
            self._conn = await aiosqlite.connect(
                database=self._path,
                isolation_level=None,
            )
        else:
            # For user/transient DB, would need aiosqlcipher (not available)
            # This is a limitation that needs to be addressed
            # For POC, using regular aiosqlite
            self._conn = await aiosqlite.connect(
                database=str(self._path),
                isolation_level=None,
            )
    
    async def execute(self, statement: str, *bindings: Sequence) -> AsyncDBCursor:
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTE {statement}')
        if self._conn is None:
            raise RuntimeError("Database connection not established")
        
        cursor = await self._conn.execute(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTE {statement}')
        return AsyncDBCursor(connection=self, cursor=cursor)
    
    async def executemany(self, statement: str, *bindings: Sequence[Sequence]) -> AsyncDBCursor:
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTEMANY {statement}')
        if self._conn is None:
            raise RuntimeError("Database connection not established")
            
        cursor = await self._conn.executemany(statement, *bindings)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTEMANY {statement}')
        return AsyncDBCursor(connection=self, cursor=cursor)
    
    async def executescript(self, script: str) -> AsyncDBCursor:
        if __debug__:
            logger.trace(f'DB CONNECTION EXECUTESCRIPT {script}')
        if self._conn is None:
            raise RuntimeError("Database connection not established")
            
        cursor = await self._conn.executescript(script)
        if __debug__:
            logger.trace(f'FINISH DB CONNECTION EXECUTESCRIPT {script}')
        return AsyncDBCursor(connection=self, cursor=cursor)
    
    async def commit(self) -> None:
        if __debug__:
            logger.trace('START DB CONNECTION COMMIT')
        if self._conn is None:
            raise RuntimeError("Database connection not established")
            
        try:
            await self._conn.commit()
        finally:
            if __debug__:
                logger.trace('FINISH DB CONNECTION COMMIT')
    
    async def rollback(self) -> None:
        if __debug__:
            logger.trace('START DB CONNECTION ROLLBACK')
        if self._conn is None:
            raise RuntimeError("Database connection not established")
            
        try:
            await self._conn.rollback()
        finally:
            if __debug__:
                logger.trace('FINISH DB CONNECTION ROLLBACK')
    
    async def cursor(self) -> AsyncDBCursor:
        if self._conn is None:
            raise RuntimeError("Database connection not established")
        cursor = await self._conn.cursor()
        return AsyncDBCursor(connection=self, cursor=cursor)
    
    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
    
    @asynccontextmanager
    async def read_ctx(self) -> AsyncGenerator[AsyncDBCursor, None]:
        cursor = await self.cursor()
        try:
            yield cursor
        finally:
            await cursor.close()
    
    @asynccontextmanager
    async def write_ctx(self, commit_ts: bool = False) -> AsyncGenerator[AsyncDBCursor, None]:
        """Opens a transaction to the database"""
        current_task_id = id(asyncio.current_task())
        
        # Handle nested savepoints
        if len(self.savepoints) != 0:
            if current_task_id != self.savepoint_task_id:
                # Wait for other task's savepoint to complete
                while self.savepoint_task_id is not None:
                    await asyncio.sleep(0.1)
            else:
                # Use savepoint instead of transaction
                async with self.savepoint_ctx() as cursor:
                    yield cursor
                    return
        
        async with self.transaction_lock:
            cursor = await self.cursor()
            self.write_task_id = current_task_id
            await cursor.execute('BEGIN TRANSACTION')
            try:
                yield cursor
            except Exception:
                await self.rollback()
                raise
            else:
                if commit_ts is True:
                    await cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        ('last_write_ts', str(ts_now())),
                    )
                await self.commit()
            finally:
                await cursor.close()
                self.write_task_id = None
    
    @asynccontextmanager
    async def savepoint_ctx(
            self,
            savepoint_name: str | None = None,
    ) -> AsyncGenerator[AsyncDBCursor, None]:
        """Creates a savepoint context with the provided name"""
        cursor, savepoint_name = await self._enter_savepoint(savepoint_name)
        try:
            yield cursor
        except Exception:
            await self.rollback_savepoint(savepoint_name)
            raise
        finally:
            await self.release_savepoint(savepoint_name)
            await cursor.close()
    
    async def _enter_savepoint(self, savepoint_name: str | None = None) -> tuple[AsyncDBCursor, str]:
        if savepoint_name is None:
            savepoint_name = str(uuid4())
        
        current_task_id = id(asyncio.current_task())
        
        # Wait for write transaction in other task
        if self._conn and self.write_task_id != current_task_id:
            while self.write_task_id is not None:
                await asyncio.sleep(0.1)
        
        # Wait for savepoints in other task
        if self.savepoint_task_id is not None and current_task_id != self.savepoint_task_id:
            while self.savepoint_task_id is not None:
                await asyncio.sleep(0.1)
        
        if savepoint_name in self.savepoints:
            raise ContextError(f'Savepoint {savepoint_name} already exists')
        
        cursor = await self.cursor()
        await cursor.execute(f"SAVEPOINT '{savepoint_name}'")
        self.savepoints[savepoint_name] = None
        self.savepoint_task_id = current_task_id
        return cursor, savepoint_name
    
    async def _modify_savepoint(
            self,
            rollback_or_release: Literal['ROLLBACK TO', 'RELEASE'],
            savepoint_name: str | None,
    ) -> None:
        if len(self.savepoints) == 0:
            raise ContextError(f'Cannot {rollback_or_release.lower()} - no savepoints exist')
        
        list_savepoints = list(self.savepoints)
        if savepoint_name is None:
            savepoint_name = list_savepoints[-1]
        elif savepoint_name not in self.savepoints:
            raise ContextError(f'Savepoint {savepoint_name} not found')
        
        await self.execute(f"{rollback_or_release} SAVEPOINT '{savepoint_name}'")
        
        if rollback_or_release == 'RELEASE':
            # Remove released savepoints
            idx = list_savepoints.index(savepoint_name)
            self.savepoints = dict.fromkeys(list_savepoints[:idx])
            if len(self.savepoints) == 0:
                self.savepoint_task_id = None
    
    async def rollback_savepoint(self, savepoint_name: str | None = None) -> None:
        await self._modify_savepoint('ROLLBACK TO', savepoint_name)
    
    async def release_savepoint(self, savepoint_name: str | None = None) -> None:
        await self._modify_savepoint('RELEASE', savepoint_name)
    
    @property
    async def total_changes(self) -> int:
        if self._conn is None:
            raise RuntimeError("Database connection not established")
        return self._conn.total_changes
    
    async def schema_sanity_check(self) -> None:
        assert (
            self.connection_type != DBConnectionType.TRANSIENT and
            self.minimized_schema is not None
        )
        
        async with self.read_ctx() as cursor:
            # Note: sanity_check_impl would need to be made async
            # For POC, showing the structure
            pass


# Example usage demonstrating the async API
async def example_usage():
    """Example showing how to use the async database connection"""
    # Create and connect to database
    db = AsyncDBConnection('test.db', DBConnectionType.GLOBAL)
    await db.connect()
    
    try:
        # Read context
        async with db.read_ctx() as cursor:
            await cursor.execute('SELECT * FROM users WHERE id = ?', (1,))
            user = await cursor.fetchone()
            print(f"User: {user}")
        
        # Write context with automatic transaction
        async with db.write_ctx() as cursor:
            await cursor.execute(
                'INSERT INTO users (name, email) VALUES (?, ?)',
                ('Alice', 'alice@example.com')
            )
        
        # Savepoint example
        async with db.write_ctx() as cursor:
            await cursor.execute('UPDATE users SET active = 1')
            
            async with db.savepoint_ctx('test_savepoint') as sp_cursor:
                await sp_cursor.execute('DELETE FROM users WHERE id = 5')
                # This will rollback only the DELETE, not the UPDATE
                raise Exception("Oops!")
        
    finally:
        await db.close()


# Comparison with gevent approach:
# 1. No monkey patching required
# 2. No progress callbacks needed (asyncio handles yielding)
# 3. Uses standard asyncio primitives (Lock instead of Semaphore)
# 4. Task identification via asyncio.current_task() instead of greenlet IDs
# 5. Explicit async/await makes control flow clearer