from typing import TYPE_CHECKING

from rotkehlchen.globaldb.cache import compute_cache_key
from rotkehlchen.types import CacheType, ChainID

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


def globaldb_data_migration_2(conn: 'DBConnection') -> None:
    """Introduced at 1.36.0
    - Removes number of queried yearn vaults to ensure that a refresh is made and
    users get the staking vaults.
    """
    with conn.write_ctx() as write_cursor:
        # Remove old setting if existing
        write_cursor.executemany(
            'DELETE FROM unique_cache WHERE key=?',
            (
                (compute_cache_key((CacheType.YEARN_VAULTS,)),),
                (compute_cache_key((
                    CacheType.YEARN_VAULTS,
                    str(ChainID.ETHEREUM.serialize_for_db()),
                )),),
            ),
        )
