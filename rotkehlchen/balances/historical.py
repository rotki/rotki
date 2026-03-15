import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

import polars as pl

from rotkehlchen.accounting.constants import EVENT_CATEGORY_MAPPINGS
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.types import HistoricalBalancesParams
from rotkehlchen.constants import DAY_IN_MILLISECONDS, ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import NotFoundError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import (
    HistoryBaseEntry,
    get_event_direction,
)
from rotkehlchen.history.events.structures.types import EventDirection
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
            filter_params: HistoricalBalancesParams,
    ) -> tuple[dict[Asset, FVal] | None, tuple[str | int | None, str | None] | None]:
        """Get historical balances for all assets at a given timestamp by replaying history events.

        Returns a tuple of (balances, negative_balance_data).
        """
        events, _ = self._get_events_and_currency(filter_params=filter_params)
        negative_balance_data = None
        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        for event in events:
            if (negative_balance_data := self._update_balances(
                    event=event,
                    current_balances=current_balances,
            )) is not None:
                break

        return {
            asset: amount
            for asset, amount in current_balances.items()
            if amount > ZERO
        } or None, negative_balance_data

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
            filter_params=HistoricalBalancesParams(
                assets=assets,
                location_label=address,
            ),
        )
        if len(events) == 0:
            raise NotFoundError(f'No historical data found for {assets} for user address {address}')  # noqa: E501

        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        for event in events:
            self._update_balances(event=event, current_balances=current_balances)

        return {asset.resolve_to_evm_token(): balance for asset, balance in current_balances.items() if balance > ZERO}  # noqa: E501

    def get_assets_amounts(
            self,
            filter_params: HistoricalBalancesParams,
    ) -> tuple[dict[Timestamp, FVal], tuple[str | int | None, str | None] | None]:
        """Get historical balance amounts for the given assets within the given time range.

        If a negative amount is encountered, returns a tuple of (identifier, group_identifier)
        for the event that caused it alongside the balances.

        It does not include the value of the balances in the user's profit currency as
        that is handled separately by the frontend in a different request.

        May raise:
        - NotFoundError if no events exist for the assets in the specified time period.
        - DeserializationError if there is a problem deserializing an event from DB.
        """
        events, _ = self._get_events_and_currency(filter_params=filter_params)
        if len(events) == 0:
            raise NotFoundError(
                f'No historical data found for {filter_params.assets} within '
                f'{filter_params.from_timestamp=} and {filter_params.to_timestamp=}.',
            )

        negative_balance_data = None
        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        amounts: dict[Timestamp, FVal] = defaultdict(lambda: ZERO)
        for event in events:
            if (negative_balance_data := self._update_balances(
                    event=event,
                    current_balances=current_balances,
            )) is not None:
                break

            # Combine balances of all assets. Overwrite any existing value for this timestamp
            # so the final amount per timestamp is the cumulative result of all processed events.
            amounts[ts_ms_to_sec(event.timestamp)] = FVal(sum(current_balances[asset] for asset in filter_params.assets))  # type: ignore[union-attr, misc]  # assets cannot be None here  # noqa: E501

        return amounts, negative_balance_data

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
                        SELECT timestamp, asset, CAST(metric_value AS REAL) as balance,
                               sort_key, location, location_label, protocol
                        FROM event_metrics em
                        WHERE metric_key = ?
                        AND asset NOT IN (
                            SELECT value FROM multisettings WHERE name='ignored_asset'
                        )
                    ), with_delta AS (
                        SELECT timestamp, sort_key, asset,
                               balance - COALESCE(
                                   LAG(balance) OVER (
                                       PARTITION BY location, location_label, protocol, asset
                                       ORDER BY sort_key
                                   ),
                                   0
                               ) as delta
                        FROM all_events
                    )
                    SELECT timestamp, sort_key, asset, delta FROM with_delta
                    WHERE timestamp >= ? AND timestamp <= ?
                    """,
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
            filter_params: HistoricalBalancesParams,
    ) -> tuple[Sequence['HistoryBaseEntry'], Asset]:
        """Helper method to get events and main currency from DB.

        May raise:
        - DeserializationError if there is a problem deserializing an event from DB.
        """
        with self.db.conn.read_ctx() as cursor:
            events = DBHistoryEvents(self.db).get_history_events_internal(
                cursor=cursor,
                filter_query=filter_params.make_history_event_filter_query(),
            )

        return events, CachedSettings().main_currency

    @staticmethod
    def _update_balances(
            event: HistoryBaseEntry,
            current_balances: dict[Asset, FVal],
    ) -> tuple[str | int | None, str | None] | None:
        """Updates current balances for a history event, checking for negative balances.
        Zero balance assets are removed to avoid accumulating empty entries.

        Returns a tuple of identifier & group_identifier if a negative balance would occur,
        otherwise None.
        """
        if (
            (direction := get_event_direction(
                event_type=event.event_type,
                event_subtype=event.event_subtype,
                for_balance_tracking=True,
            )) is None or
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
