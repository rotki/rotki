from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

# Skipped versions v1.1, v1.2, and v1.4 because these contracts dosn't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0x2b6625AAFC65373e5a82A0349F777FA11F7F04d1'),  # V1.3 commit: 0x336fda7ac33e46626cba703a82a53ad517aa8336000000000000000000000000  # noqa: E501
    string_to_evm_address('0xc8e09d4Ac2bf8b83a842068A0A6e79E118414a1d'),  # V1.5 commit: 0xa5a3b402765eb2940a6e29efa81a58e222d0ae6a000000000000000000000000  # noqa: E501
    string_to_evm_address('0x845a4dae544147FFe8cB536079b58ee43F320067'),  # V1.6 commit: 0x3ae13a6a1d3eea900d733ebc1d1ba9d772e6b415000000000000000000000000  # noqa: E501
    string_to_evm_address('0xf3E01012Ce60BB95AE294D5b24a9Fc3af245b53b'),  # V1.7 commit: 0xa6f39ee20f0c4dfe1265f5d203dfc4f3f05ca003000000000000000000000000  # noqa: E501
    string_to_evm_address('0x6dB4d3B89b06d3C8Bd2074Ee1F1B440baf122eAd'),  # V1.8 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
    string_to_evm_address('0xB254ee265261675528bdDb0796741c0C65a4C158'),  # V1.9 commit: 0xed3a62a794e1598537d99e3f7d44d08f2ff2cac8000000000000000000000000  # noqa: E501
}
