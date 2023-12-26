from rotkehlchen.types import EXTERNAL_EXCHANGES, Location

EXCHANGES_WITH_PASSPHRASE = (Location.COINBASEPRO, Location.KUCOIN, Location.OKX)
EXCHANGES_WITHOUT_API_SECRET = (Location.BITPANDA,)

# Exchanges for which we have supported modules
SUPPORTED_EXCHANGES = EXCHANGES_WITH_PASSPHRASE + EXCHANGES_WITHOUT_API_SECRET + (
    Location.BINANCE,
    Location.BINANCEUS,
    Location.BITCOINDE,
    Location.BITFINEX,
    Location.BITMEX,
    Location.BITSTAMP,
    Location.COINBASE,
    Location.GEMINI,
    Location.ICONOMI,
    Location.KRAKEN,
    Location.INDEPENDENTRESERVE,
    Location.POLONIEX,
    Location.WOO,
)

DEAD_EXCHANGES = (Location.FTX, Location.FTXUS, Location.BITTREX)
# Exchanges for which we allow import via CSV
ALL_SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES + EXTERNAL_EXCHANGES + DEAD_EXCHANGES
