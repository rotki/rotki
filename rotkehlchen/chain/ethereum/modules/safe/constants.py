from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SAFE: Final = 'safe'
SAFE_VESTING: Final = string_to_evm_address('0x96B71e2551915d98d22c448b040A3BC4801eA4ff')
CLAIMED_VESTING: Final = b'1\xb7\x188\x9b\x1e\xb9-\xf8:\xb0\x0c\x1aQ\x12\xe5\xbb\x8a\x02\xc7\xc1\xc9\xc0.\x1e<\x15\xad3\xe0S&'  # noqa: E501
