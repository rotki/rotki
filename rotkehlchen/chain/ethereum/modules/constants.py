from typing import Final

from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.evm.decoding.uniswap.constants import (
    CPT_UNISWAP_V1,
    CPT_UNISWAP_V2,
    CPT_UNISWAP_V3,
)

AMM_POSSIBLE_COUNTERPARTIES = {
    CPT_UNISWAP_V1,
    CPT_UNISWAP_V2,
    CPT_UNISWAP_V3,
    CPT_SUSHISWAP_V2,
}

SUSHISWAP_LP_SYMBOL: Final = 'SLP'
UNISWAP_V2_LP_SYMBOL: Final = 'UNI-V2'
AMM_ASSETS_SYMBOLS: Final[dict[str, str]] = {
    CPT_UNISWAP_V2: UNISWAP_V2_LP_SYMBOL,
    CPT_SUSHISWAP_V2: SUSHISWAP_LP_SYMBOL,
}
