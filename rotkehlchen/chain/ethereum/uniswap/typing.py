import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional, Set, Tuple, Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.chain.ethereum.trades import AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_ethereum_address,
    deserialize_ethereum_token_from_db,
    deserialize_price,
    deserialize_timestamp,
    deserialize_unknown_ethereum_token_from_db,
)
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Price, Timestamp

log = logging.getLogger(__name__)

SWAP_FEE = FVal('0.003')  # 0.3% fee for swapping tokens
UNISWAP_EVENTS_PREFIX = 'uniswap_events'
UNISWAP_TRADES_PREFIX = 'uniswap_trades'

# Get balances


@dataclass(init=True, repr=True)
class LiquidityPoolAsset:
    asset: Union[EthereumToken, UnknownEthereumToken]
    total_amount: Optional[FVal]
    user_balance: Balance
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict[str, Any]:
        serialized_asset: Union[str, Dict[str, Any]]

        if isinstance(self.asset, EthereumToken):
            serialized_asset = self.asset.serialize()
        elif isinstance(self.asset, UnknownEthereumToken):
            unknown_asset_keys = ('ethereum_address', 'name', 'symbol')
            serialized_asset = self.asset.serialize_as_dict(keys=unknown_asset_keys)
        else:
            raise AssertionError(
                f'Got type {type(self.asset)} for a LiquidityPool Asset. '
                f'This should never happen.',
            )

        return {
            'asset': serialized_asset,
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


AddressBalances = Dict[ChecksumEthAddress, List[LiquidityPool]]
DDAddressBalances = DefaultDict[ChecksumEthAddress, List[LiquidityPool]]
AssetPrice = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_balances: AddressBalances
    known_assets: Set[EthereumToken]
    unknown_assets: Set[UnknownEthereumToken]


# Get trades history

AddressTrades = Dict[ChecksumEthAddress, List[AMMTrade]]
ProtocolHistory = Dict[str, Union[AddressTrades]]


# Get events history


class EventType(Enum):
    """Supported Locations"""
    MINT = 1
    BURN = 2

    def __str__(self) -> str:
        if self == EventType.MINT:
            return 'mint'
        elif self == EventType.BURN:
            return 'burn'

        raise RuntimeError(f'Corrupt value {self} for EventType -- Should never happen')

    @classmethod
    def deserialize_from_db(cls, symbol: str) -> 'EventType':
        if not isinstance(symbol, str):
            raise DeserializationError(
                f'Failed to deserialize event type symbol. '
                f'Unsupported entry type: {type(symbol)}.',
            )

        if symbol == 'A':
            return cls.MINT
        elif symbol == 'B':
            return cls.BURN
        else:
            raise DeserializationError(
                f'Failed to deserialize event type symbol. '
                f'Unknown symbol: {symbol}.',
            )

    def serialize_for_db(self) -> str:
        if self == EventType.MINT:
            return 'A'
        elif self == EventType.BURN:
            return 'B'

        raise RuntimeError(f'Corrupt value {self} for EventType. Should never happen.')


LiquidityPoolEventDBTuple = (
    Tuple[
        str,  # tx_hash
        int,  # log_index
        str,  # address
        int,  # timestamp
        str,  # event_type
        str,  # pool_address
        int,  # is_token0_unknown
        str,  # token0_address
        str,  # token0_symbol
        str,  # token0_name
        int,  # token0_decimals
        int,  # is_token1_unknown
        str,  # token1_address
        str,  # token1_symbol
        str,  # token1_name
        int,  # token1_decimals
        str,  # amount0
        str,  # amount1
        str,  # usd_price
        str,  # lp_amount
    ]
)
SerializeAsDictKeys = Union[List[str], Tuple[str, ...], Set[str]]


class LiquidityPoolEvent(NamedTuple):
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    timestamp: Timestamp
    event_type: EventType
    pool_address: ChecksumEthAddress
    token0: Union[EthereumToken, UnknownEthereumToken]
    token1: Union[EthereumToken, UnknownEthereumToken]
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
        6 - is_token0_unknown
        7 - token0_address
        8 - token0_symbol
        9 - token0_name
        10 - token0_decimals
        11 - is_token1_unknown
        12 - token1_address
        13 - token1_symbol
        14 - token1_name
        15 - token1_decimals
        16 - amount0
        17 - amount1
        18 - usd_price
        19 - lp_amount
        """
        is_token0_unknown = event_tuple[6]
        is_token1_unknown = event_tuple[11]

        token0: Union[EthereumToken, UnknownEthereumToken]
        token1: Union[EthereumToken, UnknownEthereumToken]
        if is_token0_unknown:
            token0 = deserialize_unknown_ethereum_token_from_db(
                ethereum_address=event_tuple[7],
                symbol=event_tuple[8],
                name=event_tuple[9],
                decimals=event_tuple[10],
            )
        else:
            token0 = deserialize_ethereum_token_from_db(identifier=event_tuple[8])

        if is_token1_unknown:
            token1 = deserialize_unknown_ethereum_token_from_db(
                ethereum_address=event_tuple[12],
                symbol=event_tuple[13],
                name=event_tuple[14],
                decimals=event_tuple[15],
            )
        else:
            token1 = deserialize_ethereum_token_from_db(identifier=event_tuple[13])

        return cls(
            tx_hash=event_tuple[0],
            log_index=event_tuple[1],
            address=deserialize_ethereum_address(event_tuple[2]),
            timestamp=deserialize_timestamp(event_tuple[3]),
            event_type=EventType.deserialize_from_db(event_tuple[4]),
            pool_address=deserialize_ethereum_address(event_tuple[5]),
            token0=token0,
            token1=token1,
            amount0=deserialize_asset_amount(event_tuple[16]),
            amount1=deserialize_asset_amount(event_tuple[17]),
            usd_price=deserialize_price(event_tuple[18]),
            lp_amount=deserialize_asset_amount(event_tuple[19]),
        )

    def to_db_tuple(self) -> LiquidityPoolEventDBTuple:
        is_token0_unknown = (
            1 if isinstance(self.token0, UnknownEthereumToken) else 0
        )
        is_token1_unknown = (
            1 if isinstance(self.token1, UnknownEthereumToken) else 0
        )
        db_tuple = (
            self.tx_hash,
            self.log_index,
            str(self.address),
            int(self.timestamp),
            self.event_type.serialize_for_db(),
            str(self.pool_address),
            is_token0_unknown,
            str(self.token0.ethereum_address),
            str(self.token0.symbol),
            str(self.token0.name),
            self.token0.decimals,
            is_token1_unknown,
            str(self.token1.ethereum_address),
            str(self.token1.symbol),
            str(self.token1.name),
            self.token1.decimals,
            str(self.amount0),
            str(self.amount1),
            str(self.usd_price),
            str(self.lp_amount),
        )
        return db_tuple  # type: ignore

    def serialize(self) -> Dict[str, Any]:
        unknown_token_keys = ('ethereum_address', 'name', 'symbol')
        serialized_token0 = (
            self.token0.serialize()
            if isinstance(self.token0, EthereumToken)
            else self.token0.serialize_as_dict(keys=unknown_token_keys)
        )
        serialized_token1 = (
            self.token1.serialize()
            if isinstance(self.token1, EthereumToken)
            else self.token1.serialize_as_dict(keys=unknown_token_keys)
        )
        return {
            'tx_hash': self.tx_hash,
            'log_index': self.log_index,
            'address': self.address,
            'timestamp': self.timestamp,
            'event_type': str(self.event_type),
            'pool_address': self.pool_address,
            'token0': serialized_token0,
            'token1': serialized_token1,
            'amount0': str(self.amount0),
            'amount1': str(self.amount1),
            'usd_price': str(self.usd_price),
            'lp_amount': str(self.lp_amount),
        }

    def serialize_for_event_balance(self) -> Dict[str, Any]:
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
    token0: Union[EthereumToken, UnknownEthereumToken]
    token1: Union[EthereumToken, UnknownEthereumToken]
    events: List[LiquidityPoolEvent]
    profit_loss0: FVal
    profit_loss1: FVal
    usd_profit_loss: FVal
    lp_profit_loss: FVal

    def serialize(self) -> Dict[str, Any]:
        unknown_token_keys = ('ethereum_address', 'name', 'symbol')
        serialized_token0 = (
            self.token0.serialize()
            if isinstance(self.token0, EthereumToken)
            else self.token0.serialize_as_dict(keys=unknown_token_keys)
        )
        serialized_token1 = (
            self.token1.serialize()
            if isinstance(self.token1, EthereumToken)
            else self.token1.serialize_as_dict(keys=unknown_token_keys)
        )
        return {
            'address': self.address,
            'pool_address': self.pool_address,
            'token0': serialized_token0,
            'token1': serialized_token1,
            'events': [event.serialize_for_event_balance() for event in self.events],
            'profit_loss0': str(self.profit_loss0),
            'profit_loss1': str(self.profit_loss1),
            'usd_profit_loss': str(self.usd_profit_loss),
            'lp_profit_loss': str(self.lp_profit_loss),
        }


AddressEvents = Dict[ChecksumEthAddress, List[LiquidityPoolEvent]]
DDAddressEvents = DefaultDict[ChecksumEthAddress, List[LiquidityPoolEvent]]
AddressEventsBalances = Dict[ChecksumEthAddress, List[LiquidityPoolEventsBalance]]
