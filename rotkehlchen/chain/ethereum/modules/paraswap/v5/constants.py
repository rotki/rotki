from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

PARASWAP_AUGUSTUS_ROUTER: Final = string_to_evm_address(
    '0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57',
)
PARASWAP_FEE_CLAIMER: Final = string_to_evm_address(
    '0xeF13101C5bbD737cFb2bF00Bbd38c626AD6952F7',
)
