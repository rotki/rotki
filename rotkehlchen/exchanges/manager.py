import logging
from collections import defaultdict
from collections.abc import Iterator
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.db.constants import BINANCE_MARKETS_KEY, KRAKEN_ACCOUNT_TYPE_KEY
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.binance import BINANCE_BASE_URL, BINANCEUS_BASE_URL
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeWithExtras
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    ExchangeApiCredentials,
    ExchangeAuthCredentials,
    Location,
)
from rotkehlchen.user_messages import MessagesAggregator

from .constants import SUPPORTED_EXCHANGES

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ExchangeManager:

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.connected_exchanges: dict[Location, list[ExchangeInterface]] = defaultdict(list)
        self.msg_aggregator = msg_aggregator

    @staticmethod
    def _get_exchange_module_name(location: Location) -> str:
        if location == Location.BINANCEUS:
            return str(Location.BINANCE)

        return str(location)

    def connected_and_syncing_exchanges_num(self) -> int:
        return len(list(self.iterate_exchanges()))

    def get_exchange(self, name: str, location: Location) -> ExchangeInterface | None:
        """Get the exchange object for an exchange with a given name and location

        Returns None if it can not be found
        """
        exchanges_list = self.connected_exchanges.get(location)
        if exchanges_list is None:
            return None

        for exchange in exchanges_list:
            if exchange.name == name:
                return exchange

        return None

    def iterate_exchanges(self) -> Iterator[ExchangeInterface]:
        """Iterate all connected and syncing exchanges"""
        with self.database.conn.read_ctx() as cursor:
            excluded = self.database.get_settings(cursor).non_syncing_exchanges
        for exchanges in self.connected_exchanges.values():
            for exchange in exchanges:
                # We are not yielding excluded exchanges
                if exchange.location_id() not in excluded:
                    yield exchange

    def edit_exchange(
            self,
            name: str,
            location: Location,
            new_name: str | None,
            api_key: ApiKey | None,
            api_secret: ApiSecret | None,
            passphrase: str | None,
            kraken_account_type: Optional['KrakenAccountType'],
            binance_selected_trade_pairs: list[str] | None,
    ) -> tuple[bool, str]:
        """Edits both the exchange object and the database entry

        Returns True if an entry was found and edited and false otherwise
        """
        exchangeobj = self.get_exchange(name=name, location=location)
        if not exchangeobj:
            return False, f'Could not find {location!s} exchange {name} for editing'

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
                BINANCE_MARKETS_KEY: binance_selected_trade_pairs,
            })
            if success is False:
                exchangeobj.reset_to_db_credentials()
                return False, f'Failed to edit exchange extras. {msg}'

        try:
            with self.database.user_write() as cursor:
                self.database.edit_exchange(
                    cursor,
                    name=name,
                    location=location,
                    new_name=new_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                    kraken_account_type=kraken_account_type,
                    binance_selected_trade_pairs=binance_selected_trade_pairs,
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

    def delete_exchange(self, name: str, location: Location) -> tuple[bool, str]:
        """
        Deletes an exchange with the specified name + location from both connected_exchanges
        and the DB.
        """
        if self.get_exchange(name=name, location=location) is None:
            return False, f'{location!s} exchange {name} is not registered'

        exchanges_list = self.connected_exchanges.get(location)
        if exchanges_list is None:
            return False, f'{location!s} exchange {name} is not registered'

        if len(exchanges_list) == 1:  # if is last exchange of this location
            self.connected_exchanges.pop(location)
        else:
            self.connected_exchanges[location] = [x for x in exchanges_list if x.name != name]
        with self.database.user_write() as write_cursor:  # Also remove it from the db
            self.database.remove_exchange(write_cursor=write_cursor, name=name, location=location)
            self.database.delete_used_query_range_for_exchange(
                write_cursor=write_cursor,
                location=location,
                exchange_name=name,
            )
        return True, ''

    def delete_all_exchanges(self) -> None:
        """Deletes all exchanges from the manager. Not from the DB"""
        self.connected_exchanges.clear()

    def get_connected_exchanges_info(self) -> list[dict[str, Any]]:
        exchange_info = []
        for location, exchanges in self.connected_exchanges.items():
            for exchangeobj in exchanges:
                data = {'location': str(location), 'name': exchangeobj.name}
                if location == Location.KRAKEN:  # ignore type since we know this is kraken here
                    data[KRAKEN_ACCOUNT_TYPE_KEY] = str(exchangeobj.account_type)  # type: ignore
                exchange_info.append(data)

        return exchange_info

    def _get_exchange_module(self, location: Location) -> ModuleType:
        module_name = self._get_exchange_module_name(location)
        try:
            module = import_module(f'rotkehlchen.exchanges.{module_name}')
        except ModuleNotFoundError:
            # This should never happen
            raise AssertionError(
                f'Tried to initialize unknown exchange {location!s}. Should not happen',
            ) from None

        return module

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            database: 'DBHandler',
            passphrase: str | None = None,
            **kwargs: Any,
    ) -> tuple[bool, str]:
        """
        Setup a new exchange with an api key, an api secret.

        For some exchanges there is more attributes to add
        """
        if location not in SUPPORTED_EXCHANGES:  # also checked via marshmallow
            return False, f'Attempted to register unsupported exchange {name}'

        if self.get_exchange(name=name, location=location) is not None:
            return False, f'{location!s} exchange {name} is already registered'

        api_credentials = ExchangeApiCredentials(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        exchange = self.initialize_exchange(
            module=self._get_exchange_module(location),
            credentials=api_credentials,
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
                f'Failed to validate API key for {location!s} exchange {name}'
                f' due to {message}',
            )
            return False, message

        self.connected_exchanges[location].append(exchange)
        return True, ''

    def initialize_exchange(
            self,
            module: ModuleType,
            credentials: ExchangeApiCredentials,
            database: 'DBHandler',
            **kwargs: Any,
    ) -> ExchangeInterface:
        maybe_exchange = self.get_exchange(name=credentials.name, location=credentials.location)
        if maybe_exchange:
            return maybe_exchange  # already initialized

        module_name = module.__name__.split('.')[-1]
        exchange_ctor = getattr(module, module_name.capitalize())
        if credentials.passphrase is not None:
            kwargs['passphrase'] = credentials.passphrase
        elif credentials.location == Location.BINANCE:
            kwargs['uri'] = BINANCE_BASE_URL
        elif credentials.location == Location.BINANCEUS:
            kwargs['uri'] = BINANCEUS_BASE_URL

        exchange_obj = exchange_ctor(
            name=credentials.name,
            api_key=credentials.api_key,
            secret=credentials.api_secret,
            database=database,
            msg_aggregator=self.msg_aggregator,
            # remove all empty kwargs
            **{k: v for k, v in kwargs.items() if v is not None},
        )
        return exchange_obj

    def initialize_exchanges(
            self,
            exchange_credentials: dict[Location, list[ExchangeApiCredentials]],
            database: 'DBHandler',
    ) -> None:
        log.debug('Initializing exchanges')
        self.database = database
        # initialize exchanges for which we have keys and are not already initialized
        for location, credentials_list in exchange_credentials.items():
            module = self._get_exchange_module(location)
            for credentials in credentials_list:
                extras = database.get_exchange_credentials_extras(
                    name=credentials.name,
                    location=credentials.location,
                )
                exchange_obj = self.initialize_exchange(
                    module=module,
                    credentials=credentials,
                    database=database,
                    **extras,
                )
                self.connected_exchanges[location].append(exchange_obj)
        log.debug('Initialized exchanges')

    def get_user_binance_pairs(self, name: str, location: Location) -> list[str]:
        is_connected = location in self.connected_exchanges
        if is_connected:
            return self.database.get_binance_pairs(name, location)
        return []

    def query_history_events(self) -> None:
        """Queries all history events for exchanges that need it

        May raise:
        - RemoteError if any exchange's remote query fails
        """
        for exchange in self.iterate_exchanges():
            exchange.query_history_events()
