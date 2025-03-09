from enum import auto

from rotkehlchen.types import OracleSource


class CurrentPriceOracle(OracleSource):
    """Supported oracles for querying current prices"""
    COINGECKO = auto()
    CRYPTOCOMPARE = auto()
    UNISWAPV2 = auto()
    UNISWAPV3 = auto()
    MANUALCURRENT = auto()
    BLOCKCHAIN = auto()
    FIAT = auto()
    DEFILLAMA = auto()
    ALCHEMY = auto()
    YAHOOFINANCE = auto()


DEFAULT_CURRENT_PRICE_ORACLES_ORDER = (
    CurrentPriceOracle.COINGECKO,
    CurrentPriceOracle.DEFILLAMA,
    CurrentPriceOracle.CRYPTOCOMPARE,
    CurrentPriceOracle.YAHOOFINANCE,
    CurrentPriceOracle.UNISWAPV2,
    CurrentPriceOracle.UNISWAPV3,
)

SETTABLE_CURRENT_PRICE_ORACLES = {  # only these oracles should be configurable and settable via the api  # noqa: E501
    CurrentPriceOracle.COINGECKO,
    CurrentPriceOracle.DEFILLAMA,
    CurrentPriceOracle.CRYPTOCOMPARE,
    CurrentPriceOracle.ALCHEMY,
    CurrentPriceOracle.YAHOOFINANCE,
    CurrentPriceOracle.UNISWAPV2,
    CurrentPriceOracle.UNISWAPV3,
}
