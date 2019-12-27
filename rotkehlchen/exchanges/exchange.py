#!/usr/bin/env python
import logging
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_location
from rotkehlchen.typing import ApiKey, ApiSecret, T_ApiKey, T_ApiSecret, Timestamp
from rotkehlchen.utils.interfaces import CacheableObject, LockableQueryObject

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ExchangeHistorySuccessCallback = Callable[
    [List[Trade], List[MarginPosition], List[AssetMovement], Any],
    None,
]

ExchangeHistoryFailCallback = Callable[[str], None]


class ExchangeInterface(CacheableObject, LockableQueryObject):

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
    ):
        assert isinstance(api_key, T_ApiKey), (
            'api key for {} should be a string'.format(name)
        )
        assert isinstance(secret, T_ApiSecret), (
            'secret for {} should be a bytestring'.format(name)
        )
        super().__init__()
        self.name = name
        self.db = database
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        log.info(f'Initialized {name} exchange')

    def query_balances(self) -> Tuple[Optional[dict], str]:
        """Returns the balances held in the exchange in the following format:
        {
            'name' : {'amount': 1337, 'usd_value': 42},
            'ICN': {'amount': 42, 'usd_value': 1337}
        }

        The name must be the canonical name used by rotkehlchen
        """
        raise NotImplementedError("query_balances should only be implemented by subclasses")

    def query_exchange_specific_history(  # pylint: disable=no-self-use
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> Optional[Any]:
        """Has to be implemented by exchanges if they have anything exchange specific


        For example poloniex loans
        """
        return None

    def first_connection(self) -> None:
        """Performs actions that should be done in the first time coming online
        and attempting to query data from an exchange.
        """
        raise NotImplementedError('first_connection() should only be implemented by subclasses')

    def validate_api_key(self) -> Tuple[bool, str]:
        """Tries to make the simplest private api query to the exchange in order to
        verify the api key's validity"""
        raise NotImplementedError('validate_api_key() should only be implemented by subclasses')

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        """Queries the exchange's API for the trade history of the user

        Should be implemented by subclasses if the exchange can return trade history in any form.
        This is not implemented only for bitmex as it only returns margin positions
        """
        raise NotImplementedError(
            'query_online_trade_history() should only be implemented by subclasses',
        )

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[MarginPosition]:
        """Queries the exchange's API for the margin positions history of the user

        Should be implemented by subclasses if the exchange can return margin position history in
        any form. This is only implemented for bitmex at the moment.
        """
        raise NotImplementedError(
            'query_online_margin_history() should only be implemented by subclasses',
        )

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """Queries the exchange's API for the asset movements of the user

        Should be implemented in subclasses.
        """
        raise NotImplementedError(
            'query_online_deposits_withdrawals should only be implemented by subclasses',
        )

    def get_online_query_ranges(
            self,
            location_suffix: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Tuple[Timestamp, Timestamp]]:
        """Takes in the start/end ts for a location query and after checking the
        last query ranges of the DB provides a list of timestamp ranges that still
        need to be queried."""
        queried_range = self.db.get_used_query_range(self.name + location_suffix)
        if not queried_range:
            ranges_to_query = [(start_ts, end_ts)]
        else:
            ranges_to_query = []
            if start_ts < queried_range[0]:
                ranges_to_query.append((start_ts, Timestamp(queried_range[0] - 1)))

            if end_ts > queried_range[1]:
                ranges_to_query.append((Timestamp(queried_range[1] + 1), end_ts))

        return ranges_to_query

    def update_used_query_range(
            self,
            location_suffix: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            ranges_to_query: List[Tuple[Timestamp, Timestamp]],
    ) -> None:
        """Depending on the ranges to query and the given start and end ts update the DB"""
        starts = [x[0] for x in ranges_to_query]
        starts.append(start_ts)
        ends = [x[1] for x in ranges_to_query]
        ends.append(end_ts)

        self.db.update_used_query_range(
            name=self.name + location_suffix,
            start_ts=min(starts),
            end_ts=max(ends),
        )

    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        """Queries the local DB and the remote exchange for the trade history of the user"""
        trades = self.db.get_trades(
            from_ts=start_ts,
            to_ts=end_ts,
            location=deserialize_location(self.name),
        )
        ranges_to_query = self.get_online_query_ranges('_trades', start_ts, end_ts)

        new_trades = []
        for query_start_ts, query_end_ts in ranges_to_query:
            # If we have a time frame we have not asked the exchange for trades then
            # go ahead and do that now
            try:
                new_trades.extend(self.query_online_trade_history(
                    start_ts=query_start_ts,
                    end_ts=query_end_ts,
                ))
            except NotImplementedError:
                msg = 'query_online_trade_history should only not be implemented by bitmex'
                assert self.name == 'bitmex', msg
                pass

        # make sure to add them to the DB
        if new_trades != []:
            self.db.add_trades(new_trades)
        # and also set the used queried timestamp range for the exchange
        self.update_used_query_range('_trades', start_ts, end_ts, ranges_to_query)
        # finally append them to the already returned DB trades
        trades.extend(new_trades)

        return trades

    def query_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[MarginPosition]:
        """Queries the local DB and the remote exchange for the margin positions history of the user
        """
        margin_positions = self.db.get_margin_positions(
            from_ts=start_ts,
            to_ts=end_ts,
            location=self.name,
        )
        ranges_to_query = self.get_online_query_ranges('_margins', start_ts, end_ts)

        new_positions = []
        for query_start_ts, query_end_ts in ranges_to_query:
            try:
                new_positions.extend(self.query_online_margin_history(
                    start_ts=query_start_ts,
                    end_ts=query_end_ts,
                ))
            except NotImplementedError:
                pass

        # make sure to add them to the DB
        if new_positions != []:
            self.db.add_margin_positions(new_positions)
        # and also set the last queried timestamp for the exchange
        self.update_used_query_range('_margins', start_ts, end_ts, ranges_to_query)
        # finally append them to the already returned DB margin positions
        margin_positions.extend(new_positions)

        return margin_positions

    def query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        """Queries the local DB and the exchange for the deposits/withdrawal history of the user"""
        asset_movements = self.db.get_asset_movements(
            from_ts=start_ts,
            to_ts=end_ts,
            location=self.name,
        )
        ranges_to_query = self.get_online_query_ranges('_asset_movements', start_ts, end_ts)

        new_movements = []
        for query_start_ts, query_end_ts in ranges_to_query:
            new_movements.extend(self.query_online_deposits_withdrawals(
                start_ts=query_start_ts,
                end_ts=query_end_ts,
            ))

        if new_movements != []:
            self.db.add_asset_movements(new_movements)
        self.update_used_query_range('_asset_movements', start_ts, end_ts, ranges_to_query)
        asset_movements.extend(new_movements)

        return asset_movements

    def query_history_with_callbacks(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            success_callback: ExchangeHistorySuccessCallback,
            fail_callback: ExchangeHistoryFailCallback,
    ) -> None:
        """Queries the historical event endpoints for this exchange and performs actions.

        In case of success passes the result to successcallback.
        In case of failure passes the error to failure_callback
        """
        try:
            trades_history = self.query_trade_history(
                start_ts=start_ts,
                end_ts=end_ts,
            )
            margin_history = self.query_margin_history(
                start_ts=start_ts,
                end_ts=end_ts,
            )
            asset_movements = self.query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
            )
            exchange_specific_data = self.query_exchange_specific_history(
                start_ts=start_ts,
                end_ts=end_ts,
            )
            success_callback(
                trades_history,
                margin_history,
                asset_movements,
                exchange_specific_data,
            )

        except RemoteError as e:
            fail_callback(str(e))
