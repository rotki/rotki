from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

UNISWAP_V3_NFT_MANAGER: Final = string_to_evm_address('0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1')
UNISWAP_AUTO_ROUTER_V1: Final = string_to_evm_address('0xE592427A0AEce92De3Edee1F18E0157C05861564')
UNISWAP_AUTO_ROUTER_V2: Final = string_to_evm_address('0x2626664c2603336E57B271c5C0b26F421741e481')
UNISWAP_UNIVERSAL_ROUTER: Final = string_to_evm_address('0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD')  # noqa: E501
UNISWAP_ROUTER_ADDRESSES: Final = {UNISWAP_AUTO_ROUTER_V1, UNISWAP_AUTO_ROUTER_V2, UNISWAP_UNIVERSAL_ROUTER}  # noqa: E501
