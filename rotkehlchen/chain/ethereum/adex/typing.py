from enum import Enum
from typing import Any, Callable, Dict, NamedTuple, Optional, Union

from eth_typing.evm import ChecksumAddress
from eth_utils.typing import HexStr

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Timestamp


class EventType(Enum):
    """Supported events"""
    BOND = 1
    UNBOND = 2
    UNBOND_REQUEST = 3

    def __str__(self) -> str:
        if self == EventType.BOND:
            return 'bond'
        if self == EventType.UNBOND:
            return 'unbond'
        if self == EventType.UNBOND_REQUEST:
            return 'unbond_request'
        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')


class Bond(NamedTuple):
    tx_hash: HexStr  # from bond.id
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp
    bond_id: HexStr
    amount: FVal
    pool_id: HexStr
    nonce: int


class Unbond(NamedTuple):
    tx_hash: HexStr  # from unbond.id
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp
    bond_id: HexStr


class UnbondRequest(NamedTuple):
    tx_hash: HexStr  # from unbond.id
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp
    bond_id: HexStr


# Contains the events' (e.g. bond, unbond) common attributes
class EventCoreData(NamedTuple):
    tx_hash: HexStr
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp


class ADXStakingBalance(NamedTuple):
    pool_id: HexStr
    pool_name: Optional[str]
    balance: Balance
    address: ChecksumAddress

    def serialize(self) -> Dict[str, Any]:
        return {
            'pool_id': self.pool_id,
            'pool_name': self.pool_name,
            'balance': self.balance.serialize(),
            'address': self.address,
        }


DeserializationMethod = Callable[..., Union[Bond, Unbond, UnbondRequest]]
