from rotkehlchen.chain.ethereum.modules.sushiswap.constants import CPT_SUSHISWAP_V2
from rotkehlchen.chain.ethereum.modules.uniswap.constants import (
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


AMM_ASSETS_SYMBOLS = {
    CPT_UNISWAP_V2: 'UNI-V2',
    CPT_SUSHISWAP_V2: 'SLP',
}
