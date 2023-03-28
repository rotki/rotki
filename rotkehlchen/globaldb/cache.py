"""Functions dealing with the general_cache table of the Global DB"""
from collections.abc import Iterable
from typing import Optional, Union

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.types import ChecksumEvmAddress, GeneralCacheType, Timestamp
from rotkehlchen.utils.misc import ts_now

UNIQUE_CACHE_TABLE_NAME = 'unique_cache'
GENERAL_CACHE_TABLE_NAME = 'general_cache'
UNIQUE_CACHE_KEYS: set[GeneralCacheType] = {
    GeneralCacheType.CURVE_POOL_ADDRESS,
    GeneralCacheType.MAKERDAO_VAULT_ILK,
    GeneralCacheType.CURVE_GAUGE_ADDRESS,
}


def compute_cache_key(key_parts: Iterable[Union[str, GeneralCacheType]]) -> tuple[str, str]:
    """Function to compute cache key before accessing globaldb cache.
    Computes cache key by iterating through `key_parts` and making one string from them.
    Only tuple with the same values and the same order represents the same key. Also returns which
    cache table the data must be stored in."""
    unique_cache = list(key_parts)[0] in UNIQUE_CACHE_KEYS
    cache_table = UNIQUE_CACHE_TABLE_NAME if unique_cache else GENERAL_CACHE_TABLE_NAME
    cache_key = ''
    for part in key_parts:
        if isinstance(part, GeneralCacheType):
            cache_key += part.serialize()
        else:
            cache_key += part
    return cache_key, cache_table


# Using any random address here, since length of all addresses is the same
BASE_POOL_TOKENS_KEY_LENGTH = len(compute_cache_key([GeneralCacheType.CURVE_POOL_TOKENS, ZERO_ADDRESS])[0])  # noqa: E501


def globaldb_set_cache_values_at_ts(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        values: Iterable[str],
        timestamp: Timestamp,
) -> None:
    """Function to update cache in globaldb. Inserts all values paired with the cache key.
    If any entry exists, overwrites it."""
    cache_key, cache_table = compute_cache_key(key_parts)
    tuples = [(cache_key, value, timestamp) for value in values]
    write_cursor.executemany(
        f'INSERT OR REPLACE INTO {cache_table} '
        '(key, value, last_queried_ts) VALUES (?, ?, ?)',
        tuples,
    )


def globaldb_set_cache_values(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        values: Iterable[str],
) -> None:
    """Function to update cache in globaldb. Inserts all values paired with the cache key.
    If any entry exists, overwrites it. The timestamp is always the current time."""
    timestamp = ts_now()
    globaldb_set_cache_values_at_ts(
        write_cursor=write_cursor,
        key_parts=key_parts,
        values=values,
        timestamp=timestamp,
    )


def globaldb_get_cache_values(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[str]:
    """Function to read globaldb cache. Returns all the values that are paired with the key."""
    cache_key, cache_table = compute_cache_key(key_parts)
    cursor.execute(f'SELECT value FROM {cache_table} WHERE key=?', (cache_key,))
    return [entry[0] for entry in cursor]


def globaldb_get_general_cache_like(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[str]:
    """
    Function to read globaldb cache.
    Returns all values where key starts with the provided `key_parts`.

    key_parts should contain neither the "%" nor the "." symbol.
    """
    cache_key = compute_cache_key(key_parts)
    return cursor.execute(
        'SELECT value FROM general_cache WHERE key LIKE ?',
        (f'{cache_key}%',),
    ).fetchall()


def globaldb_get_cache_keys_and_values_like(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[tuple[str, str]]:
    """
    Function to read globaldb cache.
    Returns all pairs key-value where key starts with the provided `key_parts`.

    key_parts should contain neither the "%" nor the "." symbol.
    """
    cache_key, cache_table = compute_cache_key(key_parts)
    return cursor.execute(
        f'SELECT key, value FROM {cache_table} WHERE key LIKE ?',
        (f'{cache_key}%',),
    ).fetchall()


def globaldb_get_cache_last_queried_ts_by_key(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> Timestamp:
    """
    Get the last_queried_ts of the oldest stored element by key_parts. If there is no such
    element returns Timestamp(0)
    """
    cache_key, cache_table = compute_cache_key(key_parts)
    cursor.execute(
        f'SELECT last_queried_ts FROM {cache_table} WHERE key=? '
        'ORDER BY last_queried_ts ASC',
        (cache_key,),
    )
    result = cursor.fetchone()
    if result is None:
        return Timestamp(0)
    return Timestamp(result[0])


def read_curve_pool_tokens(
        cursor: 'DBCursor',
        pool_address: ChecksumEvmAddress,
) -> list[ChecksumEvmAddress]:
    """
    Reads tokens for a particular curve pool. Tokens are stored with their indices to make sure
    that the order of coins in pool contract and in our cache is the same. This functions reads
    and returns tokens in sorted order.
    """
    tokens_data = globaldb_get_cache_keys_and_values_like(
        cursor=cursor,
        key_parts=[GeneralCacheType.CURVE_POOL_TOKENS, pool_address],
    )
    found_tokens: list[tuple[int, ChecksumEvmAddress]] = []
    for key, address in tokens_data:
        index = int(key[BASE_POOL_TOKENS_KEY_LENGTH:])  # len(key) > BASE_POOL_TOKENS_KEY_LENGTH
        found_tokens.append((index, string_to_evm_address(address)))

    found_tokens.sort(key=lambda x: x[0])
    return [address for _, address in found_tokens]
