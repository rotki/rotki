import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

import polars as pl

from rotkehlchen.accounting.constants import EVENT_CATEGORY_MAPPINGS
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import DAY_IN_MILLISECONDS, ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import (
    HistoricalBalancesFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import NotFoundError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent, get_event_direction
from rotkehlchen.history.events.structures.types import EventDirection, HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EventMetricKey, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HistoricalBalancesManager:
    """Processes historical events and calculates balances"""

    _neutral_balance_tracking_pairs: tuple[tuple[str, str], ...] = tuple(
        (event_type.serialize(), subtype.serialize())
        for event_type, subtypes in EVENT_CATEGORY_MAPPINGS.items()
        for subtype in subtypes
        if get_event_direction(event_type=event_type, event_subtype=subtype, for_balance_tracking=True) == EventDirection.NEUTRAL  # noqa: E501
    )

    def __init__(self, db: 'DBHandler') -> None:
        self.db = db

    def get_balances(
            self,
            filter_query: HistoricalBalancesFilterQuery,
    ) -> tuple[bool, dict[Asset, FVal] | None]:
        """Get historical balances for all assets at a given timestamp.

        The inner query gets the latest balance per bucket via MAX(timestamp + sequence_index),
        relying on SQLite's bare column behavior to return non-aggregated columns from that row.
        See https://www.sqlite.org/lang_select.html#bareagg

        Returns a tuple of (processing_required, balances):
        - processing_required: True if events exist but haven't been processed yet
        - balances: Dict of asset to amount, or None if no data available
        """
        filter_str, filter_bindings = filter_query.prepare()
        query_bindings: list = [EventMetricKey.BALANCE.serialize(), *filter_bindings]
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                f"""SELECT asset, SUM(metric_value) FROM (
                    SELECT he.asset, em.metric_value, MAX(he.timestamp + he.sequence_index)
                    FROM event_metrics em
                    INNER JOIN history_events he ON em.event_identifier = he.identifier
                    WHERE he.ignored = 0 AND em.metric_key = ? {filter_str}
                    GROUP BY he.location, em.location_label, em.protocol, he.asset
                ) GROUP BY asset HAVING SUM(metric_value) > 0
                """,
                query_bindings,
            )
            data = {Asset(asset_id): FVal(total) for asset_id, total in cursor} or None

        return self._has_unprocessed_events(
            where_clause=filter_query.unprocessed_where_clause,
            bindings=filter_query.unprocessed_bindings,
        ), data

    def get_erc721_tokens_balances(
            self,
            address: 'ChecksumEvmAddress',
            assets: tuple[Asset, ...],
    ) -> dict['EvmToken', FVal]:
        """Get current balances for the given erc721 assets of a specific address by processing historical events.

        May raise:
            - NotFoundError if no events exist for the assets/address
            - DeserializationError if there is a problem deserializing an event from DB
        """  # noqa: E501
        events, _ = self._get_events_and_currency(
            assets=assets,
            address=address,
        )
        if len(events) == 0:
            raise NotFoundError(f'No historical data found for {assets} for user address {address}')  # noqa: E501

        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        for event in events:
            self._update_balances(event=event, current_balances=current_balances)

        return {asset.resolve_to_evm_token(): balance for asset, balance in current_balances.items() if balance > ZERO}  # noqa: E501

    def get_assets_amounts(
            self,
            assets: tuple[Asset, ...],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[bool, dict[Timestamp, FVal] | None]:
        """Get historical balance amounts for the given assets within the given time range.

        Returns a tuple of (processing_required, amounts):
        - processing_required: True if events exist but haven't been processed yet
        - amounts: Cumulative balance at each event timestamp, relative to the start of the
          time range (starting from 0). Uses pre-computed balances from event_metrics table.
          Uses SQL LAG() window function to compute per-bucket balance deltas in the database.
          None if no data is available.
        """
        from_ts_ms, to_ts_ms = ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)
        metric_key, asset_ids = EventMetricKey.BALANCE.serialize(), [asset.identifier for asset in assets]  # noqa: E501
        schema = {'timestamp': pl.Int64, 'sort_key': pl.Int64, 'delta': pl.Float64}
        df = pl.DataFrame(schema=schema)
        with self.db.conn.read_ctx() as cursor:
            for chunk, placeholders in get_query_chunks(data=asset_ids):
                if (chunk_df := pl.DataFrame(
                    cursor.execute(
                        f"""
                        WITH all_events AS (
                            SELECT
                                he.timestamp,
                                he.location || COALESCE(em.location_label, '') || COALESCE(em.protocol, '') || he.asset as bucket,
                                CAST(em.metric_value AS REAL) as balance,
                                he.timestamp + he.sequence_index as sort_key
                            FROM event_metrics em
                            INNER JOIN history_events he ON em.event_identifier = he.identifier
                            WHERE em.metric_key = ? AND he.asset IN ({placeholders})
                        ),
                        with_delta AS (
                            SELECT
                                timestamp,
                                sort_key,
                                balance - COALESCE(LAG(balance) OVER (PARTITION BY bucket ORDER BY sort_key), 0) as delta
                            FROM all_events
                        )
                        SELECT timestamp, sort_key, delta
                        FROM with_delta
                        WHERE timestamp >= ? AND timestamp <= ?
                        """,  # noqa: E501
                        (metric_key, *chunk, from_ts_ms, to_ts_ms),
                    ),
                    schema=schema,
                    orient='row',
                )).height > 0:
                    df.vstack(chunk_df, in_place=True)

        data = None
        if df.height != 0:
            result_df = (
                df.rechunk().sort('sort_key')
                .with_columns(pl.col('delta').cum_sum().alias('amount'))
                .select(['timestamp', 'amount'])
            )
            timestamps = result_df['timestamp'].to_list()
            amounts = result_df['amount'].to_list()
            data = {
                ts_ms_to_sec(ts): FVal(amt)
                for ts, amt in zip(timestamps, amounts, strict=True)
            }

        for chunk, placeholders in get_query_chunks(data=asset_ids):
            if self._has_unprocessed_events(
                where_clause=f'asset IN ({placeholders}) AND timestamp >= ? AND timestamp <= ?',
                bindings=[*chunk, from_ts_ms, to_ts_ms],
            ):
                return True, data
        return False, data

    def get_historical_netvalue(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[bool, tuple[list[Timestamp], list[dict[str, FVal]]] | None]:
        """Returns daily snapshots of asset balances between the given timestamps.

        Computes balance deltas using SQL LAG() over location/protocol buckets, then
        accumulates them per asset with polars. Days without activity for an asset
        carry forward the last known balance.

        Returns a tuple of a boolean representing whether processing is still needed,
        and either None or a pair of day timestamps and their corresponding balances.
        """
        from_ts_ms, to_ts_ms = ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)
        with self.db.conn.read_ctx() as cursor:
            df = pl.DataFrame(
                cursor.execute(
                    """
                    WITH all_events AS (
                        SELECT he.timestamp, he.asset, CAST(em.metric_value AS REAL) as balance,
                               he.timestamp + he.sequence_index as sort_key,
                               he.location || COALESCE(em.location_label, '') || COALESCE(em.protocol, '') || he.asset as bucket
                        FROM event_metrics em
                        INNER JOIN history_events he ON em.event_identifier = he.identifier
                        WHERE em.metric_key = ? AND he.ignored = 0
                    ), with_delta AS (
                        SELECT timestamp, sort_key, asset,
                               balance - COALESCE(LAG(balance) OVER (PARTITION BY bucket ORDER BY sort_key), 0) as delta
                        FROM all_events
                    )
                    SELECT timestamp, sort_key, asset, delta FROM with_delta
                    WHERE timestamp >= ? AND timestamp <= ?
                    """,  # noqa: E501
                    (EventMetricKey.BALANCE.serialize(), from_ts_ms, to_ts_ms),
                ),
                schema={'timestamp': pl.Int64, 'sort_key': pl.Int64, 'asset': pl.String, 'delta': pl.Float64},  # noqa: E501
                orient='row',
            )

        data = None
        if df.height != 0:
            # The query returns balance deltas (changes) for each event.
            # Sum them up in order to reconstruct the running balance for each asset,
            # then keep only the last balance of each day (the end-of-day snapshot).
            pivoted = (
                df.rechunk()
                .sort('sort_key')
                .with_columns(
                    pl.col('delta').cum_sum().over('asset').alias('balance'),
                    (pl.col('timestamp') // DAY_IN_MILLISECONDS * DAY_IN_MILLISECONDS).alias('day'),  # noqa: E501
                )
                .group_by(['day', 'asset'])
                .agg(pl.col('balance').last())
                .sort('day')
                # Pivot so each asset becomes a column. This allows forward-fill to
                # carry each asset's balance independently to days without activity.
                .pivot(on='asset', index='day', values='balance')
                .fill_null(strategy='forward')
            )
            timestamps = [ts_ms_to_sec(d) for d in pivoted['day'].to_list()]
            balances_per_day = [
                {asset: FVal(val) for asset, val in row.items() if val is not None}
                for row in pivoted.select(pl.exclude('day')).iter_rows(named=True)
            ]
            data = (timestamps, balances_per_day)

        return self._has_unprocessed_events(
            where_clause='timestamp >= ? AND timestamp <= ?',
            bindings=[from_ts_ms, to_ts_ms],
        ), data

    def _has_unprocessed_events(
            self,
            where_clause: str,
            bindings: Sequence[str | TimestampMS],
    ) -> bool:
        """Return True if events that should have metrics are missing them.

        Uses the stale marker to determine which events need checking:
        - If stale marker is None: all events were evaluated (including negative balance skips)
        - If stale marker exists and processing ran: only check events >= stale_event_ts
        - If stale marker exists but never processed: check all events matching where_clause
        """
        with self.db.conn.read_ctx() as cursor:
            if (stale_value := self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.STALE_BALANCES_FROM_TS,
            )) is None:
                return False  # All events evaluated (including negative balance skips)

            if self.db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
            ) is not None:  # events before stale_event_ts were already evaluated
                where_clause = f'({where_clause}) AND he.timestamp >= {stale_value}'

            exclusions = ' OR '.join(['(he.type = ? AND he.subtype = ?)'] * len(self._neutral_balance_tracking_pairs))  # noqa: E501
            return cursor.execute(
                f"""SELECT 1 FROM history_events he
                WHERE {where_clause} AND he.ignored = 0 AND NOT ({exclusions})
                AND NOT EXISTS (SELECT 1 FROM event_metrics em WHERE em.event_identifier = he.identifier) LIMIT 1
                """,  # noqa: E501
                [*bindings, *[v for pair in self._neutral_balance_tracking_pairs for v in pair]],
            ).fetchone() is not None

    def _get_events_and_currency(
            self,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
            address: 'ChecksumEvmAddress | None' = None,
    ) -> tuple[list[HistoryEvent], Asset]:
        """Helper method to get events and main currency from DB.

        If `assets` is provided, returns only events involving these specific
        assets. For history events, only the affected asset is checked.
        Otherwise, no asset filtering is applied.

        May raise:
        - DeserializationError if there is a problem deserializing an event from DB.
        """
        with self.db.conn.read_ctx() as cursor:
            main_currency = self.db.get_setting(cursor=cursor, name='main_currency')
            filter_query = HistoryEventFilterQuery.make(
                from_ts=from_ts,
                to_ts=to_ts,
                order_by_rules=[('timestamp', True)],
                exclude_ignored_assets=True,
                assets=assets,
                exclude_subtypes=[
                    HistoryEventSubType.DEPOSIT_ASSET,
                    HistoryEventSubType.REMOVE_ASSET,
                ],
                location_labels=[address] if address else None,
            )
            events = []
            where_clauses, bindings = filter_query.prepare(
                with_order=True,
                with_group_by=False,
                with_pagination=False,
                without_ignored_asset_filter=False,
            )
            for entry in cursor.execute(f'SELECT {filter_query.get_columns()} FROM history_events {where_clauses}', bindings):  # noqa: E501
                try:
                    events.append(HistoryEvent.deserialize_from_db(entry[1:]))
                except DeserializationError as e:
                    raise DeserializationError(
                        f'Failed to deserialize event {entry} while '
                        f'processing historical balances due to {e!s}',
                    ) from e

        return events, main_currency

    @staticmethod
    def _update_balances(
            event: HistoryEvent,
            current_balances: dict[Asset, FVal],
    ) -> tuple[str | int | None, str | None] | None:
        """Updates current balances for a history event, checking for negative balances.
        Zero balance assets are removed to avoid accumulating empty entries.

        Returns a tuple of identifier & group_identifier if a negative balance would occur,
        otherwise None.
        """
        if (
            (direction := event.maybe_get_direction()) is None or
            direction == EventDirection.NEUTRAL
        ):
            return None

        if direction == EventDirection.IN:
            current_balances[event.asset] += event.amount
        else:
            if current_balances[event.asset] - event.amount < ZERO:
                return event.identifier, event.group_identifier

            current_balances[event.asset] -= event.amount
            if current_balances[event.asset] == ZERO:
                del current_balances[event.asset]

        return None
