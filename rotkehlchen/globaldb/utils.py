from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor

GLOBAL_DB_VERSION = 3
MIN_SUPPORTED_GLOBAL_DB_VERSION = 2


def _get_setting_value(cursor: 'DBCursor', name: str, default_value: int) -> int:
    query = cursor.execute(
        'SELECT value FROM settings WHERE name=?;', (name,),
    )
    result = query.fetchall()
    # If setting is not set, it's the default
    if len(result) == 0:
        return default_value

    return int(result[0][0])


def _add_setting_value(write_cursor: 'DBCursor', name: str, value: int) -> None:
    write_cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
        (name, value),
    )


def _delete_setting_value(write_cursor: 'DBCursor', name: str) -> None:
    write_cursor.execute('DELETE FROM settings WHERE name=?', (name,))
