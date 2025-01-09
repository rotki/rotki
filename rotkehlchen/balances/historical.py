from collections import defaultdict
from typing import TYPE_CHECKING, TypedDict

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import NotFoundError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import EventDirection
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


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
        events, main_currency = self._get_events_and_currency(timestamp)
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
        events, main_currency = self._get_events_and_currency(timestamp, (asset,))
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

    def _get_events_and_currency(
            self,
            timestamp: Timestamp,
            assets: tuple[Asset, ...] | None = None,
    ) -> tuple[list, Asset]:
        """Helper method to get historical events and main currency from DB"""
        db_history_events = DBHistoryEvents(database=self.db)
        with self.db.conn.read_ctx() as cursor:
            events = db_history_events.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    to_ts=timestamp,
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
