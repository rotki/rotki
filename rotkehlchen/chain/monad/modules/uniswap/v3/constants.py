from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

UNISWAP_V3_NFT_MANAGER: Final = string_to_evm_address('0x7197E214c0b767cFB76Fb734ab638E2c192F4E53')
UNISWAP_SWAP_ROUTER_02: Final = string_to_evm_address('0xfE31F71C1b106EAc32F1A19239c9a9A72ddfb900')
UNISWAP_UNIVERSAL_ROUTER: Final = string_to_evm_address(
    '0x0D97Dc33264bfC1c226207428A79b26757fb9dc3',
)
UNISWAP_ROUTER_ADDRESSES: Final = {UNISWAP_SWAP_ROUTER_02, UNISWAP_UNIVERSAL_ROUTER}
