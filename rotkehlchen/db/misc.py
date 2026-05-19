"""A module with miscellaneous functions that do not depend on db/drivers/gevent.py
due. Needed in packaging since that code has log.trace and should only be
imported if trace level has been setup"""

import re
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlcipher3 import dbapi2 as sqlcipher


def get_sqlcipher_version_string() -> str:
    """Retrieve SQLCipher version used by the app"""
    conn = sqlcipher.connect(':memory:')  # pylint: disable=no-member
    version = conn.execute('PRAGMA cipher_version;').fetchone()[0]
    conn.close()
    return version


def detect_sqlcipher_version() -> int:
    """Returns the major part of the version for SQLCipher"""
    version = get_sqlcipher_version_string()
    if not (match := re.search(r'(\d+).(\d+).(\d+)', version)):
        raise ValueError(f'Could not process the version returned by SQLCipher: {version}')

    return int(match.group(1))


def evaluate_integrity_check_rows(rows: list[tuple[str, ...]]) -> tuple[bool, str | None]:
    """Inspect rows returned by `PRAGMA integrity_check` and return whether the DB is sound.

    A sound DB returns a single row with the value `ok`. Otherwise SQLite returns one or more
    rows describing what is wrong. We collapse them into a single message for logging.
    """
    if len(rows) == 1 and rows[0][0] == 'ok':
        return True, None
    return False, '; '.join(str(row[0]) for row in rows)


def plaintext_db_integrity_check(db_path: Path) -> tuple[bool, str | None]:
    """Run `PRAGMA integrity_check` on a plaintext sqlite database file at the given path.

    Returns (True, None) when sound and (False, error_message) otherwise. Any sqlite error
    raised while opening or running the pragma is also reported as a failure.
    """
    try:
        with closing(sqlite3.connect(db_path)) as conn:
            rows = conn.execute('PRAGMA integrity_check;').fetchall()
    except sqlite3.DatabaseError as e:
        return False, str(e)
    return evaluate_integrity_check_rows(rows)
