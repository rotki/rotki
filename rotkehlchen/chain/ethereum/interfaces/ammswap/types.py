import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional, Set, Tuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_token_from_db,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    AssetAmount,
    ChecksumEvmAddress,
    EVMTxHash,
    Price,
    Timestamp,
    make_evm_tx_hash,
)

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Get balances
@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    token: EvmToken
    total_amount: Optional[FVal]
    user_balance: Balance
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict[str, Any]:
        return {
            'asset': self.token.serialize(),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
        }


@dataclass(init=True, repr=True)
class LiquidityPool:
    address: ChecksumEvmAddress
    assets: List[LiquidityPoolAsset]
    total_supply: Optional[FVal]
    user_balance: Balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'assets': [asset.serialize() for asset in self.assets],
            'total_supply': self.total_supply,
            'user_balance': self.user_balance.serialize(),
        }


AddressToLPBalances = Dict[ChecksumEvmAddress, List[LiquidityPool]]
DDAddressToLPBalances = DefaultDict[ChecksumEvmAddress, List[LiquidityPool]]
AssetToPrice = Dict[ChecksumEvmAddress, Price]


class ProtocolBalance(NamedTuple):
    """Container structure for uniswap LP balances

    Known assets are all assets we have an oracle for
    Unknown assets are those we would have to try to query through uniswap directly
    """
    address_balances: AddressToLPBalances
    known_assets: Set[EvmToken]
    unknown_assets: Set[EvmToken]


class EventType(Enum):
    """Supported events"""
    MINT_UNISWAP = 1
    BURN_UNISWAP = 2
    MINT_SUSHISWAP = 3
    BURN_SUSHISWAP = 4

    def serialize_for_db(self) -> str:
        if self == EventType.MINT_UNISWAP:
            return 'mint'
        if self == EventType.BURN_UNISWAP:
            return 'burn'
        if self == EventType.MINT_SUSHISWAP:
            return 'mint sushiswap'
        if self == EventType.BURN_SUSHISWAP:
            return 'burn sushiswap'
        # else
        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')

    @classmethod
    def deserialize_from_db(
            cls,
            value: str,
    ) -> 'EventType':
        """May raise DeserializationError if anything is wrong"""
        if value == 'mint':
            return EventType.MINT_UNISWAP
        if value == 'burn':
            return EventType.BURN_UNISWAP
        if value == 'mint sushiswap':
            return EventType.MINT_SUSHISWAP
        if value == 'burn sushiswap':
            return EventType.BURN_SUSHISWAP

        raise DeserializationError(f'Unexpected value {value} at AMM EventType deserialization')

    def __str__(self) -> str:
        if self in (EventType.MINT_UNISWAP, EventType.MINT_SUSHISWAP):
            return 'mint'
        if self in (EventType.BURN_UNISWAP, EventType.BURN_SUSHISWAP):
            return 'burn'

        # else
        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')


LiquidityPoolEventDBTuple = (
    Tuple[
        bytes,  # tx_hash
        int,  # log_index
        str,  # address
        int,  # timestamp
        str,  # event_type
        str,  # pool_address
        str,  # token0_identifier
        str,  # token1_identifier
        str,  # amount0
        str,  # amount1
        str,  # usd_price
        str,  # lp_amount
    ]
)


class LiquidityPoolEvent(NamedTuple):
    tx_hash: EVMTxHash
    log_index: int
    address: ChecksumEvmAddress
    timestamp: Timestamp
    event_type: EventType
    pool_address: ChecksumEvmAddress
    token0: EvmToken
    token1: EvmToken
    amount0: AssetAmount
    amount1: AssetAmount
    usd_price: Price
    lp_amount: AssetAmount

    @classmethod
    def deserialize_from_db(
            cls,
            event_tuple: LiquidityPoolEventDBTuple,
    ) -> 'LiquidityPoolEvent':
        """Turns a tuple read from DB into an appropriate LiquidityPoolEvent.
        May raise a DeserializationError if something is wrong with the DB data
        Event_tuple index - Schema columns
        ----------------------------------
        0 - tx_hash
        1 - log_index
        2 - address
        3 - timestamp
        4 - type
        5 - pool_address
        6 - token0_identifier
        7 - token1_identifier
        8 - amount0
        9 - amount1
        10 - usd_price
        11 - lp_amount
        """
        event_type = EventType.deserialize_from_db(event_tuple[4])
        token0 = deserialize_ethereum_token_from_db(identifier=event_tuple[6])
        token1 = deserialize_ethereum_token_from_db(identifier=event_tuple[7])
        tx_hash = make_evm_tx_hash(event_tuple[0])

        return cls(
            tx_hash=tx_hash,
            log_index=event_tuple[1],
            address=string_to_evm_address(event_tuple[2]),
            timestamp=deserialize_timestamp(event_tuple[3]),
            event_type=event_type,
            pool_address=string_to_evm_address(event_tuple[5]),
            token0=token0,
            token1=token1,
            amount0=deserialize_asset_amount(event_tuple[8]),
            amount1=deserialize_asset_amount(event_tuple[9]),
            usd_price=deserialize_price(event_tuple[10]),
            lp_amount=deserialize_asset_amount(event_tuple[11]),
        )

    def to_db_tuple(self) -> LiquidityPoolEventDBTuple:
        db_tuple = (
            self.tx_hash,
            self.log_index,
            str(self.address),
            int(self.timestamp),
            self.event_type.serialize_for_db(),
            str(self.pool_address),
            self.token0.identifier,
            self.token1.identifier,
            str(self.amount0),
            str(self.amount1),
            str(self.usd_price),
            str(self.lp_amount),
        )
        return db_tuple

    def serialize(self) -> Dict[str, Any]:
        return {
            'tx_hash': self.tx_hash.hex(),
            'log_index': self.log_index,
            'timestamp': self.timestamp,
            'event_type': str(self.event_type),
            'amount0': str(self.amount0),
            'amount1': str(self.amount1),
            'usd_price': str(self.usd_price),
            'lp_amount': str(self.lp_amount),
        }


class LiquidityPoolEventsBalance(NamedTuple):
    address: ChecksumEvmAddress
    pool_address: ChecksumEvmAddress
    token0: EvmToken
    token1: EvmToken
    events: List[LiquidityPoolEvent]
    profit_loss0: FVal
    profit_loss1: FVal
    usd_profit_loss: FVal

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'pool_address': self.pool_address,
            'token0': self.token0.serialize(),
            'token1': self.token1.serialize(),
            'events': [event.serialize() for event in self.events],
            'profit_loss0': str(self.profit_loss0),
            'profit_loss1': str(self.profit_loss1),
            'usd_profit_loss': str(self.usd_profit_loss),
        }


@dataclass(init=True, repr=True)
class AggregatedAmount:
    events: List[LiquidityPoolEvent] = field(default_factory=list)
    profit_loss0: FVal = ZERO
    profit_loss1: FVal = ZERO
    usd_profit_loss: FVal = ZERO


AddressEvents = Dict[ChecksumEvmAddress, List[LiquidityPoolEvent]]
DDAddressEvents = DefaultDict[ChecksumEvmAddress, List[LiquidityPoolEvent]]
AddressEventsBalances = Dict[ChecksumEvmAddress, List[LiquidityPoolEventsBalance]]
