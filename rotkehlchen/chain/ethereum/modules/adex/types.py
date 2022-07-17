from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_typing import ChecksumAddress

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.fval import FVal
from rotkehlchen.types import EVMTxHash, Timestamp

# Pools data
TOM_POOL_ID = '0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28'
POOL_ID_POOL_NAME = {
    TOM_POOL_ID: 'Tom',
}

AdexEventDBTuple = (
    Tuple[
        bytes,  # tx_hash
        str,  # address
        str,  # identity_address
        int,  # timestamp
        str,  # type
        str,  # pool_id
        str,  # amount
        str,  # usd_value
        Optional[str],  # bond_id
        Optional[int],  # nonce
        Optional[int],  # slashed_at
        Optional[int],  # unlock_at
        Optional[str],  # channel_id
        Optional[str],  # token
        Optional[int],  # log_index
    ]
)


class AdexEventType(Enum):
    """Supported events"""
    BOND = 1
    UNBOND = 2
    UNBOND_REQUEST = 3
    CHANNEL_WITHDRAW = 4

    def __str__(self) -> str:
        if self == AdexEventType.BOND:
            return 'deposit'
        if self == AdexEventType.UNBOND:
            return 'withdraw'
        if self == AdexEventType.UNBOND_REQUEST:
            return 'withdraw request'
        if self == AdexEventType.CHANNEL_WITHDRAW:
            return 'claim'
        raise AssertionError(f'Corrupt value {self} for EventType -- Should never happen')


@dataclass(init=True, repr=True)
class AdexEvent:
    tx_hash: EVMTxHash
    address: ChecksumAddress
    identity_address: ChecksumAddress
    timestamp: Timestamp

    def serialize(self) -> Dict[str, Any]:
        return {
            'tx_hash': self.tx_hash.hex(),
            'identity_address': self.identity_address,
            'timestamp': self.timestamp,
        }


@dataclass(init=True, repr=True)
class Bond(AdexEvent):
    bond_id: str
    pool_id: str
    value: Balance
    nonce: int
    slashed_at: Timestamp  # from bond.slashedAtStart

    def serialize(self) -> Dict[str, Any]:
        common_properties = super().serialize()
        common_properties.update({
            'bond_id': self.bond_id,
            'pool_id': self.pool_id,
            'pool_name': POOL_ID_POOL_NAME.get(self.pool_id, None),
            'value': self.value.serialize(),
            'event_type': str(AdexEventType.BOND),
        })
        return common_properties

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            self.tx_hash,
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(AdexEventType.BOND),
            str(self.pool_id),
            str(self.value.amount),
            str(self.value.usd_value),
            str(self.bond_id),
            self.nonce,
            int(self.slashed_at),
            None,  # unlock_at
            None,  # channel_id
            None,  # token
            None,  # log_index
        )

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return 'Adex bond event'


@dataclass(init=True, repr=True)
class Unbond(AdexEvent):
    bond_id: str
    value: Balance  # from bond.amount
    pool_id: str = ''  # from bond.pool_id

    def serialize(self) -> Dict[str, Any]:
        common_properties = super().serialize()
        common_properties.update({
            'bond_id': self.bond_id,
            'pool_id': self.pool_id,
            'pool_name': POOL_ID_POOL_NAME.get(self.pool_id, None),
            'value': self.value.serialize(),
            'event_type': str(AdexEventType.UNBOND),
        })
        return common_properties

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            self.tx_hash,
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(AdexEventType.UNBOND),
            str(self.pool_id),
            str(self.value.amount),
            str(self.value.usd_value),
            str(self.bond_id),
            None,  # nonce
            None,  # slashed_at
            None,  # unlock_at
            None,  # channel_id
            None,  # token
            None,  # log_index
        )

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return 'Adex unbond event'


@dataclass(init=True, repr=True)
class UnbondRequest(AdexEvent):
    bond_id: str
    unlock_at: Timestamp  # from unbondRequest.willUnlock
    value: Balance  # from bond.amount
    pool_id: str = ''  # from bond.pool_id

    def serialize(self) -> Dict[str, Any]:
        common_properties = super().serialize()
        common_properties.update({
            'bond_id': self.bond_id,
            'pool_id': self.pool_id,
            'pool_name': POOL_ID_POOL_NAME.get(self.pool_id, None),
            'value': self.value.serialize(),
            'event_type': str(AdexEventType.UNBOND_REQUEST),
        })
        return common_properties

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            self.tx_hash,
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(AdexEventType.UNBOND_REQUEST),
            str(self.pool_id),
            str(self.value.amount),
            str(self.value.usd_value),
            str(self.bond_id),
            None,  # nonce
            None,  # slashed_at
            int(self.unlock_at),
            None,  # channel_id
            None,  # token
            None,  # log_index
        )

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return 'Adex unbond request'


@dataclass(init=True, repr=True)
class ChannelWithdraw(AdexEvent):
    value: Balance
    channel_id: str
    pool_id: str
    token: EvmToken
    log_index: int

    def serialize(self) -> Dict[str, Any]:
        common_properties = super().serialize()
        common_properties.update({
            'pool_id': self.pool_id,
            'pool_name': POOL_ID_POOL_NAME.get(self.pool_id, None),
            'value': self.value.serialize(),
            'event_type': str(AdexEventType.CHANNEL_WITHDRAW),
            'token': self.token.serialize(),
        })
        return common_properties

    def to_db_tuple(self) -> AdexEventDBTuple:
        return (
            self.tx_hash,
            str(self.address),
            str(self.identity_address),
            int(self.timestamp),
            str(AdexEventType.CHANNEL_WITHDRAW),
            str(self.pool_id),
            str(self.value.amount),
            str(self.value.usd_value),
            None,  # bond_id
            None,  # nonce
            None,  # slashed_at
            None,  # unlocked_at
            str(self.channel_id),
            self.token.serialize(),
            int(self.log_index),
        )

    def __str__(self) -> str:
        """Used in DefiEvent processing during accounting"""
        return 'Adex channel withdraw'


class ADXStakingEvents(NamedTuple):
    bonds: List[Bond]
    unbonds: List[Unbond]
    unbond_requests: List[UnbondRequest]
    channel_withdraws: List[ChannelWithdraw]

    def get_all(self) -> List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]:
        return (
            self.bonds +
            self.unbonds +  # type: ignore # concatenating lists
            self.unbond_requests +  # type: ignore # concatenating lists
            self.channel_withdraws  # type: ignore # concatenating lists
        )


class ADXStakingDetail(NamedTuple):
    contract_address: ChecksumAddress  # From staking contract
    pool_id: str
    pool_name: Optional[str]
    total_staked_amount: FVal
    apr: FVal
    adx_balance: Balance
    adx_unclaimed_balance: Balance
    dai_unclaimed_balance: Balance
    adx_profit_loss: Balance
    dai_profit_loss: Balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'contract_address': self.contract_address,
            'pool_id': self.pool_id,
            'pool_name': self.pool_name,
            'total_staked_amount': str(self.total_staked_amount),
            'apr': self.apr.to_percentage(precision=2),
            'adx_balance': self.adx_balance.serialize(),
            'adx_unclaimed_balance': self.adx_unclaimed_balance.serialize(),
            'dai_unclaimed_balance': self.dai_unclaimed_balance.serialize(),
            'adx_profit_loss': self.adx_profit_loss.serialize(),
            'dai_profit_loss': self.dai_profit_loss.serialize(),
        }


class ADXStakingHistory(NamedTuple):
    events: List[Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]
    staking_details: List[ADXStakingDetail]

    def serialize(self) -> Dict[str, Any]:
        return {
            'events': [event.serialize() for event in self.events],
            'staking_details': [detail.serialize() for detail in self.staking_details],
        }


DeserializationMethod = Callable[..., Union[Bond, Unbond, UnbondRequest, ChannelWithdraw]]
