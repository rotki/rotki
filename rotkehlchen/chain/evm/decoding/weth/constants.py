from typing import Final

from rotkehlchen.constants.assets import A_WETH, A_WETH_ARB, A_WETH_BASE, A_WETH_OPT, A_WETH_SCROLL
from rotkehlchen.types import ChainID

CPT_WETH: Final = 'weth'
CHAINS_WITHOUT_NATIVE_ETH: Final = {ChainID.GNOSIS, ChainID.POLYGON_POS, ChainID.BINANCE_SC}
CHAINS_WITH_SPECIAL_WETH: Final = {ChainID.SCROLL, ChainID.ARBITRUM_ONE}
CHAIN_ID_TO_WETH_MAPPING: Final = {
    ChainID.ETHEREUM: A_WETH,
    ChainID.ARBITRUM_ONE: A_WETH_ARB,
    ChainID.OPTIMISM: A_WETH_OPT,
    ChainID.SCROLL: A_WETH_SCROLL,
    ChainID.BASE: A_WETH_BASE,
}
