import logging
from abc import abstractmethod
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.websockets.typedefs import (
    HistoryEventsQueryType,
    HistoryEventsStep,
    WSMessageType,
)
from rotkehlchen.assets.asset import AssetWithOracles
from rotkehlchen.db.filtering import TradesFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import MarginPosition, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeAuthCredentials,
    ExchangeLocationID,
    Location,
    T_ApiKey,
    T_ApiSecret,
    Timestamp,
)
from rotkehlchen.utils.misc import set_user_agent, ts_now
from rotkehlchen.utils.mixins.cacheable import CacheableMixIn
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock
from rotkehlchen.utils.network import create_session

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ExchangeQueryBalances = tuple[dict[AssetWithOracles, Balance] | None, str]

ExchangeHistoryFailCallback = Callable[[str], None]
ExchangeHistoryNewStepCallback = Callable[[str], None]


class ExchangeWithExtras:
    """
    An interface for exchanges that have extra properties that can be edited.
    Note: it should be used only together with ExchangeInterface to have db, name and location.
    """
    db: 'DBHandler'
    name: str
    location: Location

    @abstractmethod
    def edit_exchange_extras(self, extras: dict) -> tuple[bool, str]:
        """
        Subclasses implement this method to accept extra properties such as kraken account type.
        """

    def reset_to_db_extras(self) -> None:
        """Resets the exchange extras to the ones saved in the DB"""
        extras = self.db.get_exchange_credentials_extras(location=self.location, name=self.name)
        self.edit_exchange_extras(extras)


class ExchangeInterface(CacheableMixIn, LockableQueryMixIn):

    def __init__(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ):
        assert isinstance(api_key, T_ApiKey), (
            f'api key for {name} should be a string'
        )
        assert isinstance(secret, T_ApiSecret), (
            f'secret for {name} should be a bytestring'
        )
        super().__init__()
        self.name = name
        self.location = location
        self.db = database
        self.api_key = api_key
        self.secret = secret
        self.msg_aggregator = msg_aggregator
        self.first_connection_made = False
        self.session = create_session()
        set_user_agent(self.session)
        log.info(f'Initialized {location!s} exchange {name}')

    def reset_to_db_credentials(self) -> None:
        """Resets the exchange credentials to the ones saved in the DB"""
        with self.db.conn.read_ctx() as cursor:
            credentials_in_db = self.db.get_exchange_credentials(
                cursor=cursor,
                location=self.location,
                name=self.name,
            )
        credentials = credentials_in_db[self.location][0]
        self.edit_exchange_credentials(ExchangeAuthCredentials(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            passphrase=credentials.passphrase,
        ))

    def location_id(self) -> ExchangeLocationID:
        """Returns unique location identifier for this exchange object (name + location)"""
        return ExchangeLocationID(name=self.name, location=self.location)

    def edit_exchange_credentials(self, credentials: ExchangeAuthCredentials) -> bool:
        """Edits the exchange object with new credentials given from the API
        Returns true if an edit happened and false otherwise.

        Needs to be implemented for each subclass
        """
        if credentials.api_key is not None:
            self.api_key = credentials.api_key
        if credentials.api_secret is not None:
            self.secret = credentials.api_secret

        return credentials.api_key is not None or credentials.api_secret is not None or credentials.passphrase is not None  # noqa: E501

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

    def query_exchange_specific_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> Any | None:
        """Has to be implemented by exchanges if they have anything exchange specific


        For example poloniex loans
        """
        return None

    def first_connection(self) -> None:
        """Performs actions that should be done in the first time coming online
        and attempting to query data from an exchange.
        """
        raise NotImplementedError('first_connection() should only be implemented by subclasses')

    def validate_api_key(self) -> tuple[bool, str]:
        """Tries to make the simplest private api query to the exchange in order to
        verify the api key's validity"""
        raise NotImplementedError('validate_api_key() should only be implemented by subclasses')

    def query_online_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[list[Trade], tuple[Timestamp, Timestamp]]:
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
    ) -> list[MarginPosition]:
        """Queries the exchange's API for the margin positions history of the user

        Should be implemented by subclasses if the exchange can return margin position history in
        any form. This is only implemented for bitmex at the moment.
        """
        raise NotImplementedError(
            'query_online_margin_history() should only be implemented by subclasses',
        )

    def query_online_history_events(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> Sequence['HistoryBaseEntry']:
        """Queries the exchange's API for history events of the user

        Should be implemented in subclasses, unless query_history_events is reimplemented with
        custom logic.
        Returns events based on HistoryBaseEntry, such as HistoryEvent, AssetMovement, etc.
        """
        return []

    @protect_with_lock()
    def query_trade_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            only_cache: bool,
    ) -> list[Trade]:
        """Queries the local DB and the remote exchange for the trade history of the user

        Limits the query to the given time range and also if only_cache is True returns
        only what is already saved in the DB without performing an exchange query

        Returns the trades sorted in an ascending timestamp order
        """
        log.debug(f'Querying trade history for {self.name} exchange')
        if only_cache is False:
            ranges = DBQueryRanges(self.db)
            location_string = f'{self.location!s}_trades_{self.name}'
            with self.db.conn.read_ctx() as cursor:
                ranges_to_query = ranges.get_location_query_ranges(
                    cursor=cursor,
                    location_string=location_string,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )

            log.debug(f'Found query ranges {ranges_to_query=} for {location_string}')
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
                with self.db.user_write() as write_cursor:
                    if len(new_trades) != 0:
                        self.db.add_trades(write_cursor=write_cursor, trades=new_trades)

                    # and also set the used queried timestamp range for the exchange
                    ranges.update_used_query_range(
                        write_cursor=write_cursor,
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
            return self.db.get_trades(
                cursor=cursor,
                filter_query=filter_query,
                has_premium=True,  # is okay since the returned trades don't make it to the user
            )

    def query_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[MarginPosition]:
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
            location_string = f'{self.location!s}_margins_{self.name}'
            ranges_to_query = ranges.get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=start_ts,
                end_ts=end_ts,
            )

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
            with self.db.user_write() as write_cursor:
                if len(new_positions) != 0:
                    self.db.add_margin_positions(write_cursor, new_positions)

                # and also set the last queried timestamp for the exchange
                ranges.update_used_query_range(
                    write_cursor=write_cursor,
                    location_string=location_string,
                    queried_ranges=[(query_start_ts, query_end_ts)],
                )
            # finally append them to the already returned DB margin positions
            margin_positions.extend(new_positions)

        return margin_positions

    def send_history_events_status_msg(
            self,
            step: HistoryEventsStep,
            period: list[Timestamp] | None = None,
            name: str | None = None,
    ) -> None:
        """Send history events status WS message.
        Args:
            step (HistoryEventsStep): Current query step
            period (list[Timestamp] | None): from/to timestamps of the range being queried
            name (str | None): Used to identify multiple portfolios on the same exchange, in
                coinbaseprime for example. Defaults to self.name when None.
        """
        data: dict[str, Any] = {
            'status': str(step),
            'location': str(self.location),
            'event_type': str(HistoryEventsQueryType.HISTORY_QUERY),
            'name': name or self.name,
        }
        if period is not None:
            data['period'] = period

        self.msg_aggregator.add_message(
            message_type=WSMessageType.HISTORY_EVENTS_STATUS,
            data=data,
        )

    @protect_with_lock()
    def query_history_events(self) -> None:
        """Queries the exchange for new history events and saves them to the database."""
        self.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_STARTED)
        db = DBHistoryEvents(self.db)
        location_string = f'{self.location!s}_history_events_{self.name}'
        with self.db.conn.read_ctx() as cursor:
            ranges_to_query = (ranges := DBQueryRanges(self.db)).get_location_query_ranges(
                cursor=cursor,
                location_string=location_string,
                start_ts=Timestamp(0),
                end_ts=ts_now(),
            )

        for query_start_ts, query_end_ts in ranges_to_query:
            self.send_history_events_status_msg(
                step=HistoryEventsStep.QUERYING_EVENTS_STATUS_UPDATE,
                period=[query_start_ts, query_end_ts],
            )
            new_events = self.query_online_history_events(
                start_ts=query_start_ts,
                end_ts=query_end_ts,
            )
            with self.db.user_write() as write_cursor:
                if len(new_events) != 0:
                    db.add_history_events(write_cursor=write_cursor, history=new_events)
                ranges.update_used_query_range(
                    write_cursor=write_cursor,
                    location_string=location_string,
                    queried_ranges=[(query_start_ts, query_end_ts)],
                )
        self.send_history_events_status_msg(step=HistoryEventsStep.QUERYING_EVENTS_FINISHED)

    def query_history_with_callbacks(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            fail_callback: ExchangeHistoryFailCallback,
            new_step_data: tuple[ExchangeHistoryNewStepCallback, str] | None = None,
    ) -> None:
        """Queries the historical event endpoints for this exchange and performs actions.
        The results are saved in the DB.
        In case of failure passes the error to failure_callback

        `new_step_data` argument contains callback and exchange name to be used for steps.
        """
        if new_step_data is not None:
            new_step_callback, exchange_name = new_step_data
            new_step_callback(f'Querying {exchange_name} trades history')
        try:
            self.query_trade_history(
                start_ts=start_ts,
                end_ts=end_ts,
                only_cache=False,
            )
            if new_step_data is not None:
                new_step_callback(f'Querying {exchange_name} margin history')
            self.query_margin_history(
                start_ts=start_ts,
                end_ts=end_ts,
            )
            if new_step_data is not None:
                new_step_callback(f'Querying {exchange_name} events history')
            self.query_history_events()
            # No new step for exchange_specific_history since it is not used in any exchange atm.
            self.query_exchange_specific_history(
                start_ts=start_ts,
                end_ts=end_ts,
            )
        except RemoteError as e:
            fail_callback(str(e))

    def send_unknown_asset_message(
            self,
            asset_identifier: str,
            details: str,
    ) -> None:
        """Log warning and send WS message to notify user of unknown asset found on an exchange.
        Args:
            asset_identifier (str): Asset identifier of the unknown asset.
            details (str): Details about what type of event was being processed
                when the unknown asset was encountered.
        """
        log.warning(f'Found unknown {self.location.serialize()} {self.name} asset {asset_identifier} in {details}.')  # noqa: E501
        self.msg_aggregator.add_message(
            message_type=WSMessageType.EXCHANGE_UNKNOWN_ASSET,
            data={
                'location': self.location.serialize(),
                'name': self.name,
                'identifier': asset_identifier,
                'details': details,
            },
        )
