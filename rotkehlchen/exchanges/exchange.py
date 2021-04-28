import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_location
from rotkehlchen.typing import ApiKey, ApiSecret, T_ApiKey, T_ApiSecret, Timestamp
from rotkehlchen.utils.mixins import CacheableMixIn, LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ExchangeQueryBalances = Tuple[Optional[Dict[Asset, Balance]], str]
ExchangeHistorySuccessCallback = Callable[
    [List[Trade], List[MarginPosition], List[AssetMovement], Any],
    None,
]

ExchangeHistoryFailCallback = Callable[[str], None]


class ExchangeInterface(CacheableMixIn, LockableQueryMixIn):

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

    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        """Returns the balances held in the exchange in the following format:

        Successful response:
        (
            {  # dict can be empty
                'name' : Balance(amount=1337, usd_value=42),
                'ICN': Balance(amount=42, usd_value=1337)
            },
            '',  # empty string
        )

        Unsuccessful response:
        (
            None,
            'The reason of the failure',  # non-empty string
        )

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

    @protect_with_lock()
    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            only_cache: bool,
    ) -> List[Trade]:
        """Queries the local DB and the remote exchange for the trade history of the user

        Limits the query to the given time range and also if only_cache is True returns
        only what is already saved in the DB without performing an exchange query
        """
        trades = self.db.get_trades(
            from_ts=start_ts,
            to_ts=end_ts,
            location=deserialize_location(self.name),
        )
        if only_cache:
            return trades

        ranges = DBQueryRanges(self.db)
        ranges_to_query = ranges.get_location_query_ranges(
            location_string=f'{self.name}_trades',
            start_ts=start_ts,
            end_ts=end_ts,
        )

        new_trades = []
        for query_start_ts, query_end_ts in ranges_to_query:
            # If we have a time frame we have not asked the exchange for trades then
            # go ahead and do that now
            new_trades.extend(self.query_online_trade_history(
                start_ts=query_start_ts,
                end_ts=query_end_ts,
            ))

        # make sure to add them to the DB
        if new_trades != []:
            self.db.add_trades(new_trades)
        # and also set the used queried timestamp range for the exchange
        ranges.update_used_query_range(
            location_string=f'{self.name}_trades',
            start_ts=start_ts,
            end_ts=end_ts,
            ranges_to_query=ranges_to_query,
        )
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
        ranges = DBQueryRanges(self.db)
        ranges_to_query = ranges.get_location_query_ranges(
            location_string=f'{self.name}_margins',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        new_positions = []
        for query_start_ts, query_end_ts in ranges_to_query:
            new_positions.extend(self.query_online_margin_history(
                start_ts=query_start_ts,
                end_ts=query_end_ts,
            ))

        # make sure to add them to the DB
        if new_positions != []:
            self.db.add_margin_positions(new_positions)
        # and also set the last queried timestamp for the exchange
        ranges.update_used_query_range(
            location_string=f'{self.name}_margins',
            start_ts=start_ts,
            end_ts=end_ts,
            ranges_to_query=ranges_to_query,
        )
        # finally append them to the already returned DB margin positions
        margin_positions.extend(new_positions)

        return margin_positions

    @protect_with_lock()
    def query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            only_cache: bool,
    ) -> List[AssetMovement]:
        """Queries the local DB and the exchange for the deposits/withdrawal history of the user

        If only_cache is true only what is already cached in the DB is returned without
        an actual exchange query.
        """
        asset_movements = self.db.get_asset_movements(
            from_ts=start_ts,
            to_ts=end_ts,
            location=deserialize_location(self.name),
        )
        if only_cache:
            return asset_movements

        ranges = DBQueryRanges(self.db)
        ranges_to_query = ranges.get_location_query_ranges(
            location_string=f'{self.name}_asset_movements',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        new_movements = []
        for query_start_ts, query_end_ts in ranges_to_query:
            new_movements.extend(self.query_online_deposits_withdrawals(
                start_ts=query_start_ts,
                end_ts=query_end_ts,
            ))

        if new_movements != []:
            self.db.add_asset_movements(new_movements)
        ranges.update_used_query_range(
            location_string=f'{self.name}_asset_movements',
            start_ts=start_ts,
            end_ts=end_ts,
            ranges_to_query=ranges_to_query,
        )
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
                only_cache=False,
            )
            margin_history = self.query_margin_history(
                start_ts=start_ts,
                end_ts=end_ts,
            )
            asset_movements = self.query_deposits_withdrawals(
                start_ts=start_ts,
                end_ts=end_ts,
                only_cache=False,
            )
            exchange_specific_data = self.query_exchange_specific_history(  # pylint: disable=assignment-from-none  # noqa: E501
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
