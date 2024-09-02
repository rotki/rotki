from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_DEFISAVER: Final = 'defisaver'
SUB_STORAGE: Final = string_to_evm_address('0x1612fc28Ee0AB882eC99842Cde0Fc77ff0691e90')

SUBSCRIBE: Final = b'w\x91\xee\xa7\xfdZ\x87y@\xfd\x06T\xc6\xb1\xe0Y\x11)<\xed\xab\xdf\xe1\xf9\x9b|,\xb00\x8d\xba\xf7'  # noqa: E501
DEACTIVATE_SUB: Final = b'\x1f\x854\xa3*\xe8\x1aG\xc9\xe9\xfe%m\x92O:\xd6h\xe9\x19\x16\xa4\x8f\xd4\x1a\xc2\x7f\x84\xc6m\x94,'  # noqa: E501
