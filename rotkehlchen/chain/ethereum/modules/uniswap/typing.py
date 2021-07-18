import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional, Set, Tuple

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_token_from_db,
    deserialize_timestamp,
)
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Price, Timestamp

log = logging.getLogger(__name__)

UNISWAP_EVENTS_PREFIX = 'uniswap_events'
UNISWAP_TRADES_PREFIX = 'uniswap_trades'

# Get balances


@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    asset: EthereumToken
    total_amount: Optional[FVal]
    user_balance: Balance
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict[str, Any]:
        return {
            'asset': self.asset.serialize(),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
        }


@dataclass(init=True, repr=True)
class LiquidityPool:
    address: ChecksumEthAddress
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


AddressToLPBalances = Dict[ChecksumEthAddress, List[LiquidityPool]]
DDAddressToLPBalances = DefaultDict[ChecksumEthAddress, List[LiquidityPool]]
AssetToPrice = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    """Container structure for uniswap LP balances

    Known assets are all assets we have an oracle for
    Unknown assets are those we would have to try to query through uniswap directly
    """
    address_balances: AddressToLPBalances
    known_assets: Set[EthereumToken]
    unknown_assets: Set[EthereumToken]


AddressTrades = Dict[ChecksumEthAddress, List[AMMTrade]]


class EventType(Enum):
    """Supported events"""
    MINT = 1
    BURN = 2

    def __str__(self) -> str:
        if self == EventType.MINT:
            return 'mint'
        if self == EventType.BURN:
            return 'burn'
        # else
        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')


LiquidityPoolEventDBTuple = (
    Tuple[
        str,  # tx_hash
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
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    timestamp: Timestamp
    event_type: EventType
    pool_address: ChecksumEthAddress
    token0: EthereumToken
    token1: EthereumToken
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
        db_event_type = event_tuple[4]
        if db_event_type not in {str(event_type) for event_type in EventType}:
            raise DeserializationError(
                f'Failed to deserialize event type. Unknown event: {db_event_type}.',
            )

        if db_event_type == str(EventType.MINT):
            event_type = EventType.MINT
        elif db_event_type == str(EventType.BURN):
            event_type = EventType.BURN
        else:
            raise ValueError(f'Unexpected event type case: {db_event_type}.')

        token0 = deserialize_ethereum_token_from_db(identifier=event_tuple[6])
        token1 = deserialize_ethereum_token_from_db(identifier=event_tuple[7])

        return cls(
            tx_hash=event_tuple[0],
            log_index=event_tuple[1],
            address=string_to_ethereum_address(event_tuple[2]),
            timestamp=deserialize_timestamp(event_tuple[3]),
            event_type=event_type,
            pool_address=string_to_ethereum_address(event_tuple[5]),
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
            str(self.event_type),
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
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
            'timestamp': self.timestamp,
            'event_type': str(self.event_type),
            'amount0': str(self.amount0),
            'amount1': str(self.amount1),
            'usd_price': str(self.usd_price),
            'lp_amount': str(self.lp_amount),
        }


class LiquidityPoolEventsBalance(NamedTuple):
    address: ChecksumEthAddress
    pool_address: ChecksumEthAddress
    token0: EthereumToken
    token1: EthereumToken
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


AddressEvents = Dict[ChecksumEthAddress, List[LiquidityPoolEvent]]
DDAddressEvents = DefaultDict[ChecksumEthAddress, List[LiquidityPoolEvent]]
AddressEventsBalances = Dict[ChecksumEthAddress, List[LiquidityPoolEventsBalance]]
