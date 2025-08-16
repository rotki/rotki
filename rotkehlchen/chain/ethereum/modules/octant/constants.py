from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

LOCKED: Final = b'L\x00(\x1b\x0b\xce!\xcdpd N\x92\x14m\x97,5\x9c7C\xb9\xa5\x03\xf48\xb42^\xfa\xaf\x14'  # noqa: E501
UNLOCKED: Final = b"\xc8f\xd6!,X\xa2H\nm\xa1O\x1b\xdb\xaa\xe0\xc1'\xcd\xc8)d\t\x15z#\xb9h\x14\x90f\xce"  # noqa: E501

CPT_OCTANT: Final = 'octant'
OCTANT_DEPOSITS: Final = string_to_evm_address('0x879133Fd79b7F48CE1c368b0fCA9ea168eaF117c')
OCTANT_REWARDS: Final = string_to_evm_address('0xc64783f0BE60A81A716535287539a694403183ba')
