from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.resolver import ethaddress_to_identifier

DEV_REWARD_DISTRIBUTOR: Final = string_to_evm_address('0x6081d7F04a8c31e929f25152d4ad37c83638C62b')
FLUENCE_IDENTIFIER: Final = ethaddress_to_identifier(string_to_evm_address('0x236501327e701692a281934230AF0b6BE8Df3353'))  # noqa: E501
CPT_FLUENCE: Final = 'fluence'
