from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_GHO: Final = 'gho'
GHO_IDENTIFIER: Final = 'eip155:1/erc20:0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f'
STAKED_GHO_ADDRESS: Final = string_to_evm_address('0x1a88Df1cFe15Af22B3c4c783D4e6F7F9e0C1885d')
STKGHO_IDENTIFIER: Final = f'eip155:1/erc20:{STAKED_GHO_ADDRESS}'
COOLDOWN_TOPIC: Final = b'\x8a\x05\xf9\x11\xd8\xab\x7f\xc5\x0f\xec7\xefK\xa7\xf9\xbf\xcb\x1a<\x19\x1c\x81\xdc\xd8$\xad\tF\xc4\xe2\re'  # noqa: E501
STAKE_TOPIC: Final = b"l\x86\xf3\xfdQ\x18\xb3\xaa\x8b\xb4\xf3\x89\xa6\x17\x04m\xe0\xa3\xd3\xd4w\xde\x1a\x16s\xd2'\xf8\x02\xf6\x16\xdc"  # noqa: E501
