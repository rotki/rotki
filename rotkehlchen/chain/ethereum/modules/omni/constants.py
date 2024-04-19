from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CLAIM: Final = b'\xd8\x13\x8f\x8a?7|RY\xcaT\x8ep\xe4\xc2\xde\x94\xf1)\xf5\xa1\x106\xa1[iQ<\xba+Bj'
OMNI_AIDROP_CONTRACT = string_to_evm_address('0xD0c155595929FD6bE034c3848C00DAeBC6D330F6')
OMNI_TOKEN_ID: str = 'eip155:1/erc20:0x36E66fbBce51e4cD5bd3C62B637Eb411b18949D4'
CPT_OMNI: Final = 'omni'
