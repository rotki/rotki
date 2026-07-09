import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, NamedTuple

import pandas as pd

from rotkehlchen.accounting.constants import EVENT_CATEGORY_MAPPINGS
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import DAY_IN_MILLISECONDS, ZERO
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import (
    HistoricalBalancesFilterQuery,
    HistoryEventFilterQuery,
)
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import NotFoundError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent, get_event_direction
from rotkehlchen.history.events.structures.types import EventDirection, HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EventMetricKey, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.manager import EvmManager
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HistoricalBalanceEntry(NamedTuple):
    location: Location
    location_label: str
    protocol: str | None
    asset: Asset
    amount: FVal


class HistoricalBalanceSeriesEntry(NamedTuple):
    location: Location
    location_label: str
    protocol: str | None
    asset: Asset
    times: list[Timestamp]
    values: list[FVal]


class HistoricalBalanceDivergenceEvent(NamedTuple):
    event_identifier: int
    group_identifier: str | None
    timestamp: Timestamp
    block_number: int
    tracked_balance: FVal
    onchain_balance: FVal
    difference: FVal


class HistoricalBalanceDivergenceProbe(NamedTuple):
    event_index: int
    event: HistoricalBalanceDivergenceEvent
    matches: bool


class HistoricalBalanceDivergenceResult(NamedTuple):
    status: Literal['diverged', 'diverged_from_start', 'no_divergence']
    location: Location
    address: str
    asset: Asset
    total_events: int
    tolerance: FVal
    first_diverged: HistoricalBalanceDivergenceEvent | None
    last_matching: HistoricalBalanceDivergenceEvent | None
    probes: list[HistoricalBalanceDivergenceProbe]


class _TrackedBalanceEvent(NamedTuple):
    event_identifier: int
    group_identifier: str | None
    timestamp: Timestamp
    tracked_balance: FVal
    block_number: int | None


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
            group_by_account: bool = False,
    ) -> tuple[bool, dict[Asset, FVal] | list[HistoricalBalanceEntry] | None]:
        """Get historical balances for all assets at a given timestamp.

        The inner query gets the latest balance per bucket via MAX(sort_key),
        relying on SQLite's bare column behavior to return non-aggregated columns from that row.
        See https://www.sqlite.org/lang_select.html#bareagg

        Returns a tuple of (processing_required, balances):
        - processing_required: True if events exist but haven't been processed yet
        - balances: When group_by_account is False, a dict of asset to total amount.
          When group_by_account is True, a list of per location/account/protocol/asset entries.
          None is returned when no balance data is available.
        """
        filter_str, filter_bindings = filter_query.prepare()
        query_bindings: list = [EventMetricKey.BALANCE.serialize(), *filter_bindings]
        data: dict[Asset, FVal] | list[HistoricalBalanceEntry] | None
        with self.db.conn.read_ctx() as cursor:
            if group_by_account is True:
                cursor.execute(
                    f"""SELECT
                        location, location_label, protocol, asset, metric_value, MAX(sort_key)
                    FROM event_metrics em
                    WHERE metric_key = ? {filter_str}
                    AND asset NOT IN (
                        SELECT value FROM multisettings WHERE name='ignored_asset'
                    )
                    GROUP BY location, location_label, protocol, asset
                    HAVING metric_value > 0
                    """,
                    query_bindings,
                )
                data = [
                    HistoricalBalanceEntry(
                        location=Location.deserialize_from_db(location),
                        location_label=location_label,
                        protocol=protocol,
                        asset=Asset(asset_id),
                        amount=FVal(amount),
                    ) for location, location_label, protocol, asset_id, amount, _sort_key in cursor
                ] or None
            else:
                cursor.execute(
                    f"""SELECT asset, SUM(metric_value) FROM (
                        SELECT asset, metric_value, MAX(sort_key)
                        FROM event_metrics em
                        WHERE metric_key = ? {filter_str}
                        AND asset NOT IN (
                            SELECT value FROM multisettings WHERE name='ignored_asset'
                        )
                        GROUP BY location, location_label, protocol, asset
                    ) GROUP BY asset HAVING SUM(metric_value) > 0
                    """,
                    query_bindings,
                )
                data = {Asset(asset_id): FVal(total) for asset_id, total in cursor} or None

        return self._has_unprocessed_events(
            where_clause=filter_query.unprocessed_where_clause,
            bindings=filter_query.unprocessed_bindings,
        ), data

    def get_balance_series(
            self,
            filter_query: HistoricalBalancesFilterQuery,
    ) -> tuple[bool, list[HistoricalBalanceSeriesEntry] | None]:
        """Get historical balance series per location/account/protocol/asset bucket."""
        filter_str, filter_bindings = filter_query.prepare()
        query_bindings: list = [EventMetricKey.BALANCE.serialize(), *filter_bindings]
        entries: list[HistoricalBalanceSeriesEntry] = []
        current_key: tuple[Location, str, str | None, Asset] | None = None
        times: list[Timestamp] = []
        values: list[FVal] = []
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                f"""SELECT location, location_label, protocol, asset, timestamp, metric_value
                FROM event_metrics em
                WHERE metric_key = ? {filter_str}
                AND asset NOT IN (SELECT value FROM multisettings WHERE name='ignored_asset')
                AND metric_value > 0
                ORDER BY location, location_label, protocol, asset, timestamp, sort_key
                """,
                query_bindings,
            )
            for location_raw, location_label, protocol, asset_id, timestamp, amount in cursor:
                key = (
                    Location.deserialize_from_db(location_raw),
                    location_label,
                    protocol,
                    Asset(asset_id),
                )
                if current_key is not None and key != current_key:
                    entries.append(HistoricalBalanceSeriesEntry(
                        location=current_key[0],
                        location_label=current_key[1],
                        protocol=current_key[2],
                        asset=current_key[3],
                        times=times,
                        values=values,
                    ))
                    times = []
                    values = []

                current_key = key
                times.append(ts_ms_to_sec(timestamp))
                values.append(FVal(amount))

            if current_key is not None:
                entries.append(HistoricalBalanceSeriesEntry(
                    location=current_key[0],
                    location_label=current_key[1],
                    protocol=current_key[2],
                    asset=current_key[3],
                    times=times,
                    values=values,
                ))

        return self._has_unprocessed_events(
            where_clause=filter_query.unprocessed_where_clause,
            bindings=filter_query.unprocessed_bindings,
        ), entries or None

    def find_onchain_balance_divergence(
            self,
            evm_manager: 'EvmManager',
            evm_chain: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
            address: 'ChecksumEvmAddress',
            asset: Asset,
            tolerance: FVal = ZERO,
    ) -> HistoricalBalanceDivergenceResult:
        """Find the first tracked wallet-balance event that disagrees with on-chain data.

        Uses the monotonic case this diagnostic targets: tracked and on-chain balance match up to
        a point, then remain diverged because a balance-changing event is missing or incorrect.
        The database scan is narrow to one chain/address/asset wallet bucket, while remote archive
        node probes are O(log n). Transient mismatches that later resolve are outside this search.

        May raise:
        - NotFoundError if no processed wallet balance metrics exist for the address/asset.
        - RemoteError if block lookup or archive balance lookup fails.
        """
        location = Location.from_chain_id(evm_chain)
        events = self._get_tracked_wallet_balance_events(
            evm_chain=evm_chain,
            location=location,
            address=address,
            asset=asset,
        )
        if len(events) == 0:
            raise NotFoundError(
                f'No historical wallet balance data found for {asset.identifier} at '
                f'{address} on {location.serialize()}',
            )

        token = (
            None
            if asset == evm_manager.node_inquirer.native_token
            else asset.resolve_to_evm_token()
        )
        probes: list[HistoricalBalanceDivergenceProbe] = []
        probe_cache: dict[int, HistoricalBalanceDivergenceProbe] = {}
        last_probe = self._probe_onchain_balance_divergence(
            evm_manager=evm_manager,
            events=events,
            probe_cache=probe_cache,
            probes=probes,
            index=len(events) - 1,
            address=address,
            asset=asset,
            token=token,
            tolerance=tolerance,
        )
        if last_probe.matches is True:
            return HistoricalBalanceDivergenceResult(
                status='no_divergence',
                location=location,
                address=address,
                asset=asset,
                total_events=len(events),
                tolerance=tolerance,
                first_diverged=None,
                last_matching=last_probe.event,
                probes=probes,
            )

        first_probe = self._probe_onchain_balance_divergence(
            evm_manager=evm_manager,
            events=events,
            probe_cache=probe_cache,
            probes=probes,
            index=0,
            address=address,
            asset=asset,
            token=token,
            tolerance=tolerance,
        )
        if first_probe.matches is False:
            return HistoricalBalanceDivergenceResult(
                status='diverged_from_start',
                location=location,
                address=address,
                asset=asset,
                total_events=len(events),
                tolerance=tolerance,
                first_diverged=first_probe.event,
                last_matching=None,
                probes=probes,
            )

        low, high = 0, len(events) - 1
        last_matching = first_probe.event
        first_diverged = last_probe.event
        while low + 1 < high:
            mid = (low + high) // 2
            mid_probe = self._probe_onchain_balance_divergence(
                evm_manager=evm_manager,
                events=events,
                probe_cache=probe_cache,
                probes=probes,
                index=mid,
                address=address,
                asset=asset,
                token=token,
                tolerance=tolerance,
            )
            if mid_probe.matches:
                low = mid
                last_matching = mid_probe.event
            else:
                high = mid
                first_diverged = mid_probe.event

        return HistoricalBalanceDivergenceResult(
            status='diverged',
            location=location,
            address=address,
            asset=asset,
            total_events=len(events),
            tolerance=tolerance,
            first_diverged=first_diverged,
            last_matching=last_matching,
            probes=probes,
        )

    @staticmethod
    def _probe_onchain_balance_divergence(
            evm_manager: 'EvmManager',
            events: list[_TrackedBalanceEvent],
            probe_cache: dict[int, HistoricalBalanceDivergenceProbe],
            probes: list[HistoricalBalanceDivergenceProbe],
            index: int,
            address: 'ChecksumEvmAddress',
            asset: Asset,
            token: 'EvmToken | None',
            tolerance: FVal,
    ) -> HistoricalBalanceDivergenceProbe:
        if (cached_probe := probe_cache.get(index)) is not None:
            return cached_probe

        event = events[index]
        block_number = event.block_number
        if block_number is None:
            block_number = evm_manager.node_inquirer.get_blocknumber_by_time(
                ts=event.timestamp,
            )

        if token is None:
            onchain_balance = evm_manager.node_inquirer.get_historical_native_balance(
                address=address,
                block_number=block_number,
                queried_timestamp=event.timestamp,
            )
        else:
            onchain_balance = evm_manager.node_inquirer.get_historical_token_balance(
                address=address,
                token=token,
                block_number=block_number,
                queried_timestamp=event.timestamp,
            )

        if onchain_balance is None:
            raise RemoteError(
                f'Failed to query historical on-chain balance for {asset.identifier} '
                f'at block {block_number}',
            )

        divergence_event = HistoricalBalanceDivergenceEvent(
            event_identifier=event.event_identifier,
            group_identifier=event.group_identifier,
            timestamp=event.timestamp,
            block_number=block_number,
            tracked_balance=event.tracked_balance,
            onchain_balance=onchain_balance,
            difference=onchain_balance - event.tracked_balance,
        )
        result = HistoricalBalanceDivergenceProbe(
            event_index=index + 1,
            event=divergence_event,
            matches=abs(divergence_event.difference) <= tolerance,
        )
        probe_cache[index] = result
        probes.append(result)
        return result

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
        events, _ = self._get_events_and_currency(from_ts=from_ts, to_ts=to_ts, assets=assets)
        if len(events) == 0:
            raise NotFoundError(f'No historical data found for {assets} within {from_ts=} and {to_ts=}.')  # noqa: E501

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
            amounts[ts_ms_to_sec(event.timestamp)] = FVal(sum(current_balances[asset] for asset in assets))  # noqa: E501

        return amounts, negative_balance_data

    def get_assets_amounts_event_metrics(
            self,
            assets: tuple[Asset, ...],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[bool, dict[Timestamp, FVal] | None]:
        """Get historical balance amounts for the given assets within the given time range.
        TODO (balances): Replace get_assets_amounts with this.

        Returns a tuple of (processing_required, amounts):
        - processing_required: True if events exist but haven't been processed yet
        - amounts: Cumulative balance at each event timestamp, relative to the start of the
          time range (starting from 0). Uses pre-computed balances from event_metrics table.
          Uses SQL LAG() window function to compute per-bucket balance deltas in the database.
          None if no data is available.
        """
        from_ts_ms, to_ts_ms = ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)
        metric_key = EventMetricKey.BALANCE.serialize()
        asset_ids = [asset.resolve_swapped_for().identifier for asset in assets]
        columns = ['timestamp', 'sort_key', 'delta']
        frames: list[pd.DataFrame] = []
        with self.db.conn.read_ctx() as cursor:
            for chunk, placeholders in get_query_chunks(data=asset_ids):
                chunk_df = pd.DataFrame(
                    cursor.execute(
                        f"""
                        WITH all_events AS (
                            SELECT
                                timestamp,
                                CAST(metric_value AS REAL) as balance,
                                sort_key,
                                location,
                                location_label,
                                protocol,
                                asset
                            FROM event_metrics em
                            WHERE metric_key = ? AND asset IN ({placeholders})
                            AND asset NOT IN (
                                SELECT value FROM multisettings WHERE name='ignored_asset'
                            )
                        ),
                        with_delta AS (
                            SELECT
                                timestamp,
                                sort_key,
                                balance - COALESCE(
                                    LAG(balance) OVER (
                                        PARTITION BY location, location_label, protocol, asset
                                        ORDER BY sort_key
                                    ),
                                    0
                                ) as delta
                            FROM all_events
                        )
                        SELECT timestamp, sort_key, delta
                        FROM with_delta
                        WHERE timestamp >= ? AND timestamp <= ?
                        """,
                        (metric_key, *chunk, from_ts_ms, to_ts_ms),
                    ),
                    columns=columns,
                )
                if len(chunk_df) > 0:
                    frames.append(chunk_df)

        data = None
        if frames:
            df = pd.concat(frames, ignore_index=True).astype(
                {'timestamp': 'int64', 'sort_key': 'int64', 'delta': 'float64'},
            ).sort_values('sort_key')
            df['amount'] = df['delta'].cumsum()
            data = {
                ts_ms_to_sec(TimestampMS(int(ts))): FVal(amt)
                for ts, amt in zip(df['timestamp'].tolist(), df['amount'].tolist(), strict=True)
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
        accumulates them per asset with pandas. Days without activity for an asset
        carry forward the last known balance.

        Returns a tuple of a boolean representing whether processing is still needed,
        and either None or a pair of day timestamps and their corresponding balances.
        """
        from_ts_ms, to_ts_ms = ts_sec_to_ms(from_ts), ts_sec_to_ms(to_ts)
        with self.db.conn.read_ctx() as cursor:
            df = pd.DataFrame(
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
                columns=['timestamp', 'sort_key', 'asset', 'delta'],
            )

        data = None
        if len(df) != 0:
            # The query returns balance deltas (changes) for each event.
            # Sum them up in order to reconstruct the running balance for each asset,
            # then keep only the last balance of each day (the end-of-day snapshot).
            df = df.astype(
                {'timestamp': 'int64', 'sort_key': 'int64', 'asset': 'str', 'delta': 'float64'},
            ).sort_values('sort_key')
            df['balance'] = df.groupby('asset', sort=False)['delta'].cumsum()
            df['day'] = (df['timestamp'] // DAY_IN_MILLISECONDS) * DAY_IN_MILLISECONDS
            pivoted = (
                df.groupby(['day', 'asset'], sort=False)['balance']
                .last().reset_index()
                .pivot(index='day', columns='asset', values='balance')
                .sort_index()
                # Forward-fill so each asset's balance carries independently to days
                # without activity.
                .ffill()
            )
            timestamps = [ts_ms_to_sec(TimestampMS(int(d))) for d in pivoted.index.tolist()]
            balances_per_day = [
                {str(asset): FVal(val) for asset, val in row.items() if pd.notna(val)}
                for row in pivoted.to_dict('records')
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

    def _get_tracked_wallet_balance_events(
            self,
            evm_chain: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
            location: Location,
            address: 'ChecksumEvmAddress',
            asset: Asset,
    ) -> list[_TrackedBalanceEvent]:
        """Load processed wallet balance checkpoints for one chain/address/asset.

        Protocol buckets are intentionally excluded: archive-node balance queries return the
        wallet balance held by the address, not balances custodied in DeFi protocol buckets.
        """
        with self.db.conn.read_ctx() as cursor:
            events = [
                _TrackedBalanceEvent(
                    event_identifier=event_identifier,
                    group_identifier=group_identifier,
                    timestamp=ts_ms_to_sec(TimestampMS(timestamp)),
                    tracked_balance=FVal(metric_value),
                    block_number=block_number,
                )
                for event_identifier, group_identifier, timestamp, metric_value, block_number in cursor.execute(  # noqa: E501
                    """
                    SELECT em.event_identifier, he.group_identifier, em.timestamp,
                    em.metric_value, et.block_number
                    FROM event_metrics em
                    JOIN history_events he ON he.identifier = em.event_identifier
                    LEFT JOIN chain_events_info cei ON cei.identifier = em.event_identifier
                    LEFT JOIN evm_transactions et ON et.tx_hash = cei.tx_ref AND et.chain_id = ?
                    WHERE em.metric_key = ? AND em.location = ? AND em.location_label = ?
                    AND em.protocol IS NULL AND em.asset = ?
                    ORDER BY em.sort_key
                    """,
                    (
                        evm_chain.serialize_for_db(),
                        EventMetricKey.BALANCE.serialize(),
                        location.serialize_for_db(),
                        address,
                        asset.resolve_swapped_for().identifier,
                    ),
                )
            ]

        # RPC balances represent the state at the end of a block. Keep the last tracked
        # checkpoint for each block so earlier events in that block are not false mismatches.
        checkpoints: list[_TrackedBalanceEvent] = []
        for event in events:
            if (
                event.block_number is not None and
                checkpoints and
                checkpoints[-1].block_number == event.block_number
            ):
                checkpoints[-1] = event
            else:
                checkpoints.append(event)
        return checkpoints

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
