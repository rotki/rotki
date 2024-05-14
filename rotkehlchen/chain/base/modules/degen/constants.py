from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_DEGEN: Final = 'degen'
CLAIM_AIRDROP_2_CONTRACT: Final = string_to_evm_address('0x88d42b6DBc10D2494A0c6c189CeFC7573a6dCE62')  # noqa: E501
CLAIM_AIRDROP_3_CONTRACT: Final = string_to_evm_address('0x0Bf676823f958d0aE6af9860880FC7A327a0c582')  # noqa: E501
DEGEN_TOKEN_ID: Final = 'eip155:8453/erc20:0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed'
