from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_AZTEC: Final = 'aztec'
AZTEC_CPT_DETAILS: Final = CounterpartyDetails(identifier=CPT_AZTEC, label='Aztec', image='aztec.svg')  # noqa: E501
AZTEC_TOKEN: Final = string_to_evm_address('0xA27EC0006e59f245217Ff08CD52A7E8b169E62D2')
AZTEC_TOKEN_ID: Final = 'eip155:1/erc20:0xA27EC0006e59f245217Ff08CD52A7E8b169E62D2'
A_AZTEC: Final = Asset(AZTEC_TOKEN_ID)
STAKING_REGISTRY: Final = string_to_evm_address('0x042dF8f42790d6943F41C25C2132400fd727f452')
GSE: Final = string_to_evm_address('0xa92ecFD0E70c9cd5E5cd76c50Af0F7Da93567a4f')
PULL_SPLIT_FACTORY: Final = string_to_evm_address('0x6B9118074aB15142d7524E8c4ea8f62A3Bdb98f1')

STAKED_WITH_PROVIDER: Final = bytes.fromhex(
    'c91c8b4e934fb8f46c6d08a34d60ceb8dbe4ab6844a7040ca4c580e5a837d5c7',
)
SPLIT_CREATED: Final = bytes.fromhex(
    'f36c74b44f70742fdc66fe7f34107c9e5025433a131e7797e9203203a3a74428',
)
SPLIT_DISTRIBUTED: Final = bytes.fromhex(
    '562c19c0e7b3493417e3cf5103baa939f4d0e9c1087be236aebb46b84e09c7d9',
)
GSE_DEPOSIT: Final = bytes.fromhex(
    '7986a8ff398d9a6be88df9dfc6e3c9a83e4da5544241aad420d1cf7c214e4345',
)
DELEGATE_CHANGED: Final = bytes.fromhex(
    '3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f',
)

AZTEC_STAKING_DATA: Final = 'aztec_staking'
