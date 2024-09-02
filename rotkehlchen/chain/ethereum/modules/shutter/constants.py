from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

REDEEMED_VESTING: Final = b'|\xd0\x91\xe2\xff?\x9f\xb5\xd2\xaf[\x8f\xf0\xf5\x94\xb6\x96=\xb4N\x14?\xd4q\xa12\xb6IS_\x126'  # noqa: E501
SHUTTER_AIDROP_CONTRACT: Final = string_to_evm_address('0x024574C4C42c72DfAaa3ccA80f73521a4eF5Ca94')  # noqa: E501
CPT_SHUTTER: Final = 'shutter'
