from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


POOL_ADDRESS: Final = string_to_evm_address('0xb50201558B00496A145fE76f7424749556E326D8')
ETH_GATEWAYS: Final = (string_to_evm_address('0xfE76366A986B72c3f2923e05E6ba07b7de5401e4'),)
AAVE_TREASURY: Final = string_to_evm_address('0x3e652E97ff339B73421f824F5b03d75b62F1Fb51')
