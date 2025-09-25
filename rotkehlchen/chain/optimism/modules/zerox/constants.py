from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

ZEROX_ROUTER: Final = string_to_evm_address(
    '0xDEF1ABE32c034e558Cdd535791643C58a13aCC10',
)
ZEROX_FLASH_WALLET: Final = string_to_evm_address(
    '0xA3128d9b7Cca7d5Af29780a56abEec12B05a6740',
)

# Skipped version v1.1, v1.2, v1.3 and v1.5 because these contracts don't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0x7600F49428e551AF89D5C6b8e77B8cF3e198F936'),  # V1.4 commit: 0x336fda7ac33e46626cba703a82a53ad517aa8336000000000000000000000000  # noqa: E501
    string_to_evm_address('0x1a3b48EA0C6e9A52511A196A287fa8371e5Ee7a0'),  # V1.6 commit: 0xa5a3b402765eb2940a6e29efa81a58e222d0ae6a000000000000000000000000  # noqa: E501
    string_to_evm_address('0x733D95e5CB3Ca43Eab2752f1D4f1A0d2686965C6'),  # V1.7 commit: 0x3ae13a6a1d3eea900d733ebc1d1ba9d772e6b415000000000000000000000000  # noqa: E501
    string_to_evm_address('0x70cA548cF343B63E5B0542F0F3EC84c61Ca1086f'),  # V1.8 commit: 0xa6f39ee20f0c4dfe1265f5d203dfc4f3f05ca003000000000000000000000000  # noqa: E501
    string_to_evm_address('0x402867B638339ad8Bec6e5373cfa95Da0b462c85'),  # V1.9 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
    string_to_evm_address('0xC82384Da1318F167Ff453760EB71DD6012896240'),  # commit: 2ddbef2c14ee27f3dafcfdb3d376dad949d7a86e  # noqa: E501
    string_to_evm_address('0xd8014f15A920bf9edfDb87159Ee10CADc07FcB53'),  # commit: 0x1440ba6fefadea1f0fe0704789662d0e7ff97a2d000000000000000000000000  # noqa: E501
    string_to_evm_address('0x86418D12eC52d1022B2f7EF849eEBFEd064F3826'),  # commit: 8304ccde0442e9b705cf709a0986d722a74a19e1  # noqa: E501
}
