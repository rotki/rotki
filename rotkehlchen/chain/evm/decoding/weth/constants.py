import typing
from typing import Final

from rotkehlchen.constants.assets import A_WETH, A_WETH_ARB, A_WETH_BASE, A_WETH_OPT, A_WETH_SCROLL
from rotkehlchen.types import SUPPORTED_CHAIN_IDS, ChainID

CPT_WETH: Final = 'weth'
CHAINS_WITHOUT_NATIVE_ETH: Final = {ChainID.GNOSIS, ChainID.POLYGON_POS}
CHAIN_ID_TO_WETH_MAPPING: Final = {
    # A mapping from chain id to WETH asset for every supported evm chain except Gnosis
    ChainID.ETHEREUM: A_WETH,
    ChainID.ARBITRUM_ONE: A_WETH_ARB,
    ChainID.OPTIMISM: A_WETH_OPT,
    ChainID.SCROLL: A_WETH_SCROLL,
    ChainID.BASE: A_WETH_BASE,
}

# Make sure the CHAIN_ID_TO_WETH_MAPPING has all supported EVM chains with native ETH
assert (
    set(CHAIN_ID_TO_WETH_MAPPING.keys()) ==
    set(typing.get_args(SUPPORTED_CHAIN_IDS)) - CHAINS_WITHOUT_NATIVE_ETH
)
