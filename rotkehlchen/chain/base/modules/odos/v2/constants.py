from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

ODOS_V2_ROUTER: Final = string_to_evm_address('0x19cEeAd7105607Cd444F5ad10dd51356436095a1')
REWARD_CLAIMED_TOPIC: Final = b'n\xc6\x85\x17\x1a\x90(\xd1\x9d\xc1U\xa4\x8ex$\xe3\xc6\x8b\x03\xbc\x89\x95A\x0e\x00j\xbe<\xbb\xeb>-'  # noqa: E501
ODOS_AIRDROP_DISTRIBUTOR: Final = string_to_evm_address('0x4C8f8055D88705f52c9994969DDe61AB574895a3')  # noqa: E501
ODOS_ASSET_ID: Final = 'eip155:8453/erc20:0xca73ed1815e5915489570014e024b7EbE65dE679'
