import logging
from collections import defaultdict
from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple

from rotkehlchen.constants.misc import BINANCE_BASE_URL, BINANCEUS_BASE_URL
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ApiKey, ApiSecret, ExchangeApiCredentials, Location
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Exchanges for which we have supported modules
SUPPORTED_EXCHANGES = [
    Location.KRAKEN,
    Location.POLONIEX,
    Location.BITTREX,
    Location.BITMEX,
    Location.BINANCE,
    Location.COINBASE,
    Location.COINBASEPRO,
    Location.GEMINI,
    Location.BITSTAMP,
    Location.BINANCEUS,
    Location.BITFINEX,
    Location.BITCOINDE,
    Location.ICONOMI,
    Location.KUCOIN,
    Location.FTX,
]
# Exchanges for which we allow import via CSV
EXTERNAL_EXCHANGES = [Location.CRYPTOCOM]
ALL_SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES + EXTERNAL_EXCHANGES


class ExchangeManager():

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        self.connected_exchanges: Dict[Location, List[ExchangeInterface]] = defaultdict(list)
        self.msg_aggregator = msg_aggregator

    @staticmethod
    def _get_exchange_module_name(location: Location) -> str:
        if location == Location.BINANCEUS:
            return str(Location.BINANCE)

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
        for _, exchanges in self.connected_exchanges.items():
            for exchange in exchanges:
                yield exchange

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

    def get_connected_exchange_names(self) -> List[Dict[str, Any]]:
        return [
            {"location": str(location), "name": e.name}
            for location, exchanges in self.connected_exchanges.items() for e in exchanges
        ]

    def setup_exchange(
            self,
            name: str,
            location: Location,
            api_key: ApiKey,
            api_secret: ApiSecret,
            database: 'DBHandler',
            passphrase: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Setup a new exchange with an api key, an api secret and for some exchanges a passphrase.

        """
        if location not in SUPPORTED_EXCHANGES:  # also checked via marshmallow
            return False, 'Attempted to register unsupported exchange {}'.format(name)

        if self.get_exchange(name=name, location=location) is not None:
            return False, f'{str(location)} exchange {name} is already registered'

        credentials_dict = {}
        api_credentials = ExchangeApiCredentials(
            name=name,
            location=location,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
        )
        credentials_dict[location] = [api_credentials]
        self.initialize_exchanges(credentials_dict, database)

        exchange = self.get_exchange(name=name, location=location)
        if exchange is None:
            return False, 'Should never happen. Exchange is None after initialization'
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
            self.delete_exchange(name=name, location=location)
            return False, message

        return True, ''

    def initialize_exchanges(
            self,
            exchange_credentials: Dict[Location, List[ExchangeApiCredentials]],
            database: 'DBHandler',
    ) -> None:
        log.debug('Initializing exchanges')
        # initialize exchanges for which we have keys and are not already initialized
        for location, credentials_list in exchange_credentials.items():
            module_name = self._get_exchange_module_name(location)
            try:
                module = import_module(f'rotkehlchen.exchanges.{module_name}')
            except ModuleNotFoundError:
                # This should never happen
                raise AssertionError(
                    f'Tried to initialize unknown exchange {str(location)}. Should not happen',
                ) from None

            for credentials in credentials_list:
                if self.get_exchange(name=credentials.name, location=credentials.location):
                    continue  # already initialized

                exchange_ctor = getattr(module, module_name.capitalize())
                extra_args: Dict[str, Any] = {}
                if credentials.passphrase is not None:
                    extra_args['passphrase'] = credentials.passphrase
                if location == Location.KRAKEN:
                    settings = database.get_settings()
                    extra_args['account_type'] = settings.kraken_account_type
                elif location == Location.BINANCE:
                    extra_args['uri'] = BINANCE_BASE_URL
                elif location == Location.BINANCEUS:
                    extra_args['uri'] = BINANCEUS_BASE_URL
                exchange_obj = exchange_ctor(
                    name=credentials.name,
                    api_key=credentials.api_key,
                    secret=credentials.api_secret,
                    database=database,
                    msg_aggregator=self.msg_aggregator,
                    **extra_args,
                )
                self.connected_exchanges[location].append(exchange_obj)
