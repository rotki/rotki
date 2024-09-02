from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

POOL_ADDRESS: Final = string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9')
ETH_GATEWAYS: Final = (
    string_to_evm_address('0xEFFC18fC3b7eb8E676dac549E0c693ad50D1Ce31'),
    string_to_evm_address('0xcc9a0B7c43DC2a5F023Bb9b738E45B0Ef6B06E04'),
)
