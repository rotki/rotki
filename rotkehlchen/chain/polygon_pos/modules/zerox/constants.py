from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

ZEROX_FLASH_WALLET: Final = string_to_evm_address(
    '0xdB6f1920A889355780aF7570773609Bd8Cb1f498',
)

# Skipped version v1.2 because this contracts don't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0xC8536873bAf65695Be8Eba0f3a31fcfCE8bf8608'),  # V1.1 commit: 0x7b1c68714aeca5b797b1e3bf95d6c8675e9cc811000000000000000000000000  # noqa: E501
    string_to_evm_address('0xD29b634D35E9E22379241eAd1F5Ba431AF6dbba3'),  # V1.3 commit: 0x336fda7ac33e46626cba703a82a53ad517aa8336000000000000000000000000  # noqa: E501
    string_to_evm_address('0x6aEC4d9f02d6D4b9a09c588922eBC81a532b94d0'),  # V1.4 commit: 0x543ca9b301408c77ea0e8dbc6749f6b2bd01b3f3000000000000000000000000  # noqa: E501
    string_to_evm_address('0xd2aeAE6DC50a8efA8919E7783125cAcDE3b4e930'),  # V1.5 commit: 0xa5a3b402765eb2940a6e29efa81a58e222d0ae6a000000000000000000000000  # noqa: E501
    string_to_evm_address('0x88530dD3a2E72c2A6580F45AC9c2197e9b75a642'),  # V1.6 commit: 0x3ae13a6a1d3eea900d733ebc1d1ba9d772e6b415000000000000000000000000  # noqa: E501
    string_to_evm_address('0xfF4b330c5BC3811b66d8864CF8078D8F2db20Dd6'),  # V1.7 commit: 0xa6f39ee20f0c4dfe1265f5d203dfc4f3f05ca003000000000000000000000000  # noqa: E501
    string_to_evm_address('0x7f20a7A526D1BAB092e3Be0733D96287E93cEf59'),  # V1.8 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
}
