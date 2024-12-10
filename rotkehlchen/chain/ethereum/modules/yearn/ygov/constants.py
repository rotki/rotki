from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

YGOV_ADDRESS: Final = string_to_evm_address('0x0001FB050Fe7312791bF6475b96569D83F695C9f')
REWARD_PAID_TOPIC: Final = b'\xe2@6@\xbah\xfe\xd3\xa2\xf8\x8buWU\x1d\x19\x93\xf8K\x99\xbb\x10\xff\x83?\x0c\xf8\xdb\x0c^\x04\x86'  # noqa: E501
