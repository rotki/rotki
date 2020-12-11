from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_typing.evm import ChecksumAddress
from eth_utils.typing import HexStr

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Timestamp

AdexEventDBTuple = (
    Tuple[
        str,  # tx_hash
        str,  # address
        str,  # identity_address
        int,  # timestamp
        str,  # bond_id
        str,  # type
        Optional[str],  # pool_id
        Optional[str],  # amount
        Optional[int],  # nonce
        Optional[int],  # slashed_at
        Optional[int],  # unlock_at
    ]
)


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
        raise AttributeError(f'Corrupt value {self} for EventType -- Should never happen')

    def pretty_name(self) -> str:
        if self == EventType.BOND:
            return 'deposit'
        if self == EventType.UNBOND:
            return 'withdraw'
        if self == EventType.UNBOND_REQUEST:
            return 'withdraw request'
        raise AttributeError(f'Corrupt value {self} for EventType -- Should never happen')


class Bond(NamedTuple):
    tx_hash: HexStr  # from bond.id
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp
    bond_id: HexStr
    amount: FVal
    pool_id: HexStr
    nonce: int
    slashed_at: Timestamp  # from bond.slashedAtStart

    def serialize(self) -> Dict[str, Any]:
        return {
            'tx_hash': self.tx_hash,
            'identity_address': self.identity_address,
            'timestamp': self.timestamp,
            'bond_id': self.bond_id,
            'amount': str(self.amount),
            'event_type': EventType.BOND.pretty_name(),
        }

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            str(self.tx_hash),
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(self.bond_id),
            str(EventType.BOND),
            str(self.pool_id),
            str(self.amount),
            self.nonce,
            int(self.slashed_at),
            None,  # unlock_at
        )


class Unbond(NamedTuple):
    tx_hash: HexStr  # from unbond.id
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp
    bond_id: HexStr

    def serialize(self) -> Dict[str, Any]:
        return {
            'tx_hash': self.tx_hash,
            'identity_address': self.identity_address,
            'timestamp': self.timestamp,
            'bond_id': self.bond_id,
            'event_type': EventType.UNBOND.pretty_name(),
        }

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            str(self.tx_hash),
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(self.bond_id),
            str(EventType.UNBOND),
            None,  # pool_id
            None,  # amount
            None,  # nonce
            None,  # slashed_at
            None,  # unlock_at
        )


class UnbondRequest(NamedTuple):
    tx_hash: HexStr  # from unbond.id
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp
    bond_id: HexStr
    unlock_at: Timestamp  # from unbondRequest.willUnlock

    def serialize(self) -> Dict[str, Any]:
        return {
            'tx_hash': self.tx_hash,
            'identity_address': self.identity_address,
            'timestamp': self.timestamp,
            'bond_id': self.bond_id,
            'event_type': EventType.UNBOND_REQUEST.pretty_name(),
        }

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            str(self.tx_hash),
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(self.bond_id),
            str(EventType.UNBOND_REQUEST),
            None,  # pool_id
            None,  # amount
            None,  # nonce
            None,  # slashed_at
            int(self.unlock_at),
        )


# Contains the events' (e.g. bond, unbond) common attributes
class EventCoreData(NamedTuple):
    tx_hash: HexStr
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp


class ADXStakingEvents(NamedTuple):
    bonds: List[Bond]
    unbonds: List[Unbond]
    unbond_requests: List[UnbondRequest]


class ADXStakingBalance(NamedTuple):
    pool_id: HexStr
    pool_name: Optional[str]
    balance: Balance
    address: ChecksumAddress  # From staking contract

    def serialize(self) -> Dict[str, Any]:
        return {
            'pool_id': self.pool_id,
            'pool_name': self.pool_name,
            'balance': self.balance.serialize(),
            'address': self.address,
        }


class TomPoolIncentive(NamedTuple):
    total_staked_amount: FVal  # from sum(currentTotalActiveStake)
    total_reward_per_second: FVal  # from sum(currentRewardPerSecond)
    period_ends_at: Timestamp  # from periodEnd
    apr: FVal  # from AdEx APY


class ADXStakingStat(NamedTuple):
    address: ChecksumAddress  # From staking contract
    pool_id: HexStr
    pool_name: Optional[str]
    total_staked_amount: FVal
    apr: FVal
    balance: Balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'pool_id': self.pool_id,
            'pool_name': self.pool_name,
            'total_staked_amount': str(self.total_staked_amount),
            'apr': self.apr.to_percentage(precision=2),
            'balance': self.balance.serialize(),
        }


class ADXStakingHistory(NamedTuple):
    events: List[Union[Bond, Unbond, UnbondRequest]]
    staking_stats: List[ADXStakingStat]

    def serialize(self) -> Dict[str, Any]:
        return {
            'events': [event.serialize() for event in self.events],
            'staking_stats': [stat.serialize() for stat in self.staking_stats],
        }


DeserializationMethod = Callable[..., Union[Bond, Unbond, UnbondRequest]]
