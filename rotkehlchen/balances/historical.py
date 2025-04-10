import logging
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, Final, TypedDict

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import DAY_IN_SECONDS, ONE, ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.constants import HISTORY_BASE_ENTRY_FIELDS
from rotkehlchen.db.filtering import (
    DBFilter,
    DBIgnoredAssetsFilter,
    DBMultiStringFilter,
    DBMultiValueFilter,
    DBNestedFilter,
    DBNotEqualFilter,
    DBTimestampFilter,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import NotFoundError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp, TradeType
from rotkehlchen.utils.misc import timestamp_to_daystart_timestamp, ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

BATCH_SIZE: Final = 250

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class HistoricalBalance(TypedDict):
    amount: FVal
    price: FVal


class HistoricalBalancesManager:
    """Processes historical events and calculates balances"""

    def __init__(self, db: 'DBHandler') -> None:
        self.db = db

    def get_balances(self, timestamp: Timestamp) -> dict[Asset, HistoricalBalance]:
        """Get historical balances for all assets at a given timestamp

        May raise:
        - NotFoundError if balance for the given timestamp does not exist.
        - DeserializationError if there is a problem deserializing an event or trade from DB.
        """
        events, main_currency = self._get_events_and_currency(to_ts=timestamp)
        if len(events) == 0:
            raise NotFoundError('No historical data found until the given timestamp.')

        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        for event in events:
            if self._update_balances(event=event, current_balances=current_balances) is not None:
                break

        result: dict[Asset, HistoricalBalance] = {}
        for asset, amount in current_balances.items():
            try:
                price = PriceHistorian.query_historical_price(
                    from_asset=asset,
                    to_asset=main_currency,
                    timestamp=timestamp,
                )
            except (RemoteError, NoPriceForGivenTimestamp):
                price = ZERO_PRICE

            result[asset] = {'amount': amount, 'price': price}

        return result

    def get_asset_balance(self, asset: Asset, timestamp: Timestamp) -> HistoricalBalance:
        """Get historical balance for a single asset at a given timestamp

        May raise:
        - NotFoundError if balance for the asset at the given timestamp does not exist.
        - DeserializationError if there is a problem deserializing an event or trade from DB.
        """
        events, main_currency = self._get_events_and_currency(to_ts=timestamp, assets=(asset,))
        if len(events) == 0:
            raise NotFoundError(f'No historical data found for {asset} until the given timestamp.')

        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        for event in events:
            if self._update_balances(
                event=event,
                current_balances=current_balances,
                assets=(asset,),
            ) is not None:
                break

        try:
            price = PriceHistorian.query_historical_price(
                from_asset=asset,
                to_asset=main_currency,
                timestamp=timestamp,
            )
        except (RemoteError, NoPriceForGivenTimestamp):
            price = ZERO_PRICE

        return {'amount': current_balances[asset], 'price': price}

    def get_assets_amounts(
            self,
            assets: tuple[Asset, ...],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[dict[Timestamp, FVal], tuple[str | int | None, str | None] | None]:
        """Get historical balance amounts for the given assets within the given time range.

        If a negative amount is encountered, returns a tuple of (identifier, group_identifier)
        for the event that caused it alongside the balances. For trades, returns
        (trade_identifier, None).

        It does not include the value of the balances in the user's profit currency as
        that is handled separately by the frontend in a different request.

        May raise:
        - NotFoundError if no events exist for the assets in the specified time period.
        - DeserializationError if there is a problem deserializing an event or trade from DB.
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
                assets=assets,
            )) is not None:
                break

            event_ts = (
                event.timestamp
                if isinstance(event, Trade)
                else ts_ms_to_sec(event.timestamp)
            )
            # Combine balances of all assets. Overwrite any existing value for this timestamp
            # so the final amount per timestamp is the cumulative result of all processed events.
            amounts[event_ts] = FVal(sum(current_balances[asset] for asset in assets))

        return amounts, negative_balance_data

    def get_historical_netvalue(
            self,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[dict[Timestamp, FVal], list[tuple[str, Timestamp]], tuple[str | int | None, str | None] | None]:  # noqa: E501
        """Calculates historical net worth per day within the given time range.

        Uses asset balances per day combined with historical prices to calculate
        the total net worth in the user's profit currency for each day. Stops calculation
        if negative balance would be created for any asset.

        May raise:
            - NotFoundError if no events exist in the specified time period.
            - DeserializationError if there is a problem deserializing an event or trade from DB.

        Returns:
            - A mapping of timestamps to net worth in main currency for each day
            - A list of (asset id, timestamp) tuples where price data was missing
            - A tuple of (identifier, group_identifier) for the event that caused a negative
              balance if any, else None. For trades, returns (trade_identifier, None).
        """
        events, main_currency = self._get_events_and_currency(from_ts=from_ts, to_ts=to_ts)
        if len(events) == 0:
            raise NotFoundError(f'No historical data found within {from_ts=} and {to_ts=}.')

        negative_balance_data = None
        current_balances: dict[Asset, FVal] = defaultdict(FVal)
        daily_balances: dict[Timestamp, dict[Asset, FVal]] = {}
        current_day = timestamp_to_daystart_timestamp(
            events[0].timestamp
            if isinstance(events[0], Trade)
            else ts_ms_to_sec(events[0].timestamp),
        )
        daily_balances[current_day] = current_balances.copy()
        for event in events:
            if (day_ts := timestamp_to_daystart_timestamp(
                event.timestamp
                if isinstance(event, Trade)
                else ts_ms_to_sec(event.timestamp),
            )) > current_day:
                daily_balances[current_day] = current_balances.copy()
                current_day = day_ts

            if (negative_balance_data := self._update_balances(event=event, current_balances=current_balances)) is not None:  # noqa: E501
                break
        else:  # no negative balance happened so update the last day's balance.
            daily_balances[current_day] = current_balances.copy()

        # For each day, calculate net worth by multiplying non-zero asset
        # balances with their prices. Store any missing price data in missing_price_points.
        net_worth_per_day: dict[Timestamp, FVal] = {}
        missing_price_points: list[tuple[str, Timestamp]] = []
        for day_ts, asset_balances in daily_balances.items():
            assets = [
                asset for asset, balance in asset_balances.items()
                if balance != ZERO
            ]
            if len(assets) == 0:
                continue

            prices, missing = self._get_prices(
                timestamp=day_ts,
                assets=assets,
                main_currency=main_currency,
            )
            missing_price_points.extend(missing)

            day_total = sum(
                (
                    balance * prices[asset]
                    for asset, balance in asset_balances.items()
                    if asset in prices and balance != ZERO
                 ),
                ZERO,
            )
            net_worth_per_day[day_ts] = day_total

        return net_worth_per_day, missing_price_points, negative_balance_data

    def _get_events_and_currency(
            self,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
    ) -> tuple[list[HistoryEvent | Trade], Asset]:
        """Helper method to get events(including trades) and main currency from DB.
        Kraken trades are ignored because they are duplicated in the history events table.

        Using two cursors to parallel scan trades and history_events tables, merging them
        chronologically. This avoids loading full tables into memory while maintaining
        event ordering. Each cursor fetches one table, allowing streaming iteration.

        If `assets` is provided, returns only events and trades involving these specific
        assets. For trades, both base and quote assets are checked. For history events,
        only the affected asset is checked. Otherwise, no asset filtering is applied.

        May raise:
        - DeserializationError if there is a problem deserializing an event or trade from DB.

        TODO: Refactor this once trades are migrated to history events.
        """
        events: list[HistoryEvent | Trade] = []
        with self.db.conn.read_ctx() as cursor1, self.db.conn.read_ctx() as cursor2:
            main_currency = self.db.get_setting(cursor=cursor1, name='main_currency')
            trade_filters: list[DBFilter] = [
                DBNestedFilter(
                    and_op=True,
                    filters=[
                        DBIgnoredAssetsFilter(
                            and_op=True,
                            asset_key='base_asset',
                            operator='NOT IN',
                        ),
                        DBIgnoredAssetsFilter(
                            and_op=True,
                            asset_key='quote_asset',
                            operator='NOT IN',
                        ),
                    ],
                ),
                DBNotEqualFilter(and_op=True, column='location', value='B'),
                DBTimestampFilter(and_op=True, from_ts=from_ts, to_ts=to_ts),
            ]
            event_filters: list[DBFilter] = [
                DBIgnoredAssetsFilter(
                    and_op=True,
                    asset_key='asset',
                    operator='NOT IN',
                ), DBTimestampFilter(
                    and_op=True,
                    to_ts=to_ts,
                    from_ts=from_ts,
                    scaling_factor=FVal(1000),  # timestamp of events are stored in ms
                ), DBMultiValueFilter(
                    and_op=True,
                    column='subtype',
                    values=[  # Skip all DEPOSIT_ASSET and REMOVE_ASSET events since they don't affect the balance.  # noqa: E501
                        HistoryEventSubType.DEPOSIT_ASSET.serialize(),
                        HistoryEventSubType.REMOVE_ASSET.serialize(),
                    ],
                    operator='NOT IN',
                ),
            ]
            if assets is not None:  # filter for the specific assets
                asset_identifiers = [asset.identifier for asset in assets]
                trade_filters.append(DBNestedFilter(
                    and_op=False,
                    filters=[
                        DBMultiStringFilter(and_op=False, column='base_asset', values=asset_identifiers, operator='IN'),  # noqa: E501
                        DBMultiStringFilter(and_op=False, column='quote_asset', values=asset_identifiers, operator='IN'),  # noqa: E501
                    ],
                ))
                event_filters.append(DBMultiStringFilter(
                    and_op=True,
                    column='asset',
                    values=asset_identifiers,
                    operator='IN',
                ))

            trade_where_clauses = []
            trade_bindings: list[Any] = []
            for filter_ in trade_filters:
                clauses, bindings = filter_.prepare()
                trade_where_clauses.extend(clauses)
                trade_bindings.extend(bindings)

            event_where_clauses = []
            event_bindings: list[Any] = []
            for filter_ in event_filters:
                clauses, bindings = filter_.prepare()
                event_where_clauses.extend(clauses)
                event_bindings.extend(bindings)

            cursor1.execute(
                f'SELECT * FROM trades WHERE {" AND ".join(trade_where_clauses)} ORDER BY timestamp',  # noqa: E501
                trade_bindings,
            )
            cursor2.execute(
                f'SELECT {HISTORY_BASE_ENTRY_FIELDS} FROM history_events WHERE {" AND ".join(event_where_clauses)} ORDER BY timestamp',  # noqa: E501
                event_bindings,
            )

            trades_buffer = deque(cursor1.fetchmany(BATCH_SIZE))
            events_buffer = deque(cursor2.fetchmany(BATCH_SIZE))
            trade_row, event_row = None, None
            while trades_buffer or events_buffer:
                try:
                    trade_row = trades_buffer[0] if trades_buffer else None
                    event_row = events_buffer[0] if events_buffer else None

                    # determine which event comes first
                    if not trade_row:
                        process_event = True
                    elif not event_row:
                        process_event = False
                    else:  # compare timestamps
                        trade_ts = trade_row[1]
                        event_ts = ts_ms_to_sec(event_row[4])
                        process_event = event_ts <= trade_ts

                    if process_event:
                        # we do not need the `entry_type` so we remove it from the tuple
                        events.append(HistoryEvent.deserialize_from_db(events_buffer.popleft()[1:]))
                        if len(events_buffer) == 0:  # refill trades buffer if empty
                            events_buffer.extend(cursor2.fetchmany(BATCH_SIZE))
                    else:
                        events.append(Trade.deserialize_from_db(trades_buffer.popleft()))
                        if len(trades_buffer) == 0:  # refill trades buffer if empty
                            trades_buffer.extend(cursor1.fetchmany(BATCH_SIZE))

                except (UnknownAsset, DeserializationError) as e:
                    raise DeserializationError(
                        f'Failed to deserialize event(s) {trade_row=} {event_row=} while '
                        f'processing historical balances due to {e!s}',
                    ) from e

        return events, main_currency

    @staticmethod
    def _get_prices(
            assets: list[Asset],
            main_currency: Asset,
            timestamp: Timestamp,
    ) -> tuple[dict[Asset, FVal], list[tuple[str, Timestamp]]]:
        """Gets cached historical prices for multiple assets at once.

        Returns:
            - A mapping of asset to price in main currency
            - A list of (asset_id, timestamp) tuples for missing prices
        """
        prices: dict[Asset, FVal] = {}
        missing_prices: list[tuple[str, Timestamp]] = []
        querystr = """
        SELECT ph1.from_asset, ph1.price
        FROM price_history AS ph1
        LEFT JOIN price_history AS ph2
            ON ph1.from_asset = ph2.from_asset
            AND ABS(ph1.timestamp - ?) > ABS(ph2.timestamp - ?)
        WHERE ph1.from_asset IN ({})
            AND ph1.to_asset = ?
            AND ph1.timestamp BETWEEN ? AND ?
            AND ph2.from_asset IS NULL;
        """.format(','.join('?' * len(assets)))
        bindings = [
            timestamp,
            timestamp,
            *(asset.identifier for asset in assets),
            main_currency.identifier,
            timestamp - DAY_IN_SECONDS,
            timestamp + DAY_IN_SECONDS,
        ]

        with GlobalDBHandler().conn.read_ctx() as cursor:
            found_prices = {row[0]: FVal(row[1]) for row in cursor.execute(querystr, bindings)}
            for asset in assets:
                if asset.identifier in found_prices:
                    prices[asset] = found_prices[asset.identifier]
                elif asset == main_currency:
                    prices[asset] = ONE
                else:
                    missing_prices.append((asset.identifier, timestamp))

        return prices, missing_prices

    @staticmethod
    def _update_balances(
            event: HistoryEvent | Trade,
            current_balances: dict[Asset, FVal],
            assets: tuple[Asset, ...] | None = None,
    ) -> tuple[str | int | None, str | None] | None:
        """Updates current balances for a trade or history event, checking for negative balances.
        Zero balance assets are removed to avoid accumulating empty entries.

        For trades:
        - BUY means we receive base_asset and spend quote_asset
        - SELL means we spend base_asset and receive quote_asset

        If `assets` is specified, then trade amounts for assets not in the list will be ignored.

        Returns a tuple of identifier & group_identifier if a negative balance would occur,
        otherwise None. For trades, only returns (trade_identifier, None).

        TODO: Remove trade-specific logic once trades are merged into history events.
        """
        if isinstance(event, Trade):
            if event.trade_type in {TradeType.BUY, TradeType.SETTLEMENT_BUY}:
                spend_asset = event.quote_asset
                receive_asset = event.base_asset
                spend_amount = event.amount * event.rate
                receive_amount = event.amount
            else:
                spend_asset = event.base_asset
                receive_asset = event.quote_asset
                spend_amount = event.amount
                receive_amount = event.amount * event.rate

            if assets is not None:  # Only include amounts for the specified assets.
                if spend_asset not in assets:
                    spend_amount = ZERO
                if receive_asset not in assets:
                    receive_amount = ZERO

            if current_balances[spend_asset] - spend_amount < ZERO:
                return event.identifier, None

            current_balances[spend_asset] -= spend_amount
            current_balances[receive_asset] += receive_amount
            if current_balances[spend_asset] == ZERO:
                del current_balances[spend_asset]

            return None

        if (  # history event logic from here and down
            (direction := event.maybe_get_direction()) is None or
            direction == EventDirection.NEUTRAL
        ):
            return None

        if direction == EventDirection.IN:
            current_balances[event.asset] += event.amount
        else:
            if current_balances[event.asset] - event.amount < ZERO:
                return event.identifier, event.event_identifier

            current_balances[event.asset] -= event.amount
            if current_balances[event.asset] == ZERO:
                del current_balances[event.asset]

        return None
