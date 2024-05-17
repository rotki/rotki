from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


SWAP_SIGNATURE: Final = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501
UNISWAP_V2_ROUTER: Final = string_to_evm_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')
