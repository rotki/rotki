import logging
from collections import defaultdict
from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

from rotkehlchen.db.constants import KRAKEN_ACCOUNT_TYPE_KEY
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.binance import BINANCE_BASE_URL, BINANCEUS_BASE_URL
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.ftx import FTX_BASE_URL, FTXUS_BASE_URL
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    EXTERNAL_EXCHANGES,
    ApiKey,
    ApiSecret,
    ExchangeApiCredentials,
    Location,
)
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.kraken import KrakenAccountType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Exchanges for which we have supported modules
SUPPORTED_EXCHANGES = [
    Location.BINANCE,
    Location.BINANCEUS,
    Location.BITCOINDE,
    Location.BITFINEX,
    Location.BITMEX,
    Location.BITPANDA,
    Location.BITSTAMP,
    Location.BITTREX,
    Location.COINBASE,
    Location.COINBASEPRO,
    Location.GEMINI,
    Location.ICONOMI,
    Location.KRAKEN,
    Location.KUCOIN,
    Location.FTX,
    Location.FTXUS,
    Location.INDEPENDENTRESERVE,
    Location.POLONIEX,
]
EXCHANGES_WITH_PASSPHRASE = (Location.COINBASEPRO, Location.KUCOIN)
# Exchanges for which we allow import via CSV
ALL_SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES + EXTERNAL_EXCHANGES


class ExchangeManager():

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.connected_exchanges: Dict[Location, List[ExchangeInterface]] = defaultdict(list)
        self.msg_aggregator = msg_aggregator

    @staticmethod
    def _get_exchange_module_name(location: Location) -> str:
        if location == Location.BINANCEUS:
            return str(Location.BINANCE)
        if location == Location.FTXUS:
            return str(Location.FTX)

        return str(location)

    def get_exchange(self, name: str, location: Location) -> Optional[ExchangeInterface]:
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
        """Iterate all connected exchanges"""
        with self.database.conn.read_ctx() as cursor:
            excluded = self.database.get_settings(cursor).non_syncing_exchanges
        for _, exchanges in self.connected_exchanges.items():
            for exchange in exchanges:
                # We are not yielding excluded exchanges
                if exchange.location_id() not in excluded:
                    yield exchange

    def edit_exchange(
            self,
            name: str,
            location: Location,
            new_name: Optional[str],
            api_key: Optional[ApiKey],
            api_secret: Optional[ApiSecret],
            passphrase: Optional[str],
            kraken_account_type: Optional['KrakenAccountType'],
            binance_selected_trade_pairs: Optional[List[str]],
            ftx_subaccount: Optional[str],
    ) -> Tuple[bool, str]:
        """Edits both the exchange object and the database entry

        Returns True if an entry was found and edited and false otherwise

        May raise:
        - InputError if there is an error updating the DB
        """
        exchangeobj = self.get_exchange(name=name, location=location)
        if not exchangeobj:
            return False, f'Could not find {str(location)} exchange {name} for editing'

        # First edit the database entries. This may raise InputError
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
                ftx_subaccount=ftx_subaccount,
            )

            # Edit the exchange object
            success, msg = exchangeobj.edit_exchange(
                name=new_name,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                kraken_account_type=kraken_account_type,
                binance_selected_trade_pairs=binance_selected_trade_pairs,
                ftx_subaccount=ftx_subaccount,
            )
            if success is False:
                # by raising we also rollback the DB writes due to user_write()
                raise InputError(msg)

            return True, ''

    def delete_exchange(self, name: str, location: Location) -> None:
        """Deletes exchange only from the manager. Not from the DB"""
        exchanges_list = self.connected_exchanges.get(location)
        if exchanges_list is None:
            return

        if len(exchanges_list) == 1:
            self.connected_exchanges.pop(location)
            return

        self.connected_exchanges[location] = [x for x in exchanges_list if x.name != name]

    def delete_all_exchanges(self) -> None:
        self.connected_exchanges.clear()

    def get_connected_exchanges_info(self) -> List[Dict[str, Any]]:
        exchange_info = []
        for location, exchanges in self.connected_exchanges.items():
            for exchangeobj in exchanges:
                data = {"location": str(location), "name": exchangeobj.name}
                if location == Location.KRAKEN:  # ignore type since we know this is kraken here
                    data[KRAKEN_ACCOUNT_TYPE_KEY] = str(exchangeobj.account_type)  # type: ignore
                if location == Location.FTX:
                    subaccount = exchangeobj.subaccount  # type: ignore
                    if subaccount is not None:
                        data['ftx_subaccount'] = subaccount
                exchange_info.append(data)

        return exchange_info

    def _get_exchange_module(self, location: Location) -> ModuleType:
        module_name = self._get_exchange_module_name(location)
        try:
            module = import_module(f'rotkehlchen.exchanges.{module_name}')
        except ModuleNotFoundError:
            # This should never happen
            raise AssertionError(
                f'Tried to initialize unknown exchange {str(location)}. Should not happen',
            ) from None

        return module

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            database: 'DBHandler',
            passphrase: Optional[str] = None,
            **kwargs: Any,
    ) -> Tuple[bool, str]:
        """
        Setup a new exchange with an api key, an api secret.

        For some exchanges there is more attributes to add
        """
        if location not in SUPPORTED_EXCHANGES:  # also checked via marshmallow
            return False, 'Attempted to register unsupported exchange {}'.format(name)

        if self.get_exchange(name=name, location=location) is not None:
            return False, f'{str(location)} exchange {name} is already registered'

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
                f'Failed to validate API key for {str(location)} exchange {name}'
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
        elif credentials.location == Location.FTX:
            kwargs['uri'] = FTX_BASE_URL
        elif credentials.location == Location.FTXUS:
            kwargs['uri'] = FTXUS_BASE_URL

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
            exchange_credentials: Dict[Location, List[ExchangeApiCredentials]],
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

    def get_user_binance_pairs(self, name: str, location: Location) -> List[str]:
        is_connected = location in self.connected_exchanges
        if is_connected:
            return self.database.get_binance_pairs(name, location)
        return []
