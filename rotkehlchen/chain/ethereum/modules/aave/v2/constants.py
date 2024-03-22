
from typing import Final
from rotkehlchen.chain.evm.types import string_to_evm_address


POOL_ADDRESS: Final = string_to_evm_address('0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9')
DEPOSIT: Final = b'\xdehW!\x95D\xbb[wF\xf4\x8e\xd3\x0b\xe68o\xef\xc6\x1b/\x86L\xac\xf5Y\x89;\xf5\x0f\xd9Q'  # noqa: E501
BORROW: Final = b'\xc6\xa8\x980\x9e\x82>\xe5\x0b\xacd\xe4\\\xa8\xad\xbaf\x90\xe9\x9exA\xc4]uN*8\xe9\x01\x9d\x9b'  # noqa: E501
REPAY: Final = b'L\xdd\xe6\xe0\x9b\xb7U\xc9\xa5X\x9e\xba\xecd\x0b\xbf\xed\xff\x13b\xd4\xb2U\xeb\xf83\x97\x82\xb9\x94/\xaa'  # noqa: E501
ETH_GATEWAYS: Final = (
    string_to_evm_address('0xEFFC18fC3b7eb8E676dac549E0c693ad50D1Ce31'),
    string_to_evm_address('0xcc9a0B7c43DC2a5F023Bb9b738E45B0Ef6B06E04'),
)
