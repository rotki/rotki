from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

ZEROX_ROUTER: Final = string_to_evm_address(
    '0xDef1C0ded9bec7F1a1670819833240f027b25EfF',
)
ZEROX_FLASH_WALLET: Final = string_to_evm_address(
    '0x22F9dCF4647084d6C31b2765F6910cd85C178C18',
)

# The settler contract has multiple deployments, and each deployment emits an event
# containing the git commit hash of the contract version used for that deployment.
# You can find this event in the deployment transaction logs.
# Example transaction with event log:
# https://etherscan.io/tx/0xfafcc9be3a8c6ceda26df29046b8651fa1298537b55c9b09fc5fd0d815f943e6#eventlog#236
# GitHub source reference:
# https://github.com/0xProject/0x-settler/blob/b1dd3e25b305fe0b4ccda70ed7d85b797501a3f7/src/SettlerBase.sol#L69

# TODO: Add support for SettlerMetaTxn.sol
# SettlerMetaTxn emits anonymous events and uses permit2, requiring a special case for this
# GitHub source reference:
# https://github.com/0xProject/0x-settler/blob/master/src/SettlerMetaTxn.sol

# Skipped version v1.2 because it dosn't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0xECf4248A682FFC676F4C596214CD6a4B463d8d2E'),  # V1.1 commit: 0x7b1c68714aeca5b797b1e3bf95d6c8675e9cc811000000000000000000000000  # noqa: E501
    string_to_evm_address('0x7f6ceE965959295cC64d0E6c00d99d6532d8e86b'),  # V1.3 commit: 0x336fda7ac33e46626cba703a82a53ad517aa8336000000000000000000000000  # noqa: E501
    string_to_evm_address('0x07E594aA718bB872B526e93EEd830a8d2a6A1071'),  # V1.4 commit: 0xa5a3b402765eb2940a6e29efa81a58e222d0ae6a000000000000000000000000  # noqa: E501
    string_to_evm_address('0x2c4B05349418Ef279184F07590E61Af27Cf3a86B'),  # V1.5 commit: 0x3ae13a6a1d3eea900d733ebc1d1ba9d772e6b415000000000000000000000000  # noqa: E501
    string_to_evm_address('0x70bf6634eE8Cb27D04478f184b9b8BB13E5f4710'),  # V1.6 commit: 0xa6f39ee20f0c4dfe1265f5d203dfc4f3f05ca003000000000000000000000000  # noqa: E501
    string_to_evm_address('0x0d0E364aa7852291883C162B22D6D81f6355428F'),  # V1.7 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
}
