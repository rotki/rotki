from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from eth_typing import ABI

    from rotkehlchen.types import ChecksumEvmAddress

SAVINGS_CONTRACT_ADDRESS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: string_to_evm_address('0x27d9AD987BdE08a0d083ef7e0e4043C857A17B38'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0xb41715e54e9f0827821A149AE8eC1aF70aa70180'),
    ChainID.BASE: string_to_evm_address('0x6426324Af1b14Df3cd03b2d500529083c5ea61BC'),
    ChainID.POLYGON_POS: string_to_evm_address('0xB519BAE359727e69990C27241Bef29b394A0ACbD'),
    ChainID.GNOSIS: string_to_evm_address('0xbF594D0feD79AE56d910Cb01b5dD4f4c57B04402'),
    ChainID.OPTIMISM: string_to_evm_address('0x6426324Af1b14Df3cd03b2d500529083c5ea61BC'),
}

SAVINGS_CONTRACT_ABI: Final[ABI] = [
    {
        'inputs': [{'name': '', 'type': 'address'}],
        'name': 'savings',
        'outputs': [
            {'name': 'saved', 'type': 'uint192'},
            {'name': 'ticks', 'type': 'uint64'},
            {'name': 'referrer', 'type': 'address'},
            {'name': 'referralFeePPM', 'type': 'uint32'},
        ],
        'stateMutability': 'view',
        'type': 'function',
    }, {
        'inputs': [{'name': 'accountOwner', 'type': 'address'}],
        'name': 'accruedInterest',
        'outputs': [{'name': '', 'type': 'uint192'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

# Saved(address,uint192): 0xf195ce54b48d5147da31c1fc525c8828b8836088b505a329e5de2b35da6731e2
SAVED_TOPIC: Final = b'\xf1\x95\xceT\xb4\x8dQG\xda1\xc1\xfcR\\\x88(\xb8\x83`\x88\xb5\x05\xa3)\xe5\xde+5\xdag1\xe2'  # noqa: E501
# InterestCollected(address,uint256,uint256): 0x9bbd517758fbae61197f1c1c04c8614064e89512dbaf4350dcdf76fcaa5e2161  # noqa: E501
INTEREST_COLLECTED_TOPIC: Final = b'\x9b\xbdQwX\xfb\xaea\x19\x7f\x1c\x1c\x04\xc8a@d\xe8\x95\x12\xdb\xafCP\xdc\xdfv\xfc\xaa^!a'  # noqa: E501
# Withdrawn(address,uint192): 0x47cf194f5e559cca0413017d38814a7843cc6f3052bc43c8085938774ae58151
WITHDRAWN_TOPIC: Final = b'G\xcf\x19O^U\x9c\xca\x04\x13\x01}8\x81JxC\xcco0R\xbcC\xc8\x08Y8wJ\xe5\x81Q'  # noqa: E501
