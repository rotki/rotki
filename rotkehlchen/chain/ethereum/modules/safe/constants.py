from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SAFE: Final = 'safe'
SAFE_VESTING: Final = string_to_evm_address('0x96B71e2551915d98d22c448b040A3BC4801eA4ff')
SAFEPASS_AIRDROP: Final = string_to_evm_address('0x57eC1930f3E5c8062926c2F3ee49316E116143df')
SAFE_LOCKING: Final = string_to_evm_address('0x0a7CB434f96f65972D46A5c1A64a9654dC9959b2')
CLAIMED_VESTING: Final = b'1\xb7\x188\x9b\x1e\xb9-\xf8:\xb0\x0c\x1aQ\x12\xe5\xbb\x8a\x02\xc7\xc1\xc9\xc0.\x1e<\x15\xad3\xe0S&'  # noqa: E501
LOCKED: Final = b'\xe8~\xf8M\x87\x01!\xe4\x90Q\xdd\xa6\xf8\xd2\x97q<\xb0\n\x0c\x07,\rw\x1fx\xea6\x88\x15\x00\x9f'  # noqa: E501
UNLOCKED: Final = b'\x1b\xd2\xaa\xc5\xb8\xfb\xf8\xaa\xccK\x88\r\xbdr0\xd6/\xc2\x08\xb7\xc3\x17\xa6\xf2\x19\xa27\x03\xa8\x02b\xc8'  # noqa: E501
WITHDRAWN: Final = b'\xd3x\x90\xa7..]\xf4+\xee\x9b\xd2x\xd8\xb8\x96)}\xff\xeb\x08\xb2\xb2P?rl\xfb.;\x98&'  # noqa: E501
ADDED_VESTING: Final = b"\xff'\x81\xf5\xafl\xf1\x15\xd1\x87\xdd\x0eN\xf5\x90\xf5\xd1(\x8b\x83\xef>\xb6s\x9ci\xdb\x99\xe7\x0c\x8bM"  # noqa: E501

SAFE_TOKEN_ID: Final = 'eip155:1/erc20:0x5aFE3855358E112B5647B952709E6165e1c1eEEe'
