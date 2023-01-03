from rotkehlchen.types import EXTERNAL_EXCHANGES, Location

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
    Location.OKX,
]
EXCHANGES_WITH_PASSPHRASE = (Location.COINBASEPRO, Location.KUCOIN, Location.OKX)
# Exchanges for which we allow import via CSV
ALL_SUPPORTED_EXCHANGES = SUPPORTED_EXCHANGES + EXTERNAL_EXCHANGES
