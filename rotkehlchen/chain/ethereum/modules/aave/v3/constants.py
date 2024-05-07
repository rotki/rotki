from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


POOL_ADDRESS: Final = string_to_evm_address('0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2')
ETH_GATEWAYS: Final = (string_to_evm_address('0x893411580e590D62dDBca8a703d61Cc4A8c7b2b9'),)
AAVE_TREASURY: Final = string_to_evm_address('0x464C71f6c2F760DdA6093dCB91C24c39e5d6e18c')
AAVE_V3_DATA_PROVIDER: Final = string_to_evm_address('0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3')
