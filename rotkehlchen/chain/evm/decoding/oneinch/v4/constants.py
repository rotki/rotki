from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

ONEINCH_V4_ROUTER: Final = string_to_evm_address('0x1111111254fb6c44bAC0beD2854e76F90643097d')

ORDERFILLED_RFQ: Final = b"\xc3\xb69\xf0+\x12[\xfa\x16\x0ePs\x9b\x8cD\xeb-\x1bi\x08\xe2\xb6\xd5\x92\\mw\x0f,\xa7\x81'"  # noqa: E501
DEFI_PLAZA_SWAPPED: Final = b'g\x82\x19\x0c\x91\xd4\xa7\xe8\xad*\x86}\xee\xd6\xec\n\x97\x0c\xab\x8f\xf17\xae+\xd4\xab\xd9+8\x10\xf4\xd3'  # dex protocol that 1inch routes swaps through  # noqa: E501
