from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_ROTKI: Final = 'rotki'
ROTKI_SPONSORSHIP_TREASURY_ADDRESS: Final = string_to_evm_address('0x0BeBD2FcA9854F657329324aA7dc90F656395189')  # noqa: E501
ROTKI_SPONSORSHIP_CONTRACT_ADDRESS: Final = string_to_evm_address('0x3337286E850cf01B8A8B6094574f0dd6a2108B16')  # noqa: E501
ROTKI_NFT_MINTED_TOPIC: Final = b'd\x9co\xb9\xa7\x9e\xe3M\xbd\xe8\x7f\x851d3\xcbt\x14\xef\xb6\x84\xadN\x05ft\xa4\x11\x1b\xd6\x92B'  # noqa: E501
ROTKI_SPONSORSHIP_COLLECTION_IDENTIFIER: Final = f'eip155:1/erc721:{ROTKI_SPONSORSHIP_CONTRACT_ADDRESS}'  # noqa: E501
ROTKI_SPONSORSHIP_TIER_MAPPING: Final = {
    0: 'Bronze',
    1: 'Silver',
    2: 'Gold',
}
