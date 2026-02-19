# ruff: noqa: INP001, T201
"""Seed rows into a SQLite or SQLCipher DB via JSON instructions on stdin.

Usage:
    uv run python seed-db.py <db_path> [password]

When a password is provided the DB is opened with SQLCipher (encrypted).
When omitted the DB is opened with plain sqlite3 (e.g. global.db).

Reads a JSON object from stdin with an "inserts" array. Each element:
    {
        "table": "evm_transactions",
        "columns": ["tx_hash", "chain_id", ...],
        "values": ["<hex:abcd>", 1, ...],
        "conflict": "ignore"          // optional: "ignore" | "replace"
    }

Values prefixed with "<hex:...>" are converted to bytes via bytes.fromhex().
"""

import json
import sqlite3
import sys

from sqlcipher3 import dbapi2 as sqlcipher  # type: ignore


def convert_value(v: object) -> object:
    """Convert hex-prefixed strings to bytes, pass everything else through."""
    if isinstance(v, str) and v.startswith('<hex:') and v.endswith('>'):
        return bytes.fromhex(v[5:-1])
    return v


def main() -> None:
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <db_path> [password]')
        sys.exit(1)

    db_path = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else None

    payload = json.load(sys.stdin)
    inserts = payload.get('inserts', [])

    if not inserts:
        print('No inserts provided')
        sys.exit(0)

    try:
        if password:
            conn = sqlcipher.connect(db_path)
        else:
            conn = sqlite3.connect(db_path)
    except (sqlcipher.OperationalError, sqlite3.OperationalError) as e:
        print(f'Failed to open database at: {db_path}', file=sys.stderr)
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)

    if password:
        conn.execute(f"PRAGMA key='{password}'")
    conn.execute('PRAGMA journal_mode=WAL')

    for entry in inserts:
        table = entry['table']
        columns = entry['columns']
        values = [convert_value(v) for v in entry['values']]
        conflict = entry.get('conflict')

        if conflict == 'ignore':
            verb = 'INSERT OR IGNORE INTO'
        elif conflict == 'replace':
            verb = 'INSERT OR REPLACE INTO'
        else:
            verb = 'INSERT INTO'

        placeholders = ', '.join('?' for _ in columns)
        col_list = ', '.join(columns)
        sql = f'{verb} {table} ({col_list}) VALUES ({placeholders})'

        conn.execute(sql, values)
        print(f'Inserted into {table} ({len(columns)} cols)')

    conn.commit()
    conn.close()
    print(f'Seeded {len(inserts)} row(s)')


if __name__ == '__main__':
    main()
