from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

TOKEN_MESSENGER: Final = string_to_evm_address('0x19330d10D9Cc8751218eaf51E8885D058642E08A')
MESSAGE_TRANSMITTER: Final = string_to_evm_address('0xC30362313FBBA5cf9163F0bb16a0e01f01A896ca')
USDC_IDENTIFIER_ARB: Final = 'eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'
