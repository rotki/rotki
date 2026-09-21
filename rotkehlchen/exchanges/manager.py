import logging
import threading
from collections import defaultdict
from importlib import import_module
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.api.websockets.typedefs import HistoryEventsStep
from rotkehlchen.connections.types import (
    ConnectionIdentifier,
    ConnectorIdentifier,
    IntegrationConnection,
    connection_range_name,
)
from rotkehlchen.db.constants import (
    BINANCE_MARKETS_KEY,
    GATE_LOCATION_KEY,
    KRAKEN_ACCOUNT_TYPE_KEY,
    KRAKEN_FUTURES_API_KEY_KEY,
    KRAKEN_FUTURES_API_SECRET_KEY,
    OKX_LOCATION_KEY,
)
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.exchanges.binance import BINANCE_BASE_URL, BINANCEUS_BASE_URL
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeWithExtras, HistoryEventQueue
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BINANCEUS,
    LOCATION_BIT2ME,
    LOCATION_BITCOINDE,
    LOCATION_BITFINEX,
    LOCATION_BITMEX,
    LOCATION_BITPANDA,
    LOCATION_BITSTAMP,
    LOCATION_BYBIT,
    LOCATION_COINBASE,
    LOCATION_COINBASEPRIME,
    LOCATION_COINEX,
    LOCATION_CRYPTOCOM,
    LOCATION_GATE,
    LOCATION_GEMINI,
    LOCATION_HTX,
    LOCATION_ICONOMI,
    LOCATION_INDEPENDENTRESERVE,
    LOCATION_KRAKEN,
    LOCATION_KUCOIN,
    LOCATION_OKX,
    LOCATION_POLONIEX,
    LOCATION_WOO,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeAuthCredentials,
    Timestamp,
)

from .constants import EXCHANGES_WITHOUT_API_SECRET, SUPPORTED_EXCHANGES

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.gate import GateLocation
    from rotkehlchen.exchanges.kraken import KrakenAccountType
    from rotkehlchen.exchanges.okx import OkxLocation
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# The module and class implementing every exchange connector
EXCHANGE_CONNECTOR_CLASSES: Final[dict[str, tuple[str, str]]] = {
    LOCATION_BINANCE: ('rotkehlchen.exchanges.binance', 'Binance'),
    LOCATION_BINANCEUS: ('rotkehlchen.exchanges.binance', 'Binance'),
    LOCATION_BIT2ME: ('rotkehlchen.exchanges.bit2me', 'Bit2me'),
    LOCATION_BITCOINDE: ('rotkehlchen.exchanges.bitcoinde', 'Bitcoinde'),
    LOCATION_BITFINEX: ('rotkehlchen.exchanges.bitfinex', 'Bitfinex'),
    LOCATION_BITMEX: ('rotkehlchen.exchanges.bitmex', 'Bitmex'),
    LOCATION_BITPANDA: ('rotkehlchen.exchanges.bitpanda', 'Bitpanda'),
    LOCATION_BITSTAMP: ('rotkehlchen.exchanges.bitstamp', 'Bitstamp'),
    LOCATION_BYBIT: ('rotkehlchen.exchanges.bybit', 'Bybit'),
    LOCATION_COINBASE: ('rotkehlchen.exchanges.coinbase', 'Coinbase'),
    LOCATION_COINBASEPRIME: ('rotkehlchen.exchanges.coinbaseprime', 'Coinbaseprime'),
    LOCATION_COINEX: ('rotkehlchen.exchanges.coinex', 'Coinex'),
    LOCATION_CRYPTOCOM: ('rotkehlchen.exchanges.cryptocom', 'Cryptocom'),
    LOCATION_GATE: ('rotkehlchen.exchanges.gate', 'Gate'),
    LOCATION_GEMINI: ('rotkehlchen.exchanges.gemini', 'Gemini'),
    LOCATION_HTX: ('rotkehlchen.exchanges.htx', 'Htx'),
    LOCATION_ICONOMI: ('rotkehlchen.exchanges.iconomi', 'Iconomi'),
    LOCATION_INDEPENDENTRESERVE: ('rotkehlchen.exchanges.independentreserve', 'Independentreserve'),  # noqa: E501
    LOCATION_KRAKEN: ('rotkehlchen.exchanges.kraken', 'Kraken'),
    LOCATION_KUCOIN: ('rotkehlchen.exchanges.kucoin', 'Kucoin'),
    LOCATION_OKX: ('rotkehlchen.exchanges.okx', 'Okx'),
    LOCATION_POLONIEX: ('rotkehlchen.exchanges.poloniex', 'Poloniex'),
    LOCATION_WOO: ('rotkehlchen.exchanges.woo', 'Woo'),
}


def exchange_connector_class(connector: str) -> type[ExchangeInterface]:
    """May raise KeyError for a connector that is not a supported exchange"""
    module_name, class_name = EXCHANGE_CONNECTOR_CLASSES[connector]
    return getattr(import_module(module_name), class_name)


class ExchangeManager:

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        # the connected exchanges of every connector
        self.connected_exchanges: dict[str, list[ExchangeInterface]] = defaultdict(list)
        self.msg_aggregator = msg_aggregator
        # Serializes compound mutations of connected_exchanges (check-then-append,
        # check-then-rebind) together with their DB persistence: concurrent api
        # requests adding/removing exchanges could otherwise lose each other's
        # update -- resurrecting a deleted exchange, registering a duplicate whose
        # balances get double-counted, or persisting credentials the registry no
        # longer holds. Never held across network calls.
        self.registry_lock = threading.Lock()

    def connected_and_syncing_exchanges_num(self) -> int:
        return sum(1 for _ in self.iterate_exchanges())

    def get_exchange(self, identifier: str) -> ExchangeInterface | None:
        """Get the exchange object of a connection. Returns None if it is not connected."""
        for exchanges in list(self.connected_exchanges.values()):
            for exchange in exchanges:
                if exchange.connection_identifier == identifier:
                    return exchange

        return None

    def get_exchange_by_name(self, connector: str, name: str) -> ExchangeInterface | None:
        for exchange in self.connected_exchanges.get(connector, ()):
            if exchange.name == name:
                return exchange

        return None

    def iterate_exchanges(self) -> Iterator[ExchangeInterface]:
        """Iterate all connected and syncing exchanges"""
        # non_syncing_exchanges is a cached setting kept in sync on every write, so read it
        # from the in-memory cache instead of doing a full settings DB read on every call.
        excluded = CachedSettings().get_settings().non_syncing_exchanges
        # iterate a snapshot: api threads add/remove exchanges concurrently and a dict
        # mutated mid-iteration would raise RuntimeError, killing the scheduler
        for exchanges in list(self.connected_exchanges.values()):
            for exchange in exchanges:
                # We are not yielding excluded exchanges
                if exchange.connection_identifier not in excluded:
                    yield exchange

    def edit_exchange(
            self,
            identifier: str,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: KrakenAccountType | None,
            kraken_futures_api_key: ApiKey | None,
            kraken_futures_api_secret: ApiSecret | None,
            binance_selected_trade_pairs: list[str] | None,
            okx_location: OkxLocation | None,
            gate_location: GateLocation | None = None,
    ) -> tuple[bool, str]:
        """Edits both the exchange object and the database entry

        Returns True if an entry was found and edited and false otherwise
        """
        exchangeobj = self.get_exchange(identifier)
        if not exchangeobj:
            return False, f'Could not find exchange connection {identifier} for editing'
        if (
                new_name is not None and new_name != exchangeobj.name and
                self.get_exchange_by_name(connector=exchangeobj.location, name=new_name) is not None  # noqa: E501
        ):
            return False, f'{exchangeobj.location!s} exchange {new_name} is already registered'

        # First validate exchange credentials
        edited = exchangeobj.edit_exchange_credentials(ExchangeAuthCredentials(
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        ))
        if edited is True:
            try:
                credentials_are_valid, msg = exchangeobj.validate_api_key()
            except Exception as e:  # pylint: disable=broad-except
                msg = str(e)
                credentials_are_valid = False

            if credentials_are_valid is False:
                exchangeobj.reset_to_db_credentials()
                return False, f'New credentials are invalid. {msg}'

        # Then edit extra properties if needed
        if isinstance(exchangeobj, ExchangeWithExtras):
            success, msg = exchangeobj.edit_exchange_extras({
                KRAKEN_ACCOUNT_TYPE_KEY: kraken_account_type,
                KRAKEN_FUTURES_API_KEY_KEY: kraken_futures_api_key,
                KRAKEN_FUTURES_API_SECRET_KEY: kraken_futures_api_secret,
                BINANCE_MARKETS_KEY: binance_selected_trade_pairs,
                OKX_LOCATION_KEY: okx_location,
                GATE_LOCATION_KEY: gate_location,
            })
            if success is False:
                exchangeobj.reset_to_db_credentials()
                return False, f'Failed to edit exchange extras. {msg}'

        try:
            with self.database.user_write() as cursor:
                self.database.edit_exchange(
                    cursor,
                    identifier=exchangeobj.connection_identifier,
                    new_name=new_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                    kraken_account_type=kraken_account_type,
                    kraken_futures_api_key=kraken_futures_api_key,
                    kraken_futures_api_secret=kraken_futures_api_secret,
                    binance_selected_trade_pairs=binance_selected_trade_pairs,
                    okx_location=okx_location,
                    gate_location=gate_location,
                )
        except InputError as e:
            exchangeobj.reset_to_db_credentials()  # DB is already rolled back at this point
            if isinstance(exchangeobj, ExchangeWithExtras):
                exchangeobj.reset_to_db_extras()
            return False, f"Couldn't update exchange properties in the DB. {e!s}"

        # Finally edit the name of the exchange object
        if new_name is not None:
            exchangeobj.name = new_name

        return True, ''

    def delete_exchange(self, identifier: str) -> tuple[bool, str]:
        """Deletes an exchange connection from both connected_exchanges and the DB"""
        with self.registry_lock:
            if (exchange := self.get_exchange(identifier)) is None:
                return False, f'Exchange connection {identifier} is not registered'

            connector = exchange.location
            if len(remaining := [x for x in self.connected_exchanges[connector] if x is not exchange]) == 0:  # noqa: E501
                self.connected_exchanges.pop(connector)
            else:
                self.connected_exchanges[connector] = remaining

            # remove from the db under the same lock: setup_exchange persists under
            # it too, so its DB write cannot interleave with this removal and leave
            # credentials in the DB for an exchange the registry no longer holds
            with self.database.user_write() as write_cursor:
                self.database.remove_exchange(write_cursor=write_cursor, identifier=exchange.connection_identifier)  # noqa: E501
        return True, ''

    def delete_all_exchanges(self) -> None:
        """Deletes all exchanges from the manager. Not from the DB"""
        self.connected_exchanges.clear()

    def get_connected_exchanges_info(self) -> list[dict[str, Any]]:
        exchange_info = []
        # snapshot since api threads add/remove exchanges concurrently
        for connector, exchanges in list(self.connected_exchanges.items()):
            for exchangeobj in exchanges:
                data = {
                    'identifier': exchangeobj.connection_identifier,
                    'name': exchangeobj.name,
                    'connector': str(connector),
                    'location': str(exchangeobj.data_location),
                }
                if connector == LOCATION_KRAKEN:  # ignore type since we know this is kraken here
                    data[KRAKEN_ACCOUNT_TYPE_KEY] = str(exchangeobj.account_type)  # type: ignore
                elif connector == LOCATION_OKX:  # ignore type since we know this is okx here
                    data[OKX_LOCATION_KEY] = exchangeobj.okx_location.serialize()  # type: ignore
                elif connector == LOCATION_GATE:  # ignore type since we know this is gate here
                    data[GATE_LOCATION_KEY] = exchangeobj.gate_location.serialize()  # type: ignore

                exchange_info.append(data)

        return exchange_info

    def setup_exchange(
            self,
            name: str,
            connector: str,
            api_key: ApiKey,
            api_secret: ApiSecret | None,
            database: DBHandler,
            passphrase: str | None = None,
            kraken_account_type: KrakenAccountType | None = None,
            binance_history_start_ts: Timestamp | None = None,
            **kwargs: Any,
    ) -> tuple[ConnectionIdentifier | None, str]:
        """
        Setup a new exchange connection with an api key, an api secret and register it in
        both connected_exchanges and the DB. Returns the identifier of the new connection,
        or None and the reason it failed.

        For some exchanges there is more attributes to add
        """
        if connector not in SUPPORTED_EXCHANGES:  # also checked via marshmallow
            return None, f'Attempted to register unsupported exchange {name}'

        if self.get_exchange_by_name(connector=connector, name=name) is not None:
            return None, f'{connector!s} exchange {name} is already registered'

        exchange: ExchangeInterface = self.initialize_exchange(
            connector=connector,
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            database=database,
            **kwargs,
        )
        try:
            result, message = exchange.validate_api_key()
        except Exception as e:  # pylint: disable=broad-except
            result = False
            message = str(e)

        if not result:
            log.error(
                f'Failed to validate API key for {connector!s} exchange {name}'
                f' due to {message}',
            )
            return None, message

        with self.registry_lock:
            # re-check under the lock: a concurrent setup of the same exchange may
            # have registered it while this one validated the credentials remotely
            if self.get_exchange_by_name(connector=connector, name=name) is not None:
                return None, f'{connector!s} exchange {name} is already registered'
            # persist under the same lock as the registry append: delete_exchange
            # serializes on it too, so a concurrent delete cannot slip between the
            # two and leave orphaned credentials in the DB that would resurrect
            # the exchange on the next login. DB first, so that a failed write
            # registers nothing.
            exchange.connection_identifier = database.add_exchange(
                name=name,
                connector=ConnectorIdentifier(connector),
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                kraken_account_type=kraken_account_type,
                kraken_futures_api_key=kwargs.get('kraken_futures_api_key'),
                kraken_futures_api_secret=kwargs.get('kraken_futures_api_secret'),
                binance_selected_trade_pairs=kwargs.get('binance_selected_trade_pairs'),
                binance_history_start_ts=binance_history_start_ts,
                okx_location=kwargs.get('okx_location'),
                gate_location=kwargs.get('gate_location'),
            )
            if (
                    connector in (LOCATION_BINANCE, LOCATION_BINANCEUS) and
                    isinstance(exchange, ExchangeWithExtras)
            ):
                exchange.reset_to_db_extras()
            self.connected_exchanges[connector].append(exchange)
        return exchange.connection_identifier, ''

    def initialize_exchange(
            self,
            connector: str,
            name: str,
            api_key: ApiKey,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            database: DBHandler,
            **kwargs: Any,
    ) -> ExchangeInterface:
        """Create the exchange object of a connection. It gets the connection's identifier
        only once the connection is saved."""
        if passphrase is not None:
            kwargs['passphrase'] = passphrase
        elif connector == LOCATION_BINANCE:
            kwargs['uri'] = BINANCE_BASE_URL
        elif connector == LOCATION_BINANCEUS:
            kwargs['uri'] = BINANCEUS_BASE_URL

        params = {
            'name': name,
            'api_key': api_key,
            'database': database,
            'msg_aggregator': self.msg_aggregator,
            # remove all empty kwargs
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        if connector not in EXCHANGES_WITHOUT_API_SECRET:
            params['secret'] = api_secret

        return exchange_connector_class(connector)(**params)

    def initialize_exchanges(
            self,
            connections: list[IntegrationConnection],
            database: DBHandler,
    ) -> None:
        log.debug('Initializing exchanges')
        self.database = database
        for connection in connections:
            if connection.connector not in SUPPORTED_EXCHANGES:  # banks or a no longer supported exchange  # noqa: E501
                continue
            if self.get_exchange(connection.identifier) is not None:
                continue  # already initialized

            exchange_obj = self.initialize_exchange(
                connector=connection.connector,
                name=connection.name,
                api_key=connection.api_key,
                api_secret=connection.api_secret,
                passphrase=connection.passphrase,
                database=database,
                **database.get_exchange_credentials_extras(connection.identifier),
            )
            exchange_obj.connection_identifier = connection.identifier
            with self.registry_lock:
                self.connected_exchanges[connection.connector].append(exchange_obj)
        log.debug('Initialized exchanges')

    def get_user_binance_pairs(self, identifier: str) -> list[str]:
        if (exchange := self.get_exchange(identifier)) is not None:
            return self.database.get_binance_pairs(exchange.connection_identifier)
        return []

    def query_exchange_history_events(
            self,
            location: str | None,
            identifier: str | None,
    ) -> None:
        """Queries new history events of one exchange connection, or of every connection of
        the given exchange.

        May raise:
        - RemoteError if one or more exchange queries fail
        - InputError if the specified exchange's query input is invalid
        """
        with self.database.conn.read_ctx() as cursor:
            excluded = self.database.get_settings(cursor).non_syncing_exchanges
        exchanges_list = []
        if identifier is not None:
            if (exchange := self.get_exchange(identifier)) is None:
                log.error(
                    'Failed to query history events for unknown exchange connection '
                    f'{identifier}',
                )
                return
            exchanges_list.append(exchange)
        else:
            assert location is not None, 'the API asks for a connection or a location'
            if (exchanges := self.connected_exchanges.get(location)) is None:
                log.error(
                    'Unable to query history events with no connected exchanges '
                    f'for location: {location!s}',
                )
                return
            exchanges_list.extend(exchanges)

        errors: list[str] = []
        for exchange in exchanges_list:
            if exchange.connection_identifier in excluded:
                log.info(
                    'Skipping history events query for disabled syncing exchange. '
                    f'Location: {exchange.location!s}, Name: {exchange.name}',
                )
                continue
            try:
                exchange.query_history_events()
            except (InputError, RemoteError) as e:
                if identifier is not None and isinstance(e, InputError):
                    raise

                log.error(
                    'Failed to query history events for %s exchange %s due to %s',
                    exchange.location,
                    exchange.name,
                    e,
                )
                errors.append(f'{exchange.name}: {e!s}')

        if len(errors) != 0:
            raise RemoteError(
                f'Failed to query {location!s} history events for {", ".join(errors)}',
            )

    def requery_exchange_history_events(
            self,
            identifier: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> tuple[int, int, int, Timestamp]:
        """Query an exchange instance for certain range of time measured in seconds

        May raise:
            - InputError: if the exchange instance can't be found.
            - RemoteError: if the exchange's remote query fails.
            - DeserializationError
            - IntegrityError
        """
        if (exchange := self.get_exchange(identifier)) is None:
            raise InputError(f'Exchange connection {identifier} is not registered')
        with self.database.conn.read_ctx() as cursor:
            excluded = self.database.get_settings(cursor).non_syncing_exchanges
        if exchange.connection_identifier in excluded:
            raise InputError(f'Syncing for {exchange.location!s} exchange {exchange.name} is disabled')  # noqa: E501

        exchange.send_history_events_status_msg(
            step=HistoryEventsStep.QUERYING_EVENTS_STARTED,
        )
        exchange.send_history_events_status_msg(
            step=HistoryEventsStep.QUERYING_EVENTS_STATUS_UPDATE,
            period=[start_ts, end_ts],
        )
        event_queue = HistoryEventQueue(
            database=self.database,
            location_string=connection_range_name(exchange.connection_identifier, 'history_events'),  # noqa: E501
            query_start_ts=start_ts,
        )
        try:
            actual_end_ts = exchange.requery_online_history_events_into_queue(
                start_ts=start_ts,
                end_ts=end_ts,
                event_queue=event_queue,
            )
        finally:
            try:
                event_queue.flush()
            finally:
                exchange.send_history_events_status_msg(
                    step=HistoryEventsStep.QUERYING_EVENTS_FINISHED,
                )

        if (total_events := event_queue.queried_events) == 0:
            return 0, 0, 0, actual_end_ts

        skipped_events = total_events - event_queue.saved_events
        return total_events, event_queue.saved_events, skipped_events, actual_end_ts
