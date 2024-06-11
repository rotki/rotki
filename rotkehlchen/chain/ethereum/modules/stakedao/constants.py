from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_STAKEDAO: Final = 'stakedao'

STAKEDAO_CLAIMER1: Final = string_to_evm_address('0x0000000BE1d98523B5469AfF51A1e7b4891c6225')
STAKEDAO_CLAIMER2: Final = string_to_evm_address('0x0000000895cB182E6f983eb4D8b4E0Aa0B31Ae4c')
STAKEDAO_CLAIMER_OLD: Final = string_to_evm_address('0x9f8386001D2245F3052725Dd29da68D268B7F4bB')


CLAIMED_WITH_BOUNTY: Final = b'o\x9c\x98&\xbeYv\xf3\xf8*4\x90\xc5*\x832\x8c\xe2\xec{\xe9\xe6-\xcb9\xc2m\xa5\x14\x8d|v'  # noqa: E501
CLAIMED_WITH_BRIBE: Final = b'\xd7\x95\x91St\x02K\xe1\xf02\x04\xe0R\xbdXK3\xbb\x85\xc9\x12\x8e\xde\x9cT\xad\xbe\x0b\xbd\xc2 \x95'  # noqa: E501
