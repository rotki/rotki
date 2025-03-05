from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

ROUTER_V2: Final = string_to_evm_address('0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858')
ROUTER_V1: Final = string_to_evm_address('0x9c12939390052919aF3155f41Bf4160Fd3666A6f')
VOTER_CONTRACT_ADDRESS: Final = string_to_evm_address('0x41C914ee0c7E1A5edCD0295623e6dC557B5aBf3C')
VOTING_ESCROW_CONTRACT_ADDRESS: Final = string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d')  # noqa: E501
A_VELO: Final = Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db')
