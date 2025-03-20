from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

# Skipped versions v1.1 to v1.4 because these contracts dosn't have transactions
SETTLER_ROUTERS: Final = {
    string_to_evm_address('0xb2845bb0e9166357938445539Eb9bE94338594f2'),  # V1.5 commit: 0xa177de1aa0ab217473aa8fa8d94df63b61ba8cb7000000000000000000000000  # noqa: E501
    string_to_evm_address('0x0BE366A2cfFa54901B05c19B76C7a29f5608ad25'),  # V1.6 commit: 0x7f9bb31ef098b402f3a69fcadbba598849617b28000000000000000000000000  # noqa: E501
    string_to_evm_address('0xff48D64D1aEAe4c17b6a6Aa43e002345e21b8C51'),  # V1.7 commit: 0x85e036fe008a5226ee57faaf46c8e1454004e76e000000000000000000000000  # noqa: E501
    string_to_evm_address('0x11CD8a23558A05d7f0a8F9c33012B1529FEF65bc'),  # V1.8 commit: 0xfcb4511565e07d5302ca7efd9b70aebacc150fe2000000000000000000000000  # noqa: E501
    string_to_evm_address('0x068BA5d0540e27b39c71a00a1c0c1E669D62Dc10'),  # V1.9 commit: 0xd86391e90c849c1e925e111e2db3e3a46f063011000000000000000000000000  # noqa: E501
    string_to_evm_address('0x4C6F446dD88fD1be8B80D2940806002777dc12a2'),  # V1.10 commit: 0xffc129424fbe525c124e52cff5225afbfb610534000000000000000000000000  # noqa: E501
}
