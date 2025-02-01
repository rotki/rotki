from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

PARASWAP_AUGUSTUS_ROUTER: Final = string_to_evm_address(
    '0x59C7C832e96D2568bea6db468C1aAdcbbDa08A52',
)
PARASWAP_FEE_CLAIMER: Final = string_to_evm_address('0x9aaB4B24541af30fD72784ED98D8756ac0eFb3C7')
