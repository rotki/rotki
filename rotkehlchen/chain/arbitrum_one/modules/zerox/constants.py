from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

# Skipped versions v1.1, v1.2, and v1.4 because these contracts don't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0x2b6625AAFC65373e5a82A0349F777FA11F7F04d1'),  # V1.3 commit: 0x336fda7ac33e46626cba703a82a53ad517aa8336000000000000000000000000  # noqa: E501
    string_to_evm_address('0xc8e09d4Ac2bf8b83a842068A0A6e79E118414a1d'),  # V1.5 commit: 0xa5a3b402765eb2940a6e29efa81a58e222d0ae6a000000000000000000000000  # noqa: E501
    string_to_evm_address('0x845a4dae544147FFe8cB536079b58ee43F320067'),  # V1.6 commit: 0x3ae13a6a1d3eea900d733ebc1d1ba9d772e6b415000000000000000000000000  # noqa: E501
    string_to_evm_address('0xf3E01012Ce60BB95AE294D5b24a9Fc3af245b53b'),  # V1.7 commit: 0xa6f39ee20f0c4dfe1265f5d203dfc4f3f05ca003000000000000000000000000  # noqa: E501
    string_to_evm_address('0x6dB4d3B89b06d3C8Bd2074Ee1F1B440baf122eAd'),  # V1.8 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
    string_to_evm_address('0xB254ee265261675528bdDb0796741c0C65a4C158'),  # V1.9 commit: 0xed3a62a794e1598537d99e3f7d44d08f2ff2cac8000000000000000000000000  # noqa: E501
    string_to_evm_address('0x246475E1F63d8e26D6f4fB6029033da8831eD396'),  # commit: 0x2ddbef2c14ee27f3dafcfdb3d376dad949d7a86e000000000000000000000000  # noqa: E501
    string_to_evm_address('0x80A5a825b8bb07e355244A7De6384a064b0D601d'),  # commit: 8304ccde0442e9b705cf709a0986d722a74a19e1  # noqa: E501
    string_to_evm_address('0x7a5118C54Bd5a97F2A2c1240Fe5A9f5F309E4C97'),
    string_to_evm_address('0x67b5657aF7284eAE94184A8Fcf982C0d976b9AB9'),
    string_to_evm_address('0x653eFb15d8CE9ccC995b65d407Df337560096E30'),
    string_to_evm_address('0xa56DCe9f402daeE3665A5eE9252DdB5A88B305AA'),
    string_to_evm_address('0x56C65290a3309247379345C9Fd270A308Ce8b3ec'),
    string_to_evm_address('0xa11F4a058e3E167ad111897c97cA2965F7e58177'),
    string_to_evm_address('0x36e50FE8879dC11453fBdE7983c82B0E8a04BDF6'),
    string_to_evm_address('0x99794A30EaC50663F79e16cba223e2764F701cd4'),
}
