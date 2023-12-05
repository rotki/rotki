from rotkehlchen.types import EXTERNAL_EXCHANGES, Location

# Exchanges for which we have supported modules
SUPPORTED_EXCHANGES = (
    Location.BINANCE,
    Location.BINANCEUS,
    Location.BITCOINDE,
    Location.BITFINEX,
    Location.BITMEX,
    Location.BITPANDA,
    Location.BITSTAMP,
    Location.COINBASE,
    Location.COINBASEPRO,
    Location.GEMINI,
    Location.ICONOMI,
    Location.KRAKEN,
    Location.KUCOIN,
    Location.INDEPENDENTRESERVE,
    Location.POLONIEX,
    Location.OKX,
    Location.WOO,
    Location.BYBIT,
)
EXCHANGES_WITH_PASSPHRASE = (Location.COINBASEPRO, Location.KUCOIN, Location.OKX)
DEAD_EXCHANGES = (Location.FTX, Location.FTXUS, Location.BITTREX)
# Exchanges for which we allow import via CSV
ALL_SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES + EXTERNAL_EXCHANGES + DEAD_EXCHANGES
