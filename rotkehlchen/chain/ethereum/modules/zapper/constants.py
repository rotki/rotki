from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_ZAPPER: Final = 'zapper'
ZAPPER_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_ZAPPER,
    label='Zapper',
    image='zapper.png',
)

# Legacy Zapper.fi multi-exchange swap router contract (no longer in use).
ZAPPER_SWAP_CONTRACT: Final = string_to_evm_address('0xacDF47C844Eff0Ecb218D8945e28A9A484aF8D07')
