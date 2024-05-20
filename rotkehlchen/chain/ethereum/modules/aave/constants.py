from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

STK_AAVE_ADDR: Final = string_to_evm_address('0x4da27a545c0c5B758a6BA100e3a049001de870f5')
STKAAVE_IDENTIFIER: Final = f'eip155:1/erc20:{STK_AAVE_ADDR}'
STAKED_AAVE: Final = b"l\x86\xf3\xfdQ\x18\xb3\xaa\x8b\xb4\xf3\x89\xa6\x17\x04m\xe0\xa3\xd3\xd4w\xde\x1a\x16s\xd2'\xf8\x02\xf6\x16\xdc"  # noqa: E501
REDEEM_AAVE: Final = b'?i?\xff\x03\x8b\xb8\xa0F\xaav\xd9Qa\x90\xactD\xf7\xd6\x9c\xf9R\xc4\xcb\xdc\x08o\xde\xf2\xd6\xfc'  # noqa: E501
