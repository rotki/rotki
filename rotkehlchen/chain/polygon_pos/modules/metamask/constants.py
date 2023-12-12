from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


METAMASK_ROUTER: Final = string_to_evm_address('0x1a1ec25DC08e98e5E93F1104B5e5cdD298707d31')
METAMASK_FEE_RECEIVER_ADDRESS: Final = string_to_evm_address(
    '0x930DEDdDB92Fef1B4Ab2665D250877339f064eac',
)
