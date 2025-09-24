from typing import Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

WCT_TOKEN_ID: Final = 'eip155:10/erc20:0xeF4461891DfB3AC8572cCf7C794664A8DD927945'

WALLETCONECT_AIRDROP_CLAIM: Final = string_to_evm_address('0x4ee97a759AACa2EdF9c1445223b6Cd17c2eD3fb4')  # noqa: E501
WALLETCONECT_STAKE_WEIGHT: Final = string_to_evm_address('0x521B4C065Bbdbe3E20B3727340730936912DfA46')  # noqa: E501


CPT_WALLETCONNECT: Final = 'walletconnect'
WALLETCONNECT_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_WALLETCONNECT,
    label='WalletConnect',
    image='walletconnect.svg',
)
