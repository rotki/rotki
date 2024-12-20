from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

ETHEREUM_MONERIUM_LEGACY_ADDRESSES: Final = {
    string_to_evm_address('0x3231Cb76718CDeF2155FC47b5286d82e6eDA273f'),  # legacy EURe
    string_to_evm_address('0x7ba92741Bf2A568abC6f1D3413c58c6e0244F8fD'),  # legacy GBPe
    string_to_evm_address('0xBc5142e0CC5eB16b47c63B0f033d4c2480853a52'),  # legacy USDe
    string_to_evm_address('0xC642549743A93674cf38D6431f75d6443F88E3E2'),  # legacy ISKe
}
ETHEREUM_MONERIUM_ADDRESSES: Final = ETHEREUM_MONERIUM_LEGACY_ADDRESSES | {
    string_to_evm_address('0x39b8B6385416f4cA36a20319F70D28621895279D'),  # EURe
    string_to_evm_address('0x78a20B7AF85156B4389a349Aa4c96efC2E509768'),  # GBPe
    string_to_evm_address('0x05968f40939fdc016AD58F82Cd08dA884825aD55'),  # USDe
    string_to_evm_address('0x38D22BD604c4549e2cC15e94B8e22E6FE4aE82B4'),  # ISKe
}

V1_TO_V2_MONERIUM_MAPPINGS: Final = {
    'eip155:1/erc20:0x3231Cb76718CDeF2155FC47b5286d82e6eDA273f': Asset('eip155:1/erc20:0x39b8B6385416f4cA36a20319F70D28621895279D'),  # noqa: E501
    'eip155:1/erc20:0x7ba92741Bf2A568abC6f1D3413c58c6e0244F8fD': Asset('eip155:1/erc20:0x78a20B7AF85156B4389a349Aa4c96efC2E509768'),  # noqa: E501
    'eip155:1/erc20:0xBc5142e0CC5eB16b47c63B0f033d4c2480853a52': Asset('eip155:1/erc20:0x05968f40939fdc016AD58F82Cd08dA884825aD55'),  # noqa: E501
    'eip155:1/erc20:0xC642549743A93674cf38D6431f75d6443F88E3E2': Asset('eip155:1/erc20:0x38D22BD604c4549e2cC15e94B8e22E6FE4aE82B4'),  # noqa: E501
}
