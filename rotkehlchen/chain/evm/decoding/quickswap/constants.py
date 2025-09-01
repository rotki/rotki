from typing import Final

from rotkehlchen.chain.evm.decoding.uniswap.constants import (
    CPT_UNISWAP_V2,
    CPT_UNISWAP_V3,
)

CPT_QUICKSWAP_V2: Final = 'quickswap-v2'
CPT_QUICKSWAP_V3: Final = 'quickswap-v3'
CPT_QUICKSWAP_V4: Final = 'quickswap-v4'

UNISWAP_QUICKSWAP_COUNTERPARTY_MAP: Final = {
    CPT_UNISWAP_V2: CPT_QUICKSWAP_V2,
    CPT_UNISWAP_V3: CPT_QUICKSWAP_V3,
}  # Used to update quickswap events that were initially decoded by the uniswap decoder.
