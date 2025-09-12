from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

# Skipped version v1.1, v1.3 and v1.5 because these contracts dosn't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0x3d868Cd3f8f24DA361364E442411DAe23CD79cC4'),  # V1.2 commit: 0x7426193dacc58467ab4b85bb1fa7acbc0a4764d4000000000000000000000000  # noqa: E501
    string_to_evm_address('0x55873e4b1Dd63ab3Fea3CA47c10277655Ac2DcE0'),  # V1.4 commit: 0x336fda7ac33e46626cba703a82a53ad517aa8336000000000000000000000000  # noqa: E501
    string_to_evm_address('0x163631Ebf9550476156d78748dFF6b1C691d89e1'),  # V1.6 commit: 0xa5a3b402765eb2940a6e29efa81a58e222d0ae6a000000000000000000000000  # noqa: E501
    string_to_evm_address('0xf15c6EC20e5863351D3bBC9E742f9208E3A343fF'),  # V1.7 commit: 0x3ae13a6a1d3eea900d733ebc1d1ba9d772e6b415000000000000000000000000  # noqa: E501
    string_to_evm_address('0xBc3c5cA50b6A215edf00815965485527f26F5dA8'),  # V1.8 commit: 0xa6f39ee20f0c4dfe1265f5d203dfc4f3f05ca003000000000000000000000000  # noqa: E501
    string_to_evm_address('0x6A57A0579E91A5B7ce9c2d08b93E1A9b995f974f'),  # V1.9 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
    string_to_evm_address('0x5C9bdC801a600c006c388FC032dCb27355154cC9'),  # V1.10 commit: 0xed3a62a794e1598537d99e3f7d44d08f2ff2cac8000000000000000000000000  # noqa: E501
    string_to_evm_address('0xf525fF21C370Beb8D9F5C12DC0DA2B583f4b949F'),  # V1.11 commit: 0x4c4f79b89a708c57b74f2ab830a576f1523ae1a9000000000000000000000000  # noqa: E501
}
