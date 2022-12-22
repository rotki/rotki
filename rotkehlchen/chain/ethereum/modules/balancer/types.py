from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, DefaultDict, NamedTuple, Optional, Union, cast

from eth_typing.evm import ChecksumAddress

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_timestamp
from rotkehlchen.types import (
    AssetAmount,
    ChecksumEvmAddress,
    EVMTxHash,
    Price,
    Timestamp,
    make_evm_tx_hash,
)
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin

# TODO: improve the prefixes annotation and amend their usage in balancer.py
BALANCER_EVENTS_PREFIX = 'balancer_events'
POOL_MAX_NUMBER_TOKENS = 8


class BalancerV1EventTypes(Enum):
    JOIN = auto()
    EXIT = auto()


@dataclass(init=True, repr=True)
class BalancerPoolTokenBalance:
    token: EvmToken
    total_amount: FVal  # token amount in the pool
    user_balance: Balance  # user token balance
    weight: FVal
    usd_price: Price = Price(ZERO)

    def serialize(self) -> dict:
        return {
            'token': self.token.serialize(),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
            'weight': self.weight,
        }


@dataclass(init=True, repr=True)
class BalancerPoolBalance:
    pool_token: EvmToken
    underlying_tokens_balance: list[BalancerPoolTokenBalance]
    total_amount: FVal  # LP token amount
    user_balance: Balance  # user LP token balance

    def serialize(self) -> dict[str, Any]:

        return {
            'address': self.pool_token.evm_address,
            'tokens': [token.serialize() for token in self.underlying_tokens_balance],
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
        }


AddressToPoolBalances = dict[ChecksumEvmAddress, list[BalancerPoolBalance]]
DDAddressToPoolBalances = DefaultDict[ChecksumEvmAddress, list[BalancerPoolBalance]]
TokenToPrices = dict[ChecksumEvmAddress, Price]


class ProtocolBalance(NamedTuple):
    address_to_pool_balances: AddressToPoolBalances
    known_tokens: set[EvmToken]
    unknown_tokens: set[EvmToken]


class BalancerInvestEventType(SerializableEnumMixin):
    ADD_LIQUIDITY = 1
    REMOVE_LIQUIDITY = 2


class BalancerBPTEventType(SerializableEnumMixin):
    MINT = 1
    BURN = 2


class BalancerInvestEvent(NamedTuple):
    tx_hash: EVMTxHash
    log_index: int
    address: ChecksumEvmAddress
    timestamp: Timestamp
    event_type: BalancerInvestEventType
    pool_address_token: EvmToken
    token_address: ChecksumEvmAddress
    amount: AssetAmount  # added or removed token amount

    def __hash__(self) -> int:
        return hash(self.tx_hash + str(self.log_index).encode())

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)


class BalancerBPTEventPoolToken(NamedTuple):
    token: EvmToken
    weight: FVal

    def serialize(self) -> dict:
        return {
            'token': self.token.serialize(),
            'weight': str(self.weight),
        }


class BalancerBPTEvent(NamedTuple):
    tx_hash: EVMTxHash
    log_index: int
    address: ChecksumEvmAddress
    event_type: BalancerBPTEventType
    pool_address_token: EvmToken
    amount: AssetAmount  # minted or burned BPT amount

    def __hash__(self) -> int:
        return hash(self.tx_hash + str(self.log_index).encode())

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)


class BalancerEventsData(NamedTuple):
    add_liquidities: list[BalancerInvestEvent]
    remove_liquidities: list[BalancerInvestEvent]
    mints: list[BalancerBPTEvent]
    burns: list[BalancerBPTEvent]


AddressToInvestEvents = dict[ChecksumEvmAddress, list[BalancerInvestEvent]]
DDAddressToUniqueInvestEvents = DefaultDict[ChecksumEvmAddress, set[BalancerInvestEvent]]
AddressToBPTEvents = dict[ChecksumEvmAddress, list[BalancerBPTEvent]]
DDAddressToUniqueBPTEvents = DefaultDict[ChecksumEvmAddress, set[BalancerBPTEvent]]
AddressToEventsData = dict[ChecksumAddress, BalancerEventsData]
PoolAddrToTokenAddrToIndex = dict[EvmToken, dict[ChecksumAddress, int]]

BalancerEventDBTuple = (
    tuple[
        bytes,  # tx_hash
        int,  # log_index
        str,  # address
        int,  # timestamp
        str,  # type
        str,  # pool_address_token (identifier)
        str,  # lp_amount
        str,  # usd_value
        str,  # amount0
        str,  # amount1
        Optional[str],  # amount2
        Optional[str],  # amount3
        Optional[str],  # amount4
        Optional[str],  # amount5
        Optional[str],  # amount6
        Optional[str],  # amount7
    ]
)


class BalancerEvent(NamedTuple):
    tx_hash: EVMTxHash
    log_index: int
    address: ChecksumEvmAddress
    timestamp: Timestamp
    event_type: BalancerBPTEventType
    pool_address_token: EvmToken
    lp_balance: Balance
    amounts: list[AssetAmount]

    @classmethod
    def deserialize_from_db(
            cls,
            event_tuple: BalancerEventDBTuple,
    ) -> 'BalancerEvent':
        """May raise DeserializationError

        Event_tuple index - Schema columns
        ----------------------------------
        0 - tx_hash
        1 - log_index
        2 - address
        3 - timestamp
        4 - type
        5 - pool_address_token
        6 - lp_amount
        7 - usd_value
        8 - amount0
        9 - amount1
        10 - amount2
        11 - amount3
        12 - amount4
        13 - amount5
        14 - amount6
        15 - amount7
        """
        event_tuple_type = event_tuple[4]
        try:
            event_type = getattr(BalancerBPTEventType, event_tuple_type.upper())
        except AttributeError as e:
            raise DeserializationError(f'Unexpected event type: {event_tuple_type}.') from e

        try:
            pool_address_token = EvmToken(event_tuple[5])
        except UnknownAsset as e:
            raise DeserializationError(
                f'Balancer event pool token: {event_tuple[5]} not found in the DB.',
            ) from e

        amounts: list[AssetAmount] = [
            deserialize_asset_amount(item)
            for item in event_tuple[8:16]
            if item is not None
        ]
        return cls(
            tx_hash=make_evm_tx_hash(event_tuple[0]),
            log_index=event_tuple[1],
            address=string_to_evm_address(event_tuple[2]),
            timestamp=deserialize_timestamp(event_tuple[3]),
            event_type=event_type,
            pool_address_token=pool_address_token,
            lp_balance=Balance(
                amount=deserialize_asset_amount(event_tuple[6]),
                usd_value=deserialize_price(event_tuple[7]),
            ),
            amounts=amounts,
        )

    def serialize(
            self,
            pool_tokens: Optional[list[UnderlyingToken]] = None,
    ) -> dict[str, Any]:
        amounts: Union[list[str], dict[str, Any]]
        if isinstance(pool_tokens, list) and len(pool_tokens) > 0:
            amounts = {}
            for pool_token, amount in zip(pool_tokens, self.amounts):
                token_identifier = ethaddress_to_identifier(pool_token.address)
                amounts[token_identifier] = str(amount)
        else:
            amounts = [str(amount) for amount in self.amounts]
        return {
            'tx_hash': self.tx_hash.hex(),
            'log_index': self.log_index,
            'timestamp': self.timestamp,
            'event_type': str(self.event_type),
            'lp_balance': self.lp_balance.serialize(),
            'amounts': amounts,
        }

    def to_db_tuple(self) -> BalancerEventDBTuple:
        serialized_for_db_attributes = [
            self.tx_hash,
            self.log_index,
            self.address,
            self.timestamp,
            str(self.event_type),
            self.pool_address_token.serialize(),
            str(self.lp_balance.amount),
            str(self.lp_balance.usd_value),
        ]
        serialized_for_db_attributes.extend([str(amount) for amount in self.amounts])
        serialized_for_db_attributes.extend([None] * (POOL_MAX_NUMBER_TOKENS - len(self.amounts)))
        return cast(BalancerEventDBTuple, tuple(serialized_for_db_attributes))


AddressToEvents = dict[ChecksumAddress, list[BalancerEvent]]
DDAddressToEvents = DefaultDict[EvmToken, list[BalancerEvent]]


class BalancerPoolEventsBalance(NamedTuple):
    address: ChecksumAddress
    pool_address_token: EvmToken
    events: list[BalancerEvent]
    profit_loss_amounts: list[AssetAmount]
    usd_profit_loss: FVal

    def serialize(self) -> dict[str, Any]:
        profit_loss_amounts: dict[str, Any] = {}  # Includes all assets, even with zero amount
        tokens_and_weights = []
        for pool_token, profit_loss_amount in zip(self.pool_address_token.underlying_tokens, self.profit_loss_amounts):  # noqa: E501
            token_identifier = ethaddress_to_identifier(pool_token.address)
            profit_loss_amounts[token_identifier] = str(profit_loss_amount)
            tokens_and_weights.append({
                'token': token_identifier,
                'weight': str(pool_token.weight * 100),
            })

        return {
            'pool_address': self.pool_address_token.evm_address,
            'pool_tokens': tokens_and_weights,
            'events': [event.serialize(pool_tokens=self.pool_address_token.underlying_tokens) for event in self.events],  # noqa: E501
            'profit_loss_amounts': profit_loss_amounts,
            'usd_profit_loss': str(self.usd_profit_loss),
        }


AddressToPoolEventsBalances = dict[ChecksumEvmAddress, list[BalancerPoolEventsBalance]]
DDAddressToProfitLossAmounts = DefaultDict[EvmToken, list[AssetAmount]]
