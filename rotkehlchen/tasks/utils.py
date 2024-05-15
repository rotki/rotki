import logging
from typing import TYPE_CHECKING, Literal

from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import Timestamp

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


def query_missing_prices_of_base_entries(
        database: 'DBHandler',
        entries_missing_prices: list[tuple[str, 'FVal', 'Asset', 'Timestamp']],
        base_entries_ignore_set: set[str] | None = None,
) -> None:
    """
    Queries missing prices for HistoryBaseEntry in database updating
    the price if it is found.
    If provided we keep a set of events that have been already queried in this session
    and we couldn't find a price for it now.
    """
    inquirer = PriceHistorian()
    updates = []
    for identifier, amount, asset, timestamp in entries_missing_prices:
        try:
            price = inquirer.query_historical_price(
                from_asset=asset,
                to_asset=A_USD,
                timestamp=timestamp,
            )
        except (NoPriceForGivenTimestamp, RemoteError) as e:
            log.error(
                f'Failed to find price for {asset} at {timestamp} in history '
                f'event with {identifier=}. {e!s}.',
            )
            if base_entries_ignore_set is not None:
                base_entries_ignore_set.add(identifier)
            continue

        usd_value = amount * price
        updates.append((str(usd_value), identifier))

    query = 'UPDATE history_events SET usd_value=? WHERE rowid=?'
    with database.user_write() as write_cursor:
        write_cursor.executemany(query, updates)
