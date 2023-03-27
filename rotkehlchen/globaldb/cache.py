"""Functions dealing with the general_cache table of the Global DB"""
from collections.abc import Iterable
from typing import Optional, Union

from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.types import GeneralCacheType, Timestamp
from rotkehlchen.utils.misc import ts_now


def _compute_cache_key(key_parts: Iterable[Union[str, GeneralCacheType]]) -> str:
    """Function to compute cache key before accessing globaldb cache.
    Computes cache key by iterating through `key_parts` and making one string from them.
    Only tuple with the same values and the same order represents the same key."""
    cache_key = ''
    for part in key_parts:
        if isinstance(part, GeneralCacheType):
            cache_key += part.serialize()
        else:
            cache_key += part
    return cache_key


def globaldb_set_general_cache_values_at_ts(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        values: Iterable[str],
        timestamp: Timestamp,
) -> None:
    """Function to update cache in globaldb. Inserts all values paired with the cache key.
    If any entry exists, overwrites it."""
    cache_key = _compute_cache_key(key_parts)
    tuples = [(cache_key, value, timestamp) for value in values]
    write_cursor.executemany(
        'INSERT OR REPLACE INTO general_cache '
        '(key, value, last_queried_ts) VALUES (?, ?, ?)',
        tuples,
    )


def globaldb_set_general_cache_values(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        values: Iterable[str],
) -> None:
    """Function to update cache in globaldb. Inserts all values paired with the cache key.
    If any entry exists, overwrites it. The timestamp is always the current time."""
    timestamp = ts_now()
    globaldb_set_general_cache_values_at_ts(
        write_cursor=write_cursor,
        key_parts=key_parts,
        values=values,
        timestamp=timestamp,
    )


def globaldb_get_general_cache_values(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[str]:
    """Function to read globaldb cache. Returns all the values that are paired with the key."""
    cache_key = _compute_cache_key(key_parts)
    cursor.execute('SELECT value FROM general_cache WHERE key=?', (cache_key,))
    return [entry[0] for entry in cursor]


def globaldb_get_general_cache_last_queried_ts(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        value: str,
) -> Optional[Timestamp]:
    """Function to get timestamp at which pair key - value was queried last time."""
    cache_key = _compute_cache_key(key_parts)
    cursor.execute(
        'SELECT last_queried_ts FROM general_cache WHERE key=? AND value=?',
        (cache_key, value),
    )
    result = cursor.fetchone()
    if result is None:
        return None
    return Timestamp(result[0])


def globaldb_get_general_cache_last_queried_ts_by_key(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> Timestamp:
    """
    Get the last_queried_ts of the oldest stored element by key_parts. If there is no such
    element returns Timestamp(0)
    """
    cache_key = _compute_cache_key(key_parts)
    cursor.execute(
        'SELECT last_queried_ts FROM general_cache WHERE key=? '
        'ORDER BY last_queried_ts ASC',
        (cache_key,),
    )
    result = cursor.fetchone()
    if result is None:
        return Timestamp(0)
    return Timestamp(result[0])


def globaldb_delete_general_cache(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        value: Optional[str] = None,
) -> None:
    """Deletes from cache in globaldb. If value is None deletes all entries with the provided
    cache key. Otherwise, deletes only single entry `key - value`."""
    cache_key = _compute_cache_key(key_parts)
    if value is None:
        write_cursor.execute('DELETE FROM general_cache WHERE key=?', (cache_key,))
    else:
        write_cursor.execute('DELETE FROM general_cache WHERE key=? AND value=?', (cache_key, value))  # noqa: E501
