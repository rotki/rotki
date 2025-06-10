"""Repository for managing database cache operations."""
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, Unpack, overload

from rotkehlchen.chain.evm.types import ChecksumEvmAddress
from rotkehlchen.db.cache import (
    AddressArgType,
    BinancePairLastTradeArgsType,
    DBCacheDynamic,
    DBCacheStatic,
    ExtraTxArgType,
    IndexArgType,
    LabeledLocationArgsType,
    LabeledLocationIdArgsType,
)
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class CacheRepository:
    """Repository for handling all cache-related database operations."""

    def get_cache_for_api(self, cursor: 'DBCursor') -> dict[str, int]:
        """Returns a few key-value pairs that are used in the API
        from the `key_value_cache` table of the DB. Defaults to `Timestamp(0)` if not found"""
        cursor.execute(
            'SELECT name, value FROM key_value_cache WHERE name IN (?,?);',
            (DBCacheStatic.LAST_DATA_UPLOAD_TS.value, DBCacheStatic.LAST_BALANCE_SAVE.value),
        )
        db_cache = {name: int(value) for name, value in cursor}
        return {  # Return with default value, if needed
            DBCacheStatic.LAST_BALANCE_SAVE.value: db_cache.get(DBCacheStatic.LAST_BALANCE_SAVE.value, 0),  # noqa: E501
            DBCacheStatic.LAST_DATA_UPLOAD_TS.value: db_cache.get(DBCacheStatic.LAST_DATA_UPLOAD_TS.value, 0),  # noqa: E501
        }

    def get_static(
            self,
            cursor: 'DBCursor',
            name: DBCacheStatic,
    ) -> Timestamp | None:
        """Returns the cache value from the `key_value_cache` table of the DB
        according to the given `name`. Defaults to `None` if not found"""
        value = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?;', (name.value,),
        ).fetchone()
        return None if value is None else Timestamp(int(value[0]))

    def set_static(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheStatic,
            value: Timestamp,
    ) -> None:
        """Save the name-value pair of the cache with constant name
        to the `key_value_cache` table of the DB"""
        write_cursor.execute(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            (name.value, value),
        )

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_CRYPTOTX_OFFSET],
            **kwargs: Unpack[LabeledLocationArgsType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.BINANCE_PAIR_LAST_ID],
            **kwargs: Unpack[BinancePairLastTradeArgsType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_TS],
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> Timestamp | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_ID],
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> str | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_BLOCK_ID],
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_TS],
            **kwargs: Unpack[AddressArgType],
    ) -> Timestamp | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_IDX],
            **kwargs: Unpack[AddressArgType],
    ) -> int | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.EXTRA_INTERNAL_TX],
            **kwargs: Unpack[ExtraTxArgType],
    ) -> ChecksumEvmAddress | None:
        ...

    @overload
    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS],
            **kwargs: Unpack[IndexArgType],
    ) -> Timestamp | None:
        ...

    def get_dynamic(
            self,
            cursor: 'DBCursor',
            name: DBCacheDynamic,
            **kwargs: Any,
    ) -> int | Timestamp | str | ChecksumEvmAddress | None:
        """Returns the cache value from the `key_value_cache` table of the DB
        according to the given `name` and `kwargs`. Defaults to `None` if not found."""
        value = cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?;', (name.get_db_key(**kwargs),),
        ).fetchone()
        return None if value is None else name.deserialize_callback(value[0])

    def delete_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheDynamic,
            **kwargs: str,
    ) -> None:
        """Delete the cache value from the `key_value_cache` table of the DB
        according to the given `name` and `kwargs` if it exists"""
        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name=?;', (name.get_db_key(**kwargs),),
        ).fetchone()

    @staticmethod
    def delete_dynamic_caches(
            write_cursor: 'DBCursor',
            key_parts: Sequence[str],
    ) -> None:
        """Delete cache entries whose names start with any of the given `key_parts`"""
        placeholders = ' OR '.join(['name LIKE ?'] * len(key_parts))
        write_cursor.execute(
            f'DELETE FROM key_value_cache WHERE {placeholders}',
            [f'{key_part}%' for key_part in key_parts],
        )

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_CRYPTOTX_OFFSET],
            value: int,
            **kwargs: Unpack[LabeledLocationArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.BINANCE_PAIR_LAST_ID],
            value: int,
            **kwargs: Unpack[BinancePairLastTradeArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_TS],
            value: Timestamp,
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_QUERY_ID],
            value: str,
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_BLOCK_ID],
            value: int,
            **kwargs: Unpack[LabeledLocationIdArgsType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_TS],
            value: Timestamp,
            **kwargs: Unpack[AddressArgType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.WITHDRAWALS_IDX],
            value: int,
            **kwargs: Unpack[AddressArgType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.EXTRA_INTERNAL_TX],
            value: ChecksumEvmAddress,
            **kwargs: Unpack[ExtraTxArgType],
    ) -> None:
        ...

    @overload
    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: Literal[DBCacheDynamic.LAST_PRODUCED_BLOCKS_QUERY_TS],
            value: Timestamp,
            **kwargs: Unpack[IndexArgType],
    ) -> None:
        ...

    def set_dynamic(
            self,
            write_cursor: 'DBCursor',
            name: DBCacheDynamic,
            value: int | Timestamp | str | ChecksumEvmAddress,
            **kwargs: Any,
    ) -> None:
        """Save the name-value pair of the cache with dynamic name
        to the `key_value_cache` table of the DB"""
        write_cursor.execute(
            'INSERT OR REPLACE INTO key_value_cache(name, value) VALUES(?, ?)',
            (name.get_db_key(**kwargs), value),
        )
