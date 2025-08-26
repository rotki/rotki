from typing import Final

from rotkehlchen.chain.evm.decoding.uniswap.v2.constants import UNISWAP_V2_SWAP_SIGNATURE
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import (
    SWAP_SIGNATURE as UNISWAP_V3_SWAP_SIGNATURE,
)

CPT_UNISWAP_V1: Final = 'uniswap-v1'
CPT_UNISWAP_V2: Final = 'uniswap-v2'
CPT_UNISWAP_V3: Final = 'uniswap-v3'
CPT_UNISWAP_V4: Final = 'uniswap-v4'
UNISWAP_LABEL: Final = 'Uniswap'
UNISWAP_ICON: Final = 'uniswap.svg'
UNISWAP_SIGNATURES: Final = (
    UNISWAP_V2_SWAP_SIGNATURE,
    UNISWAP_V3_SWAP_SIGNATURE,
)
