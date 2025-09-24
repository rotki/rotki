from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

BLUR_STAKING_CONTRACT: Final = string_to_evm_address('0xeC2432a227440139DDF1044c3feA7Ae03203933E')
BLUR_DISTRIBUTOR: Final = string_to_evm_address('0xB38283CB75faaBb384c22F97c633606265DdF093')
BLUR_IDENTIFIER: Final = 'eip155:1/erc20:0x5283D291DBCF85356A21bA090E6db59121208b44'
CPT_BLUR: Final = 'blur'
BLUR_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_BLUR,
    label='Blur',
    image='blur.png',
)
