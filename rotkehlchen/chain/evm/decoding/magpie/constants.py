from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_MAGPIE: Final = 'magpie'
MAGPIE_LABEL: Final = 'Magpie'
MAGPIE_ICON: Final = 'magpie.png'

# Router addresses across different chains
# All chains use the same router address
MAGPIE_ROUTER: Final = string_to_evm_address('0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B')

# Method signatures for Magpie swaps
# These are the first 4 bytes of the function selector
MAGPIE_METHODS: Final = {
    b'\x73\xfc\x44\x57',  # swapWithMagpieSignature - most common method
    b'\x25\xe6\x51\xed',  # swap method
    b'\x2f\x86\x56\x33',  # swap(SwapArgs calldata swapArgs)
    b'\x12\xaa\x3c\xf6',  # swapTokensForTokens
}

# Event signatures
# Main swap event signature
SWAPPED = b" \xef\xd6\xd5\x19[{P'?\x01\xcdy\xa2y\x89%SV\xf9\xf12\x93\xed\xc5>\xe1B\xac\xcf\xdbu"
