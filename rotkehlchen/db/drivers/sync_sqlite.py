"""Synchronous SQLite driver for backward compatibility

This is a simple sync-only SQLite driver for use in tests and
parts of the codebase that haven't been migrated to async yet.
"""
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from rotkehlchen.db.checks import sanity_check_impl_sync
from rotkehlchen.db.minimized_schema import MINIMIZED_USER_DB_SCHEMA
from rotkehlchen.globaldb.minimized_schema import MINIMIZED_GLOBAL_DB_SCHEMA
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.logging import RotkehlchenLogger

logger: 'RotkehlchenLogger' = logging.getLogger(__name__)  # type: ignore


class DBConnectionType(Enum):
    USER = auto()
    TRANSIENT = auto()
    GLOBAL = auto()


class DBCursor:
    """Wrapper for sync database cursor - provides compatibility interface"""
    
    def __init__(self, cursor: sqlite3.Cursor, connection: 'DBConnection'):
        self.cursor = cursor
        self.connection = connection
    
    def execute(self, statement: str, *bindings) -> 'DBCursor':
        self.cursor.execute(statement, *bindings)
        return self
    
    def executemany(self, statement: str, *bindings) -> 'DBCursor':
        self.cursor.executemany(statement, *bindings)
        return self
    
    def executescript(self, script: str) -> 'DBCursor':
        self.cursor.executescript(script)
        return self
    
    def fetchone(self) -> Any:
        return self.cursor.fetchone()
    
    def fetchall(self) -> list[Any]:
        return self.cursor.fetchall()
    
    def fetchmany(self, size: int | None = None) -> list[Any]:
        return self.cursor.fetchmany(size or self.cursor.arraysize)
    
    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount
    
    @property
    def lastrowid(self) -> int:
        return self.cursor.lastrowid
    
    def close(self) -> None:
        self.cursor.close()


class DBConnection:
    """Synchronous SQLite connection for backward compatibility"""
    
    def __init__(
        self,
        path: str | Path,
        connection_type: DBConnectionType,
        sql_vm_instructions_cb: int = 0,
    ):
        self.path = Path(path)
        self.connection_type = connection_type
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        
        # Set minimized schema based on connection type
        if connection_type == DBConnectionType.USER:
            self.minimized_schema = MINIMIZED_USER_DB_SCHEMA
        elif connection_type == DBConnectionType.GLOBAL:
            self.minimized_schema = MINIMIZED_GLOBAL_DB_SCHEMA
        else:
            self.minimized_schema = None
        
        # Open connection
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA cache_size=10000')
        self.conn.execute('PRAGMA page_size=4096')
        
        # Transaction management
        self.savepoints: dict[str, None] = {}
        self.savepoint_greenlet_id: int | None = None
    
    def execute(self, statement: str, *bindings) -> sqlite3.Cursor:
        """Execute a statement directly"""
        return self.conn.execute(statement, *bindings)
    
    def executescript(self, script: str) -> None:
        """Execute a script directly"""
        self.conn.executescript(script)
    
    def executemany(self, statement: str, *bindings) -> None:
        """Execute many statements directly"""
        self.conn.executemany(statement, *bindings)
    
    def commit(self) -> None:
        """Commit the current transaction"""
        self.conn.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction"""
        self.conn.rollback()
    
    def close(self) -> None:
        """Close the connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    @contextmanager
    def read_ctx(self) -> Generator[DBCursor, None, None]:
        """Context manager for read operations"""
        cursor = self.conn.cursor()
        db_cursor = DBCursor(cursor, self)
        try:
            yield db_cursor
        finally:
            cursor.close()
    
    @contextmanager
    def write_ctx(self, commit_ts: bool = False) -> Generator[DBCursor, None, None]:
        """Context manager for write operations with transaction"""
        cursor = self.conn.cursor()
        db_cursor = DBCursor(cursor, self)
        
        cursor.execute('BEGIN TRANSACTION')
        
        try:
            yield db_cursor
        except Exception:
            self.conn.rollback()
            raise
        else:
            if commit_ts:
                cursor.execute(
                    'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                    ('last_write_ts', str(ts_now())),
                )
            self.conn.commit()
        finally:
            cursor.close()
    
    def user_write(self, commit_ts: bool = True):
        """Alias for write_ctx - for compatibility"""
        return self.write_ctx(commit_ts=commit_ts)
    
    @contextmanager
    def savepoint_ctx(self, savepoint_name: str | None = None) -> Generator[DBCursor, None, None]:
        """Context manager for savepoint operations"""
        if savepoint_name is None:
            savepoint_name = str(uuid4())
        
        cursor = self.conn.cursor()
        db_cursor = DBCursor(cursor, self)
        
        # Create savepoint
        cursor.execute(f"SAVEPOINT '{savepoint_name}'")
        self.savepoints[savepoint_name] = None
        
        try:
            yield db_cursor
        except Exception:
            # Rollback to savepoint
            self.execute(f"ROLLBACK TO SAVEPOINT '{savepoint_name}'")
            raise
        else:
            # Release savepoint
            self.execute(f"RELEASE SAVEPOINT '{savepoint_name}'")
        finally:
            cursor.close()
            self.savepoints.pop(savepoint_name, None)
    
    @property
    def total_changes(self) -> int:
        """Total number of database rows that have been modified"""
        return self.conn.total_changes
    
    def schema_sanity_check(self) -> None:
        """Check database schema integrity"""
        assert (
            self.connection_type != DBConnectionType.TRANSIENT and
            self.minimized_schema is not None
        )
        
        with self.read_ctx() as cursor:
            sanity_check_impl_sync(
                cursor.cursor,  # Pass the underlying sqlite3 cursor
                self.connection_type.name.lower(),
                self.minimized_schema,
            )