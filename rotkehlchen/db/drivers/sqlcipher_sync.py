"""Synchronous SQLCipher wrapper for use with asyncio via thread pool"""
import asyncio
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.checks import sanity_check_impl
from rotkehlchen.db.drivers.gevent import DBConnectionType
from rotkehlchen.db.minimized_schema import MINIMIZED_USER_DB_SCHEMA
from rotkehlchen.globaldb.minimized_schema import MINIMIZED_GLOBAL_DB_SCHEMA
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore


class SyncSQLCipherConnection:
    """Synchronous SQLCipher connection wrapper for use with thread pool executor
    
    This maintains the same interface as the gevent driver but runs synchronously
    in a thread pool when called from async code.
    """
    
    def __init__(
            self,
            path: str | Path,
            connection_type: DBConnectionType,
    ) -> None:
        self.path = path
        self.connection_type = connection_type
        self._conn: sqlcipher.Connection | sqlite3.Connection
        
        # Use regular SQLite for global DB, SQLCipher for others
        if connection_type == DBConnectionType.GLOBAL:
            self._conn = sqlite3.connect(
                database=str(path),
                check_same_thread=False,
                isolation_level=None,
            )
        else:
            self._conn = sqlcipher.connect(
                database=str(path),
                check_same_thread=False,
                isolation_level=None,
            )
            
        self.minimized_schema = None
        if connection_type == DBConnectionType.USER:
            self.minimized_schema = MINIMIZED_USER_DB_SCHEMA
        elif connection_type == DBConnectionType.GLOBAL:
            self.minimized_schema = MINIMIZED_GLOBAL_DB_SCHEMA
            
    def execute(self, statement: str, *bindings: Any) -> sqlite3.Cursor:
        """Execute a SQL statement"""
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'SYNC DB EXECUTE {statement}')  # type: ignore[attr-defined]
        return self._conn.execute(statement, *bindings)
    
    def executemany(self, statement: str, *bindings: Any) -> sqlite3.Cursor:
        """Execute a SQL statement with multiple parameter sets"""
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'SYNC DB EXECUTEMANY {statement}')  # type: ignore[attr-defined]
        return self._conn.executemany(statement, *bindings)
    
    def executescript(self, script: str) -> sqlite3.Cursor:
        """Execute a SQL script"""
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace(f'SYNC DB EXECUTESCRIPT {script}')  # type: ignore[attr-defined]
        return self._conn.executescript(script)
    
    def commit(self) -> None:
        """Commit the current transaction"""
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace('SYNC DB COMMIT')  # type: ignore[attr-defined]
        self._conn.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction"""
        if logger.isEnabledFor(logging.TRACE):  # type: ignore[attr-defined]
            logger.trace('SYNC DB ROLLBACK')  # type: ignore[attr-defined]
        self._conn.rollback()
    
    def close(self) -> None:
        """Close the database connection"""
        self._conn.close()
    
    @contextmanager
    def read_ctx(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for read operations"""
        cursor = self._conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    @contextmanager
    def write_ctx(self, commit_ts: bool = False) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for write operations with transaction"""
        cursor = self._conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        try:
            yield cursor
        except Exception:
            self._conn.rollback()
            raise
        else:
            if commit_ts:
                cursor.execute(
                    'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                    ('last_write_ts', str(ts_now())),
                )
            self._conn.commit()
        finally:
            cursor.close()
    
    @contextmanager
    def savepoint_ctx(
            self,
            savepoint_name: str | None = None,
    ) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for savepoint operations"""
        from uuid import uuid4
        
        if savepoint_name is None:
            savepoint_name = str(uuid4())
            
        cursor = self._conn.cursor()
        cursor.execute(f"SAVEPOINT '{savepoint_name}'")
        
        try:
            yield cursor
        except Exception:
            cursor.execute(f"ROLLBACK TO SAVEPOINT '{savepoint_name}'")
            raise
        else:
            cursor.execute(f"RELEASE SAVEPOINT '{savepoint_name}'")
        finally:
            cursor.close()
    
    @property
    def total_changes(self) -> int:
        """Total number of database rows that have been modified"""
        return self._conn.total_changes
    
    def schema_sanity_check(self) -> None:
        """Check database schema integrity"""
        assert (
            self.connection_type != DBConnectionType.TRANSIENT and
            self.minimized_schema is not None
        )
        
        with self.read_ctx() as cursor:
            sanity_check_impl(
                cursor=cursor,
                db_name=self.connection_type.name.lower(),
                minimized_schema=self.minimized_schema,
            )


class AsyncSQLCipherWrapper:
    """Async wrapper for SQLCipher operations using thread pool
    
    This provides an async interface while running SQLCipher operations
    synchronously in a thread pool, since SQLCipher doesn't support async.
    """
    
    def __init__(
            self,
            path: str | Path,
            connection_type: DBConnectionType,
            executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self.path = path
        self.connection_type = connection_type
        self.executor = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix='sqlcipher')
        self._sync_conn: SyncSQLCipherConnection | None = None
        self._loop = asyncio.get_event_loop()
        
    async def connect(self) -> None:
        """Establish database connection"""
        self._sync_conn = await self._loop.run_in_executor(
            self.executor,
            SyncSQLCipherConnection,
            self.path,
            self.connection_type,
        )
    
    async def execute(self, statement: str, *bindings: Any) -> Any:
        """Execute a SQL statement asynchronously"""
        if not self._sync_conn:
            raise RuntimeError("Database not connected")
            
        return await self._loop.run_in_executor(
            self.executor,
            self._sync_conn.execute,
            statement,
            *bindings,
        )
    
    async def executemany(self, statement: str, *bindings: Any) -> Any:
        """Execute a SQL statement with multiple parameter sets asynchronously"""
        if not self._sync_conn:
            raise RuntimeError("Database not connected")
            
        return await self._loop.run_in_executor(
            self.executor,
            self._sync_conn.executemany,
            statement,
            *bindings,
        )
    
    async def commit(self) -> None:
        """Commit the current transaction asynchronously"""
        if not self._sync_conn:
            raise RuntimeError("Database not connected")
            
        return await self._loop.run_in_executor(
            self.executor,
            self._sync_conn.commit,
        )
    
    async def rollback(self) -> None:
        """Rollback the current transaction asynchronously"""
        if not self._sync_conn:
            raise RuntimeError("Database not connected")
            
        return await self._loop.run_in_executor(
            self.executor,
            self._sync_conn.rollback,
        )
    
    async def close(self) -> None:
        """Close the database connection"""
        if self._sync_conn:
            await self._loop.run_in_executor(
                self.executor,
                self._sync_conn.close,
            )
            self._sync_conn = None
    
    # Context managers would need more complex implementation
    # to properly handle async context switching
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)