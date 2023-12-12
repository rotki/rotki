from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


METAMASK_ROUTER: Final = string_to_evm_address('0x881D40237659C251811CEC9c364ef91dC08D300C')
METAMASK_FEE_RECEIVER_ADDRESS: Final = string_to_evm_address(
    '0x2aCf35C9A3F4c5C3F4c78EF5Fb64c3EE82f07c45',
)
