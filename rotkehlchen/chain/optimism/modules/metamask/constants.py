from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address


METAMASK_ROUTER: Final = string_to_evm_address('0x9dDA6Ef3D919c9bC8885D5560999A3640431e8e6')
METAMASK_FEE_RECEIVER_ADDRESS: Final = string_to_evm_address(
    '0x45D047bfCB1055B9dd531eF9605e8f0b0Dc285f3',
)
