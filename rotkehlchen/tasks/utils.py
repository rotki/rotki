import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
        ],
        refresh_period: int,
) -> bool:
    """
    Checks if enough time has elapsed since the last run of a periodic task in order to run
    it again.
    """
    with database.conn.read_ctx() as cursor:
        cursor.execute('SELECT value FROM key_value_cache WHERE name=?', (key_name.value,))
        timestamp_in_db = cursor.fetchone()

    if timestamp_in_db is None:
        return True

    last_update_ts = deserialize_timestamp(timestamp_in_db[0])
    return ts_now() - last_update_ts >= refresh_period
