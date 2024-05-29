from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

TOKEN_MESSENGER: Final = string_to_evm_address('0x1682Ae6375C4E4A97e4B583BC394c861A46D8962')
MESSAGE_TRANSMITTER: Final = string_to_evm_address('0xAD09780d193884d503182aD4588450C416D6F9D4')
USDC_IDENTIFIER_BASE: Final = 'eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
