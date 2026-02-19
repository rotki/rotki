from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

LOCKED: Final = b'L\x00(\x1b\x0b\xce!\xcdpd N\x92\x14m\x97,5\x9c7C\xb9\xa5\x03\xf48\xb42^\xfa\xaf\x14'  # noqa: E501
UNLOCKED: Final = b"\xc8f\xd6!,X\xa2H\nm\xa1O\x1b\xdb\xaa\xe0\xc1'\xcd\xc8)d\t\x15z#\xb9h\x14\x90f\xce"  # noqa: E501
STAKE_DEPOSITED_V2: Final = b'\x1a\x32\x53\x85\xf1\x68\x07\xe9\x9f\xb6\x88\xb5\x97\xdb\x78\xb0\x0f\xae\xe3\x13\xdc\xf0\x2e\x88\x2d\xd1\x6d\xaa\xb6\xfc\x3e\x1f'  # noqa: E501

CPT_OCTANT: Final = 'octant'
OCTANT_DEPOSITS: Final = string_to_evm_address('0x879133Fd79b7F48CE1c368b0fCA9ea168eaF117c')
OCTANT_DEPOSITS_V2: Final = string_to_evm_address('0x7bee381d8ea5AE16459BcCD06ee5600bD0F1E86f')
OCTANT_REWARDS: Final = string_to_evm_address('0xc64783f0BE60A81A716535287539a694403183ba')
