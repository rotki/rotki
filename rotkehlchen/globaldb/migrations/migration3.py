from typing import TYPE_CHECKING

from rotkehlchen.types import CacheType

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


def globaldb_data_migration_3(conn: 'DBConnection') -> None:
    """Introduced in 1.39.0

    - Clears Velodrome/Aerodrome pool and gauge cache entries to ensure a full refresh.
    Previously, fee and bribe addresses were not stored, so this forces an update
    to include them where available.
    """
    with conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE FROM general_cache WHERE key IN (?, ?, ?, ?)',
            (
                CacheType.VELODROME_POOL_ADDRESS.serialize(),
                CacheType.VELODROME_GAUGE_ADDRESS.serialize(),
                CacheType.AERODROME_POOL_ADDRESS.serialize(),
                CacheType.AERODROME_GAUGE_ADDRESS.serialize(),
            ),
        )
