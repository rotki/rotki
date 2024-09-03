from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_VOTIUM: Final = 'votium'
CLAIMED: Final = b'Gf\x92\x1f\\Ydm"\xd7\xd2f\xa2\x91d\xc8\xe9b6\x84\xd8\xdf\xdb\xd91s\x1d\xfd\xca\x02R8'  # noqa: E501
VOTIUM_CONTRACTS: Final = [  # https://docs.votium.app/faq/contract-addresses
    string_to_evm_address('0x378Ba9B73309bE80BF4C2c027aAD799766a7ED5A'),  # MultiMerkleStash
    string_to_evm_address('0x34590960981f98b55d236b70E8B4d9929ad89C9c'),  # veCRV Merkle Stash
]
