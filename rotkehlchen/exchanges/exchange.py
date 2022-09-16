import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

import requests

from rotkehlchen.accounting.ledger_actions import LedgerAction
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.db.filtering import (
    AssetMovementsFilterQuery,
    LedgerActionsFilterQuery,
    TradesFilterQuery,
)
from rotkehlchen.db.ledger_actions import DBLedgerActions
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeLocationID,
    Location,
    T_ApiKey,
    T_ApiSecret,
    Timestamp,
)
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ExchangeQueryBalances = Tuple[Optional[Dict[AssetWithSymbol, Balance]], str]
ExchangeHistorySuccessCallback = Callable[
    [List[Trade], List[MarginPosition], List[AssetMovement], Any],
    None,
]

ExchangeHistoryFailCallback = Callable[[str], None]


class ExchangeInterface(CacheableMixIn, LockableQueryMixIn):

    def __init__(
            self,
            name: str,
            location: Location,
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
        self.location = location
        self.db = database
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        log.info(f'Initialized {str(location)} exchange {name}')

    def location_id(self) -> ExchangeLocationID:
        """Returns unique location identifier for this exchange object (name + location)"""
        return ExchangeLocationID(name=self.name, location=self.location)

    def edit_exchange_credentials(
            self,
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
    ) -> bool:
        """Edits the exchange object with new credentials given from the API
        Returns true if an edit happened and false otherwise.

        Needs to be implemented for each subclass
        """
        if api_key is not None:
            self.api_key = api_key
        if api_secret is not None:
            self.secret = api_secret

        return api_key is not None or api_secret is not None or passphrase is not None

    def edit_exchange(
            self,
            name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            **kwargs: Any,
    ) -> Tuple[bool, str]:
        """Edits the exchange object with new info given from the API

        Returns False and error message in case of problems

        If extra exchange info should be edited this needs to also be implemented by the subclass.
        """
        passphrase = kwargs.get('passphrase')
        old_passphrase = None
        if passphrase is not None:  # backup old passphrase
            with self.db.conn.read_ctx() as cursor:
                mapping = self.db.get_exchange_credentials(cursor, name=self.name, location=self.location)  # noqa: E501
            credentials = mapping.get(self.location)
            if not credentials or len(credentials) == 0 or credentials[0].passphrase is None:
                old_passphrase = None  # should not happen, unless passphrase is optional
                log.warning(
                    f'When updating the passphrase for {self.name} {str(self.location)} '
                    f'exchange, could not find an old passphrase to restore.',
                )
            else:
                old_passphrase = credentials[0].passphrase

        old_api_key = self.api_key
        old_api_secret = self.secret
        changed = self.edit_exchange_credentials(api_key, api_secret, passphrase)
        if changed is True:
            try:
                success, message = self.validate_api_key()
            except Exception as e:  # pylint: disable=broad-except
                success = False
                message = str(e)

            if success is False:
                self.edit_exchange_credentials(old_api_key, old_api_secret, old_passphrase)
                return False, message

        if name is not None:
            self.name = name

        return True, ''

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
        raise NotImplementedError('query_balances should only be implemented by subclasses')

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
    ) -> Tuple[List[Trade], Tuple[Timestamp, Timestamp]]:
        """Queries the exchange's API for the trade history of the user

        Should be implemented by subclasses if the exchange can return trade history in any form.
        This is not implemented only for bitmex as it only returns margin positions

        Returns a tuple of the trades of the exchange and a Tuple of the queried time
        range. The time range can differ from the given time range if an error happened
        and the call stopped in the middle.
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

    def query_online_income_loss_expense(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[LedgerAction]:
        """Queries the exchange's API for the ledger actions of the user

        Should be implemented in subclasses.
        Has to be implemented by exchanges if they have anything exchange specific

        For example coinbase
        """
        raise NotImplementedError(
            'query_online_income_loss_expense should only be implemented by subclasses',
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

        Returns the trades sorted in an ascending timestamp order
        """
        log.debug(f'Querying trade history for {self.name} exchange')
        if only_cache is False:
            ranges = DBQueryRanges(self.db)
            location_string = f'{str(self.location)}_trades_{self.name}'
            with self.db.conn.read_ctx() as cursor:
                ranges_to_query = ranges.get_location_query_ranges(
                    cursor=cursor,
                    location_string=location_string,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )

            for query_start_ts, query_end_ts in ranges_to_query:
                # If we have a time frame we have not asked the exchange for trades then
                # go ahead and do that now
                log.debug(
                    f'Querying online trade history for {self.name} between '
                    f'{query_start_ts} and {query_end_ts}',
                )
                new_trades, queried_range = self.query_online_trade_history(
                    start_ts=query_start_ts,
                    end_ts=query_end_ts,
                )

                # make sure to add them to the DB
                with self.db.user_write() as cursor:
                    if new_trades != []:
                        self.db.add_trades(write_cursor=cursor, trades=new_trades)

                    # and also set the used queried timestamp range for the exchange
                    ranges.update_used_query_range(
                        write_cursor=cursor,
                        location_string=location_string,
                        queried_ranges=[queried_range],
                    )

        # Read all requested trades from the DB
        with self.db.conn.read_ctx() as cursor:
            filter_query = TradesFilterQuery.make(
                from_ts=start_ts,
                to_ts=end_ts,
                location=self.location,
            )
            trades = self.db.get_trades(
                cursor=cursor,
                filter_query=filter_query,
                has_premium=True,  # is okay since the returned trades don't make it to the user
            )

        return trades

    def query_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[MarginPosition]:
        """
        Queries the local DB and the remote exchange for the margin positions history of the user
        """
        log.debug(f'Querying margin history for {self.name} exchange')
        with self.db.conn.read_ctx() as cursor:
            margin_positions = self.db.get_margin_positions(
                cursor=cursor,
                from_ts=start_ts,
                to_ts=end_ts,
                location=self.location,
            )
            ranges = DBQueryRanges(self.db)
            location_string = f'{str(self.location)}_margins_{self.name}'
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )

        with self.db.user_write() as cursor:
            for query_start_ts, query_end_ts in ranges_to_query:
                log.debug(
                    f'Querying online margin history for {self.name} between '
                    f'{query_start_ts} and {query_end_ts}',
                )
                new_positions = self.query_online_margin_history(
                    start_ts=query_start_ts,
                    end_ts=query_end_ts,
                )

                # make sure to add them to the DB
                if len(new_positions) != 0:
                    self.db.add_margin_positions(cursor, new_positions)

                # and also set the last queried timestamp for the exchange
                ranges.update_used_query_range(
                    write_cursor=cursor,
                    location_string=location_string,
                    queried_ranges=[(query_start_ts, query_end_ts)],
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
        log.debug(f'Querying deposits/withdrawals history for {self.name} exchange')
        filter_query = AssetMovementsFilterQuery.make(
            from_ts=start_ts,
            to_ts=end_ts,
            location=self.location,
        )
        with self.db.conn.read_ctx() as cursor:
            asset_movements = self.db.get_asset_movements(
                cursor=cursor,
                filter_query=filter_query,
                has_premium=True,  # is okay since the returned trades don't make it to the user
            )
            if only_cache:
                return asset_movements

            ranges = DBQueryRanges(self.db)
            location_string = f'{str(self.location)}_asset_movements_{self.name}'
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )

        with self.db.user_write() as cursor:
            for query_start_ts, query_end_ts in ranges_to_query:
                log.debug(
                    f'Querying online deposits/withdrawals for {self.name} between '
                    f'{query_start_ts} and {query_end_ts}',
                )
                new_movements = self.query_online_deposits_withdrawals(
                    start_ts=query_start_ts,
                    end_ts=query_end_ts,
                )

                if len(new_movements) != 0:
                    self.db.add_asset_movements(cursor, new_movements)

                ranges.update_used_query_range(
                    write_cursor=cursor,
                    location_string=location_string,
                    queried_ranges=[(query_start_ts, query_end_ts)],
                )
                asset_movements.extend(new_movements)

        return asset_movements

    @protect_with_lock()
    def query_income_loss_expense(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            only_cache: bool,
    ) -> List[LedgerAction]:
        """Queries the local DB and the exchange for the income/loss/expense history of the user

        If only_cache is true only what is already cached in the DB is returned without
        an actual exchange query.
        """
        db = DBLedgerActions(self.db, self.db.msg_aggregator)
        filter_query = LedgerActionsFilterQuery.make(
            from_ts=start_ts,
            to_ts=end_ts,
            location=self.location,
        )

        with self.db.conn.read_ctx() as cursor:
            # has_premium True is fine here since the result of this is not user facing atm
            ledger_actions = db.get_ledger_actions(cursor, filter_query=filter_query, has_premium=True)  # noqa: E501
            if only_cache:
                return ledger_actions

            ranges = DBQueryRanges(self.db)
            location_string = f'{str(self.location)}_ledger_actions_{self.name}'
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )

        with self.db.user_write() as cursor:
            for query_start_ts, query_end_ts in ranges_to_query:
                new_ledger_actions = self.query_online_income_loss_expense(
                    start_ts=query_start_ts,
                    end_ts=query_end_ts,
                )
                if len(new_ledger_actions) != 0:
                    db.add_ledger_actions(cursor, new_ledger_actions)

                ranges.update_used_query_range(
                    write_cursor=cursor,
                    location_string=location_string,
                    queried_ranges=[(query_start_ts, query_end_ts)],
                )
                ledger_actions.extend(new_ledger_actions)

        return ledger_actions

    def query_history_with_callbacks(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            success_callback: ExchangeHistorySuccessCallback,
            fail_callback: ExchangeHistoryFailCallback,
    ) -> None:
        """Queries the historical event endpoints for this exchange and performs actions.

        In case of success passes the result to success_callback.
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
            # Query (and save in the DB) any ledger actions. They will be included in history l8er
            self.query_income_loss_expense(
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
