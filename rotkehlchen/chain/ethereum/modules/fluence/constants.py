from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CLAIMED: Final = b'\x04g R\xdc\xb6\xb5\xb1\x9a\x9c\xc2\xec\x1b\x8fD\x7f\x1f^G\xb5\xe2L\xfa^O\xfbd\rc\xca+\xe7'  # noqa: E501
DEV_REWARD_DISTRIBUTOR: Final = string_to_evm_address('0x6081d7F04a8c31e929f25152d4ad37c83638C62b')
CPT_FLUENCE: Final = 'fluence'
