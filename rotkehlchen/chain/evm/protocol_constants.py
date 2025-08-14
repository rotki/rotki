from typing import Final, Literal

from rotkehlchen.chain.ethereum.modules.yearn.constants import CPT_YEARN_V2
from rotkehlchen.chain.evm.decoding.beefy_finance.constants import CPT_BEEFY_FINANCE
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.decoding.pendle.constants import CPT_PENDLE
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME

# NOTE: these constants are kept separate from evm/constants.py to avoid circular imports.
# The protocols for which we know how to calculate their prices
EVM_PROTOCOLS_WITH_PRICE_LOGIC: Final = (
    CPT_UNISWAP_V2,
    CPT_YEARN_V2,
    CPT_CURVE,
    CPT_VELODROME,
    CPT_AERODROME,
    CPT_HOP,
    CPT_PENDLE,
    CPT_UNISWAP_V3,
    CPT_BEEFY_FINANCE,
)

LP_TOKEN_AS_POOL_PROTOCOLS: Final = (  # In these protocols the LP token of a pool and the pool itself are the same contract  # noqa: E501
    CPT_UNISWAP_V2,
    CPT_VELODROME,
    CPT_AERODROME,
)

LP_TOKEN_AS_POOL_CONTRACT_ABIS = Literal['VELO_V2_LP', 'UNISWAP_V2_LP']  # These contract are both the pool and the LP token of the pool  # noqa: E501
