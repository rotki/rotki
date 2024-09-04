from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

BLUR_STAKING_CONTRACT: Final = string_to_evm_address('0xeC2432a227440139DDF1044c3feA7Ae03203933E')
BLUR_DEPOSITED: Final = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
BLUR_WITHDRAWN: Final = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501
BLUR_AIRDROP_2_CLAIM: Final = b'\xd8\x13\x8f\x8a?7|RY\xcaT\x8ep\xe4\xc2\xde\x94\xf1)\xf5\xa1\x106\xa1[iQ<\xba+Bj'  # noqa: E501
BLUR_DISTRIBUTOR: Final = string_to_evm_address('0xB38283CB75faaBb384c22F97c633606265DdF093')
BLUR_IDENTIFIER: Final = 'eip155:1/erc20:0x5283D291DBCF85356A21bA090E6db59121208b44'
CPT_BLUR: Final = 'blur'
BLUR_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_BLUR,
    label='Blur',
    image='blur.png',
)
