from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import NotFoundError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


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
        """
        events, main_currency = self._get_events_and_currency(to_ts=timestamp)
        if len(events) == 0:
            raise NotFoundError('No historical data found until the given timestamp.')

        amounts = self._calculate_balance_from_events(events)
        result: dict[Asset, HistoricalBalance] = {}
        for asset, amount in amounts.items():
            try:
                price = PriceHistorian().query_historical_price(
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
        """
        events, main_currency = self._get_events_and_currency(to_ts=timestamp, assets=(asset,))
        if len(events) == 0:
            raise NotFoundError(f'No historical data found for {asset} until the given timestamp.')

        amounts = self._calculate_balance_from_events(events)
        try:
            price = PriceHistorian().query_historical_price(
                from_asset=asset,
                to_asset=main_currency,
                timestamp=timestamp,
            )
        except (RemoteError, NoPriceForGivenTimestamp):
            price = ZERO_PRICE

        return {'amount': amounts[asset], 'price': price}

    def get_assets_amounts(
            self,
            assets: tuple[Asset, ...],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> tuple[dict[Timestamp, FVal], str | None]:
        """Get historical balance amounts for the given assets within the given time range.

        If a negative amount is encountered in the time range, the event_identifier of the
        event that caused it is returned alongside the balances.

        It does not include the value of the balances in the user's profit currency as
        that is handled separately by the frontend in a different request.

        May raise:
        - NotFoundError if no events exist for the assets in the specified time period.
        """
        events, _ = self._get_events_and_currency(from_ts=from_ts, to_ts=to_ts, assets=assets)
        if len(events) == 0:
            raise NotFoundError(f'No historical data found for {assets} within {from_ts=} and {to_ts=}.')  # noqa: E501

        total_amount, last_event_id = ZERO, None
        amounts: dict[Timestamp, FVal] = defaultdict(lambda: ZERO)
        for event in events:
            if (
                (direction := event.maybe_get_direction()) is None or
                direction == EventDirection.NEUTRAL
            ):
                continue

            if direction == EventDirection.IN:
                total_amount += event.balance.amount
            else:  # EventDirection.OUT
                total_amount -= event.balance.amount

            amounts[ts_ms_to_sec(event.timestamp)] = total_amount
            if total_amount < ZERO:
                last_event_id = event.event_identifier
                break

        return amounts, last_event_id

    def _get_events_and_currency(
            self,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
    ) -> tuple[list['HistoryBaseEntry'], Asset]:
        """Helper method to get historical events and main currency from DB"""
        db_history_events = DBHistoryEvents(database=self.db)
        with self.db.conn.read_ctx() as cursor:
            events = db_history_events.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=from_ts,
                    to_ts=to_ts,
                    assets=assets,
                ),
                has_premium=True,
            )
            main_currency = self.db.get_setting(cursor=cursor, name='main_currency')

        return events, main_currency

    @staticmethod
    def _calculate_balance_from_events(events: list) -> dict[Asset, FVal]:
        """Calculate balances from a list of historical events"""
        amounts: dict[Asset, FVal] = defaultdict(FVal)
        for event in events:
            if (
                (direction := event.maybe_get_direction()) is None or
                direction == EventDirection.NEUTRAL
            ):
                continue

            if direction == EventDirection.IN:
                amounts[event.asset] += event.balance.amount
            else:  # EventDirection.OUT
                amounts[event.asset] -= event.balance.amount

        return amounts
