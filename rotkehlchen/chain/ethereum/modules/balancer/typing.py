from dataclasses import dataclass
from enum import Enum
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional, Set, Tuple, Union, cast

from eth_typing.evm import ChecksumAddress

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.assets.utils import serialize_ethereum_token
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
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

# TODO: improve the prefixes annotation and amend their usage in balancer.py
BALANCER_EVENTS_PREFIX = 'balancer_events'
BALANCER_TRADES_PREFIX = 'balancer_trades'
POOL_MAX_NUMBER_TOKENS = 8
DB_TOKEN_NUMBER_COLUMNS = 6
NONE_TOKEN_SERIALIZED_FOR_DB = [None] * DB_TOKEN_NUMBER_COLUMNS


@dataclass(init=True, repr=True)
class BalancerPoolTokenBalance:
    token: Union[EthereumToken, UnknownEthereumToken]
    total_amount: FVal  # token amount in the pool
    user_balance: Balance  # user token balance
    weight: FVal
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict:
        return {
            'token': serialize_ethereum_token(self.token),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
            'weight': self.weight,
        }


@dataclass(init=True, repr=True)
class BalancerPoolBalance:
    address: ChecksumEthAddress
    tokens: List[BalancerPoolTokenBalance]
    total_amount: FVal  # LP token amount
    user_balance: Balance  # user LP token balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'tokens': [token.serialize() for token in self.tokens],
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
        }


AddressToPoolBalances = Dict[ChecksumEthAddress, List[BalancerPoolBalance]]
DDAddressToPoolBalances = DefaultDict[ChecksumEthAddress, List[BalancerPoolBalance]]
TokenToPrices = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_to_pool_balances: AddressToPoolBalances
    known_tokens: Set[EthereumToken]
    unknown_tokens: Set[UnknownEthereumToken]


AddressToSwaps = Dict[ChecksumEthAddress, List[AMMSwap]]
DDAddressToUniqueSwaps = DefaultDict[ChecksumEthAddress, Set[AMMSwap]]
AddressToTrades = Dict[ChecksumEthAddress, List[AMMTrade]]


class BalancerInvestEventType(Enum):
    ADD_LIQUIDITY = 1
    REMOVE_LIQUIDITY = 2

    def __str__(self) -> str:
        if self == BalancerInvestEventType.ADD_LIQUIDITY:
            return 'add liquidity'
        if self == BalancerInvestEventType.REMOVE_LIQUIDITY:
            return 'remove liquidity'
        raise AssertionError(f'Unexpected BalancerEventType type: {self}.')


class BalancerBPTEventType(Enum):
    MINT = 1
    BURN = 2

    def __str__(self) -> str:
        if self == BalancerBPTEventType.MINT:
            return 'mint'
        if self == BalancerBPTEventType.BURN:
            return 'burn'
        raise AssertionError(f'Unexpected BalancerBPTEventType type: {self}.')


class BalancerInvestEvent(NamedTuple):
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    timestamp: Timestamp
    event_type: BalancerInvestEventType
    pool_address: ChecksumEthAddress
    token_address: ChecksumEthAddress
    amount: AssetAmount  # added or removed token amount

    def __hash__(self) -> int:
        return hash(self.tx_hash + str(self.log_index))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)


class BalancerBPTEventPoolToken(NamedTuple):
    token: Union[EthereumToken, UnknownEthereumToken]
    weight: FVal

    def serialize(self) -> Dict:
        return {
            'token': serialize_ethereum_token(self.token),
            'weight': str(self.weight),
        }


class BalancerBPTEvent(NamedTuple):
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    event_type: BalancerBPTEventType
    pool_address: ChecksumEthAddress
    pool_tokens: List[BalancerBPTEventPoolToken]
    amount: AssetAmount  # minted or burned BPT amount

    def __hash__(self) -> int:
        return hash(self.tx_hash + str(self.log_index))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)


class BalancerEventsData(NamedTuple):
    add_liquidities: List[BalancerInvestEvent]
    remove_liquidities: List[BalancerInvestEvent]
    mints: List[BalancerBPTEvent]
    burns: List[BalancerBPTEvent]


AddressToInvestEvents = Dict[ChecksumEthAddress, List[BalancerInvestEvent]]
DDAddressToUniqueInvestEvents = DefaultDict[ChecksumEthAddress, Set[BalancerInvestEvent]]
AddressToBPTEvents = Dict[ChecksumEthAddress, List[BalancerBPTEvent]]
DDAddressToUniqueBPTEvents = DefaultDict[ChecksumEthAddress, Set[BalancerBPTEvent]]
AddressToEventsData = Dict[ChecksumAddress, BalancerEventsData]
PoolAddrToTokenAddrToIndex = Dict[ChecksumAddress, Dict[ChecksumAddress, int]]

BalancerEventDBTuple = (
    Tuple[
        str,  # tx_hash
        int,  # log_index
        str,  # address
        int,  # timestamp
        str,  # type
        str,  # pool_address
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
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    timestamp: Timestamp
    event_type: BalancerBPTEventType
    pool_address: ChecksumEthAddress
    lp_balance: Balance
    amounts: List[AssetAmount]

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
        5 - pool_address
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

        amounts: List[AssetAmount] = [
            deserialize_asset_amount(item)
            for item in event_tuple[8:16]
            if item is not None
        ]
        return cls(
            tx_hash=event_tuple[0],
            log_index=event_tuple[1],
            address=deserialize_ethereum_address(event_tuple[2]),
            timestamp=deserialize_timestamp(event_tuple[3]),
            event_type=event_type,
            pool_address=deserialize_ethereum_address(event_tuple[5]),
            lp_balance=Balance(
                amount=deserialize_asset_amount(event_tuple[6]),
                usd_value=deserialize_price(event_tuple[7]),
            ),
            amounts=amounts,
        )

    def serialize(
            self,
            pool_tokens: Optional[List[BalancerBPTEventPoolToken]] = None,
    ) -> Dict[str, Any]:
        amounts: Union[List[str], Dict[str, Any]]
        if isinstance(pool_tokens, list) and len(pool_tokens) > 0:
            amounts = {}
            for pool_token, amount in zip(pool_tokens, self.amounts):
                token_identifier = pool_token.token.identifier
                amounts[token_identifier] = str(amount)
        else:
            amounts = [str(amount) for amount in self.amounts]

        return {
            'tx_hash': self.tx_hash,
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
            self.pool_address,
            str(self.lp_balance.amount),
            str(self.lp_balance.usd_value),
        ]
        serialized_for_db_attributes.extend([str(amount) for amount in self.amounts])
        serialized_for_db_attributes.extend([None] * (POOL_MAX_NUMBER_TOKENS - len(self.amounts)))
        return cast(BalancerEventDBTuple, tuple(serialized_for_db_attributes))


AddressToEvents = Dict[ChecksumAddress, List[BalancerEvent]]
DDAddressToEvents = DefaultDict[ChecksumEthAddress, List[BalancerEvent]]

BalancerEventPoolDBTuple = (
    Tuple[
        str,  # address
        int,  # tokens_number
        int,  # is_token0_unknown
        str,  # token0_address
        str,  # token0_symbol
        Optional[str],  # token0_name
        Optional[int],  # token0_decimals
        str,  # token0_weight
        int,  # is_token1_unknown
        str,  # token1_address
        str,  # token1_symbol
        Optional[str],  # token1_name
        Optional[int],  # token1_decimals
        str,  # token1_weight
        Optional[int],  # is_token2_unknown
        Optional[str],  # token2_address
        Optional[str],  # token2_symbol
        Optional[str],  # token2_name
        Optional[int],  # token2_decimals
        Optional[str],  # token2_weight
        Optional[int],  # is_token3_unknown
        Optional[str],  # token3_address
        Optional[str],  # token3_symbol
        Optional[str],  # token3_name
        Optional[int],  # token3_decimals
        Optional[str],  # token3_weight
        Optional[int],  # is_token4_unknown
        Optional[str],  # token4_address
        Optional[str],  # token4_symbol
        Optional[str],  # token4_name
        Optional[int],  # token4_decimals
        Optional[str],  # token4_weight
        Optional[int],  # is_token5_unknown
        Optional[str],  # token5_address
        Optional[str],  # token5_symbol
        Optional[str],  # token5_name
        Optional[int],  # token5_decimals
        Optional[str],  # token5_weight
        Optional[int],  # is_token6_unknown
        Optional[str],  # token6_address
        Optional[str],  # token6_symbol
        Optional[str],  # token6_name
        Optional[int],  # token6_decimals
        Optional[str],  # token6_weight
        Optional[int],  # is_token7_unknown
        Optional[str],  # token7_address
        Optional[str],  # token7_symbol
        Optional[str],  # token7_name
        Optional[int],  # token7_decimals
        Optional[str],  # token7_weight
    ]
)


class BalancerEventPool(NamedTuple):
    address: ChecksumAddress
    tokens: List[BalancerBPTEventPoolToken]

    def __hash__(self) -> int:
        return hash(self.address)

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)

    @classmethod
    def deserialize_from_db(
            cls,
            pool_tuple: BalancerEventPoolDBTuple,
    ) -> 'BalancerEventPool':
        """May raise DeserializationError

        Event_tuple index - Schema columns
        ----------------------------------
        0 - address
        1 - tokens_number
        2 - is_token0_unknown
        3 - token0_address
        4 - token0_symbol
        5 - token0_name
        6 - token0_decimals
        7 - token0_weight

        ...token columns are repeated for token 0 to 7

        44 - is_token7_unknown
        45 - token7_address
        46 - token7_symbol
        47 - token7_name
        48 - token7_decimals
        49 - token7_weight
        """
        address = deserialize_ethereum_address(pool_tuple[0])
        tokens_number = pool_tuple[1]
        pool_tokens: List[BalancerBPTEventPoolToken] = []
        # Deserialize only existing tokens (not null) using `tokens_number`
        for idx in range(tokens_number):
            idx_start = 2 + idx * DB_TOKEN_NUMBER_COLUMNS
            idx_stop = idx_start + DB_TOKEN_NUMBER_COLUMNS
            (
                is_token_unknown,
                token_address,
                token_symbol,
                token_name,
                token_decimals,
                token_weight,
            ) = pool_tuple[idx_start:idx_stop]

            token: Union[EthereumToken, UnknownEthereumToken]
            if not is_token_unknown:
                token = deserialize_ethereum_token_from_db(identifier=cast(str, token_symbol))
            else:
                token = deserialize_unknown_ethereum_token_from_db(
                    ethereum_address=cast(str, token_address),
                    symbol=cast(str, token_symbol),
                    name=None if token_name is None else cast(str, token_name),
                    decimals=None if token_decimals is None else cast(int, token_decimals),
                )
            pool_token = BalancerBPTEventPoolToken(
                token=token,
                weight=deserialize_asset_amount(cast(str, token_weight)),
            )
            pool_tokens.append(pool_token)

        return cls(address=address, tokens=pool_tokens)

    def to_db_tuple(self) -> BalancerEventPoolDBTuple:
        tokens_number = len(self.tokens)
        serialized_for_db_attributes = [self.address, tokens_number]
        for pool_token in self.tokens:
            token = pool_token.token
            if isinstance(token, EthereumToken):
                is_token_unknown = 0
            elif isinstance(token, UnknownEthereumToken):
                is_token_unknown = 1
            else:
                raise AssertionError(f'Unexpected token type: {type(token)}.')

            serialized_for_db_attributes.extend([
                is_token_unknown,
                token.ethereum_address,
                token.symbol,
                token.name,
                token.decimals,
                str(pool_token.weight),
            ])
        serialized_for_db_none_tokens = (
            NONE_TOKEN_SERIALIZED_FOR_DB * (POOL_MAX_NUMBER_TOKENS - tokens_number)
        )
        serialized_for_db_attributes.extend(serialized_for_db_none_tokens)
        return cast(BalancerEventPoolDBTuple, tuple(serialized_for_db_attributes))


class BalancerAggregatedEventsData(NamedTuple):
    balancer_pools: List[BalancerEventPool]
    balancer_events: List[BalancerEvent]


class BalancerPoolEventsBalance(NamedTuple):
    address: ChecksumAddress
    pool_address: ChecksumAddress
    pool_tokens: List[BalancerBPTEventPoolToken]
    events: List[BalancerEvent]
    profit_loss_amounts: List[AssetAmount]
    usd_profit_loss: FVal

    def serialize(self) -> Dict[str, Any]:
        profit_loss_amounts: Dict[str, Any] = {}  # Includes all assets, even with zero amount
        for pool_token, profit_loss_amount in zip(self.pool_tokens, self.profit_loss_amounts):
            token_identifier = pool_token.token.identifier
            profit_loss_amounts[token_identifier] = str(profit_loss_amount)

        return {
            'pool_address': self.pool_address,
            'pool_tokens': [pool_token.serialize() for pool_token in self.pool_tokens],
            'events': [event.serialize(pool_tokens=self.pool_tokens) for event in self.events],
            'profit_loss_amounts': profit_loss_amounts,
            'usd_profit_loss': str(self.usd_profit_loss),
        }


AddressToEventPool = Dict[ChecksumAddress, BalancerEventPool]
AddressToPoolEventsBalances = Dict[ChecksumEthAddress, List[BalancerPoolEventsBalance]]
DDAddressToProfitLossAmounts = DefaultDict[ChecksumEthAddress, List[AssetAmount]]
