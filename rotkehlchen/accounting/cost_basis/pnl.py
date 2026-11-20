"""Track the unprocessed portion of materialized cost basis."""
from typing import TYPE_CHECKING

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.types import TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor


def get_unprocessed_from_ts(
        cursor: DBCursor,
        database: DBHandler,
) -> TimestampMS | None:
    """The timestamp from which events still need cost basis processing, or None if none do.

    Includes the progress of an unfinished pass while nothing has changed since it started.
    """
    (
        stale_from_ts,
        last_processing_ts,
        modification_ts,
        pass_processed_ts,
        pass_modification_ts,
    ) = database.get_static_caches(
        cursor=cursor,
        names=(
            DBCacheStatic.STALE_COST_BASIS_FROM_TS,
            DBCacheStatic.LAST_COST_BASIS_PROCESSING_TS,
            DBCacheStatic.STALE_COST_BASIS_MODIFICATION_TS,
            DBCacheStatic.COST_BASIS_PASS_PROCESSED_TS,
            DBCacheStatic.COST_BASIS_PASS_MODIFICATION_TS,
        ),
    )
    unprocessed_from_ts = (
        0 if last_processing_ts is None
        else None if stale_from_ts is None
        else int(stale_from_ts)
    )
    if (
        unprocessed_from_ts is not None and
        pass_processed_ts is not None and
        pass_modification_ts == (modification_ts or '0')
    ):
        unprocessed_from_ts = max(unprocessed_from_ts, int(pass_processed_ts))

    return None if unprocessed_from_ts is None else TimestampMS(unprocessed_from_ts)
