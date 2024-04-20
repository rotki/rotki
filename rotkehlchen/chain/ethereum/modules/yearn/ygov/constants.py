from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

YGOV_ADDRESS: Final = string_to_evm_address('0x0001FB050Fe7312791bF6475b96569D83F695C9f')
WITHDRAWN_TOPIC: Final = b'p\x84\xf5Gf\x18\xd8\xe6\x0b\x11\xef\r}?\x06\x91FU\xad\xb8y>(\xff\x7f\x01\x8dLv\xd5\x05\xd5'  # noqa: E501
REWARD_PAID_TOPIC: Final = b'\xe2@6@\xbah\xfe\xd3\xa2\xf8\x8buWU\x1d\x19\x93\xf8K\x99\xbb\x10\xff\x83?\x0c\xf8\xdb\x0c^\x04\x86'  # noqa: E501
