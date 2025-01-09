from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

UNISWAP_V3_NFT_MANAGER: Final = string_to_evm_address('0x7b8A01B39D58278b5DE7e48c8449c9f4F5170613')
UNISWAP_AUTO_ROUTER_V2: Final = string_to_evm_address('0xB971eF87ede563556b2ED4b1C0b0019111Dd85d2')
UNISWAP_UNIVERSAL_ROUTER: Final = string_to_evm_address('0x5Dc88340E1c5c6366864Ee415d6034cadd1A9897')  # noqa: E501
UNISWAP_ROUTER_ADDRESSES: Final = {UNISWAP_AUTO_ROUTER_V2, UNISWAP_UNIVERSAL_ROUTER}
