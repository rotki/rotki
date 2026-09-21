from typing import TYPE_CHECKING, Any

from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BINANCEUS,
    LOCATION_BIT2ME,
    LOCATION_BITCOINDE,
    LOCATION_BITFINEX,
    LOCATION_BITMEX,
    LOCATION_BITPANDA,
    LOCATION_BITSTAMP,
    LOCATION_BITTREX,
    LOCATION_BYBIT,
    LOCATION_COINBASE,
    LOCATION_COINBASEPRIME,
    LOCATION_COINBASEPRO,
    LOCATION_COINEX,
    LOCATION_CRYPTOCOM,
    LOCATION_FTX,
    LOCATION_FTXUS,
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
from rotkehlchen.locations.types import LocationIdentifier
from rotkehlchen.types import EXTERNAL_EXCHANGES

if TYPE_CHECKING:
    from rotkehlchen.connections.types import ConnectorIdentifier

EXCHANGES_WITH_PASSPHRASE = (LOCATION_KUCOIN, LOCATION_OKX, LOCATION_COINBASEPRIME)
EXCHANGES_WITHOUT_API_SECRET = (LOCATION_BITPANDA,)

# Exchanges for which we have supported modules
SUPPORTED_EXCHANGES = EXCHANGES_WITH_PASSPHRASE + EXCHANGES_WITHOUT_API_SECRET + (
    LOCATION_BINANCE,
    LOCATION_BINANCEUS,
    LOCATION_BIT2ME,
    LOCATION_BITCOINDE,
    LOCATION_BITFINEX,
    LOCATION_BITMEX,
    LOCATION_BITSTAMP,
    LOCATION_COINBASE,
    LOCATION_CRYPTOCOM,
    LOCATION_GEMINI,
    LOCATION_ICONOMI,
    LOCATION_KRAKEN,
    LOCATION_INDEPENDENTRESERVE,
    LOCATION_POLONIEX,
    LOCATION_WOO,
    LOCATION_BYBIT,
    LOCATION_HTX,
    LOCATION_GATE,
    LOCATION_COINEX,
)

EXPERIMENTAL_EXCHANGES = (LOCATION_CRYPTOCOM,)

DEAD_EXCHANGES = (LOCATION_FTX, LOCATION_FTXUS, LOCATION_BITTREX, LOCATION_COINBASEPRO)
# Exchanges for which we allow import via CSV
ALL_SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES + EXTERNAL_EXCHANGES + DEAD_EXCHANGES


def exchange_location(connector: ConnectorIdentifier | LocationIdentifier) -> LocationIdentifier:
    """The location an exchange connector's connections put their data in. Every exchange
    connector reads its own exchange, whose location is spelled like the connector."""
    return LocationIdentifier(connector)


def serialize_exchange_connectors() -> list[dict[str, Any]]:
    """What the setup of each supported exchange connector needs"""
    return [{
        'connector': connector,
        'location': exchange_location(connector),
        'is_exchange_with_passphrase': connector in EXCHANGES_WITH_PASSPHRASE,
        'is_exchange_without_api_secret': connector in EXCHANGES_WITHOUT_API_SECRET,
        'experimental': connector in EXPERIMENTAL_EXCHANGES,
    } for connector in SUPPORTED_EXCHANGES]
