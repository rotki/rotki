from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_FARCASTER: Final = 'farcaster'
BASE_USDC: Final = string_to_evm_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
FARCASTER_PRO: Final = string_to_evm_address('0x00000000fc84484d585C3cF48d213424DFDE43FD')
PURCHASED_TIER_TOPIC: Final = b'y5D\xf1\xee\xbc\xd8\x0e\xaa$\xd7\xc6\xe3+pt\x88\xda\xf40=\x0e\xc34\x9b4\xea\x9d\x0522\x85'  # noqa: E501

FARCASTER_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_FARCASTER,
    label='Farcaster',
    image='farcaster.png',
)
