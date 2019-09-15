#!/usr/bin/env python
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import requests
from gevent.lock import Semaphore

from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ApiKey, ApiSecret, T_ApiKey, T_ApiSecret, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ExchangeHistorySuccessCallback = Callable[
    [List[Trade], List[MarginPosition], List[AssetMovement], Any],
    None,
]

ExchangeHistoryFailCallback = Callable[[str], None]


def data_up_todate(json_data: Dict[str, Any], start_ts: Timestamp, end_ts: Timestamp) -> bool:
    if 'data' not in json_data or 'start_time' not in json_data or 'end_time' not in json_data:
        return False

    start_ts_ok = (
        (json_data['start_time'] is not None) and
        start_ts >= json_data['start_time']
    )
    end_ts_ok = (
        json_data['end_time'] is not None and
        end_ts <= json_data['end_time']
    )
    return start_ts_ok and end_ts_ok


class ExchangeInterface():

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
    ):
        assert isinstance(api_key, T_ApiKey), (
            'api key for {} should be a bytestring'.format(name)
        )
        assert isinstance(secret, T_ApiSecret), (
            'secret for {} should be a bytestring'.format(name)
        )
        self.name = name
        self.db = database
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})

        # -- Cache related variales
        self.lock = Semaphore()
        self.results_cache: Dict[str, Any] = {}
        # The amount of seconds cache of cache_response_timewise is supposed to last
        # IF 0 is given then cache is disabled. A zero value also disabled the trades cache
        self.cache_ttl_secs = CACHE_RESPONSE_FOR_SECS
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

    def query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[AssetMovement]:
        raise NotImplementedError(
            'query_deposits_withdrawals should only be implemented by subclasses',
        )

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

    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Trade]:
        """Queries the local DB and the remote exchange for the trade history of the user"""
        trades = self.db.get_trades(from_ts=start_ts, to_ts=end_ts, location=self.name)
        last_trade_db_ts = self.db.get_last_query_time(self.name + '_trades')
        # If last DB trade is within the time frame, no need to ask the exchange
        if last_trade_db_ts >= end_ts:
            return trades

        # If we have a time frame we have not asked the exchange for trades then
        # go ahead and do that now
        try:
            new_trades = self.query_online_trade_history(
                start_ts=Timestamp(last_trade_db_ts + 1),
                end_ts=end_ts,
            )
        except NotImplementedError:
            msg = 'query_online_trade_history should only not be implemented by bitmex'
            assert self.name == 'bitmex', msg
            new_trades = []

        # make sure to add them to the DB
        if new_trades != []:
            self.db.add_trades(new_trades)
        # and also set the last queried timestamp for the exchange
        self.db.update_last_query_time(name=self.name + '_trades', ts=end_ts)
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

        last_margin_db_ts = self.db.get_last_query_time(self.name + '_margins')
        # If last margin is within the time frame, no need to ask the exchange
        if last_margin_db_ts >= end_ts:
            return margin_positions

        # IF we have a time frame we have not asked the exchange for trades then
        # go ahead and do that now
        try:
            new_positions = self.query_online_margin_history(
                start_ts=Timestamp(last_margin_db_ts + 1),
                end_ts=end_ts,
            )
        except NotImplementedError:
            new_positions = []

        # make sure to add them to the DB
        if new_positions != []:
            self.db.add_margin_positions(new_positions)
        # and also set the last queried timestamp for the exchange
        self.db.update_last_query_time(name=self.name + '_margins', ts=end_ts)
        # finally append them to the already returned DB margin positions
        margin_positions.extend(new_positions)

        return margin_positions

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
