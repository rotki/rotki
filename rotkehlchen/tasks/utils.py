import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Final, Literal

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# The last-run timestamp keys that the task scheduler checks on every tick via
# should_run_periodic_task. Prefetching them all in a single query lets one scheduling pass
# avoid a separate key_value_cache read per task. This list is only an optimization hint: a key
# missing from it (or not yet set) still works, should_run_periodic_task falls back to a single
# DB read for it, so correctness never depends on this being complete.
SCHEDULER_PERIODIC_TASK_KEYS: Final = (
    DBCacheStatic.LAST_DATA_UPDATES_TS,
    DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS,
    DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY,
    DBCacheStatic.LAST_OWNED_ASSETS_UPDATE,
    DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE,
    DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
    DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
    DBCacheStatic.LAST_DELETE_PAST_CALENDAR_EVENTS,
    DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
    DBCacheStatic.LAST_ETH2_EVENTS_PROCESSING_TS,
    DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS,
)


def prefetch_scheduler_task_timestamps(database: 'DBHandler') -> dict[str, str]:
    """Read all periodic-task last-run timestamps the scheduler needs in a single query.

    The returned mapping is meant to be passed to should_run_periodic_task as cached_timestamps
    so a scheduling pass does not issue one key_value_cache read per task.
    """
    placeholders = ','.join('?' * len(SCHEDULER_PERIODIC_TASK_KEYS))
    with database.conn.read_ctx() as cursor:
        return dict(cursor.execute(
            f'SELECT name, value FROM key_value_cache WHERE name IN ({placeholders})',
            [key.value for key in SCHEDULER_PERIODIC_TASK_KEYS],
        ))


def should_run_periodic_task(
        database: 'DBHandler',
        key_name: Literal[
            DBCacheStatic.LAST_DATA_UPDATES_TS,
            DBCacheStatic.LAST_EVM_ACCOUNTS_DETECT_TS,
            DBCacheStatic.LAST_SPAM_ASSETS_DETECT_KEY,
            DBCacheStatic.LAST_AUGMENTED_SPAM_ASSETS_DETECT_KEY,
            DBCacheStatic.LAST_OWNED_ASSETS_UPDATE,
            DBCacheStatic.LAST_MONERIUM_QUERY_TS,
            DBCacheStatic.LAST_AAVE_V3_ASSETS_UPDATE,
            DBCacheStatic.LAST_DELETE_PAST_CALENDAR_EVENTS,
            DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
            DBCacheStatic.LAST_GRAPH_DELEGATIONS_CHECK_TS,
            DBCacheStatic.LAST_GNOSISPAY_QUERY_TS,
            DBCacheStatic.LAST_SPARK_ASSETS_UPDATE,
            DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
            DBCacheStatic.LAST_ETH2_EVENTS_PROCESSING_TS,
            DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS,
        ],
        refresh_period: int,
        cached_timestamps: Mapping[str, str] | None = None,
) -> bool:
    """
    Checks if enough time has elapsed since the last run of a periodic task in order to run
    it again.

    cached_timestamps is an optional name -> value map of already-read key_value_cache entries
    (see prefetch_scheduler_task_timestamps). When the key is present there the in-memory value
    is used; otherwise we fall back to a single DB read so correctness does not depend on the
    prefetch containing every key.
    """
    if cached_timestamps is not None and (last_update_str := cached_timestamps.get(key_name.value)) is not None:  # noqa: E501
        return ts_now() - deserialize_timestamp(last_update_str) >= refresh_period

    with database.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM key_value_cache WHERE name=?', (key_name.value,))
        timestamp_in_db = cursor.fetchone()

    if timestamp_in_db is None:
        return True

    last_update_ts = deserialize_timestamp(timestamp_in_db[0])
    return ts_now() - last_update_ts >= refresh_period
