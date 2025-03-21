from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_RAINBOW_SWAPS: Final = 'rainbow_swaps'

# The Rainbow router contract address is hardcoded in the Rainbow decoder class.
# If the address changes for a different chain, it needs to be updated accordingly.
RAINBOW_ROUTER_CONTRACT: Final = string_to_evm_address('0x00000000009726632680FB29d3F7A9734E3010E2')  # noqa: E501

# The chains on which the Rainbow router is deployed:
# https://github.com/rainbow-me/swaps/tree/main/smart-contracts#deployment-addresses
RAINBOW_SUPPORTED_CHAINS: Final = {
    ChainID.ARBITRUM_ONE,
    ChainID.BASE,
    ChainID.BINANCE_SC,
    ChainID.ETHEREUM,
    ChainID.OPTIMISM,
    ChainID.POLYGON_POS,
}
