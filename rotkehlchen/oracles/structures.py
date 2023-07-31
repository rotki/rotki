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


DEFAULT_CURRENT_PRICE_ORACLES_ORDER = (
    CurrentPriceOracle.MANUALCURRENT,
    CurrentPriceOracle.COINGECKO,
    CurrentPriceOracle.DEFILLAMA,
    CurrentPriceOracle.CRYPTOCOMPARE,
    CurrentPriceOracle.UNISWAPV2,
    CurrentPriceOracle.UNISWAPV3,
)
