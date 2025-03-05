from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

ROUTER: Final = string_to_evm_address('0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43')
VOTER_CONTRACT_ADDRESS: Final = string_to_evm_address('0x16613524e02ad97eDfeF371bC883F2F5d6C480A5')
VOTING_ESCROW_CONTRACT_ADDRESS: Final = string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4')  # noqa: E501
A_AERO: Final = Asset('eip155:8453/erc20:0x940181a94A35A4569E4529A3CDfB74e38FD98631')
