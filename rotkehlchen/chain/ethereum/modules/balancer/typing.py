from dataclasses import dataclass
from enum import Enum
from typing import Any, DefaultDict, Dict, List, NamedTuple, Optional, Set, Tuple, Union, cast

from eth_typing.evm import ChecksumAddress

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken, UnderlyingToken
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.resolver import ethaddress_to_identifier
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import deserialize_asset_amount, deserialize_timestamp
from rotkehlchen.typing import AssetAmount, ChecksumEthAddress, Price, Timestamp

# TODO: improve the prefixes annotation and amend their usage in balancer.py
BALANCER_EVENTS_PREFIX = 'balancer_events'
BALANCER_TRADES_PREFIX = 'balancer_trades'
POOL_MAX_NUMBER_TOKENS = 8


@dataclass(init=True, repr=True)
class BalancerPoolTokenBalance:
    token: EthereumToken
    total_amount: FVal  # token amount in the pool
    user_balance: Balance  # user token balance
    weight: FVal
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict:
        return {
            'token': self.token.serialize(),
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
            'weight': self.weight,
        }


@dataclass(init=True, repr=True)
class BalancerPoolBalance:
    pool_token: EthereumToken
    underlying_tokens_balance: List[BalancerPoolTokenBalance]
    total_amount: FVal  # LP token amount
    user_balance: Balance  # user LP token balance

    def serialize(self) -> Dict[str, Any]:

        return {
            'address': self.pool_token.ethereum_address,
            'tokens': [token.serialize() for token in self.underlying_tokens_balance],
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
        }


AddressToPoolBalances = Dict[ChecksumEthAddress, List[BalancerPoolBalance]]
DDAddressToPoolBalances = DefaultDict[ChecksumEthAddress, List[BalancerPoolBalance]]
TokenToPrices = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_to_pool_balances: AddressToPoolBalances
    known_tokens: Set[EthereumToken]
    unknown_tokens: Set[EthereumToken]


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
    pool_address_token: EthereumToken
    token_address: ChecksumEthAddress
    amount: AssetAmount  # added or removed token amount

    def __hash__(self) -> int:
        return hash(self.tx_hash + str(self.log_index))

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return False

        return hash(self) == hash(other)


class BalancerBPTEventPoolToken(NamedTuple):
    token: EthereumToken
    weight: FVal

    def serialize(self) -> Dict:
        return {
            'token': self.token.serialize(),
            'weight': str(self.weight),
        }


class BalancerBPTEvent(NamedTuple):
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    event_type: BalancerBPTEventType
    pool_address_token: EthereumToken
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
PoolAddrToTokenAddrToIndex = Dict[EthereumToken, Dict[ChecksumAddress, int]]

BalancerEventDBTuple = (
    Tuple[
        str,  # tx_hash
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
    tx_hash: str
    log_index: int
    address: ChecksumEthAddress
    timestamp: Timestamp
    event_type: BalancerBPTEventType
    pool_address_token: EthereumToken
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

        pool_address_token = EthereumToken.from_identifier(event_tuple[5])
        if pool_address_token is None:
            raise DeserializationError(
                f'Balancer event pool token: {event_tuple[5]} not found in the DB.',
            )

        amounts: List[AssetAmount] = [
            deserialize_asset_amount(item)
            for item in event_tuple[8:16]
            if item is not None
        ]
        return cls(
            tx_hash=event_tuple[0],
            log_index=event_tuple[1],
            address=string_to_ethereum_address(event_tuple[2]),
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
            pool_tokens: Optional[List[UnderlyingToken]] = None,
    ) -> Dict[str, Any]:
        amounts: Union[List[str], Dict[str, Any]]
        if isinstance(pool_tokens, list) and len(pool_tokens) > 0:
            amounts = {}
            for pool_token, amount in zip(pool_tokens, self.amounts):
                token_identifier = ethaddress_to_identifier(pool_token.address)
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
            self.pool_address_token.serialize(),
            str(self.lp_balance.amount),
            str(self.lp_balance.usd_value),
        ]
        serialized_for_db_attributes.extend([str(amount) for amount in self.amounts])
        serialized_for_db_attributes.extend([None] * (POOL_MAX_NUMBER_TOKENS - len(self.amounts)))
        return cast(BalancerEventDBTuple, tuple(serialized_for_db_attributes))


AddressToEvents = Dict[ChecksumAddress, List[BalancerEvent]]
DDAddressToEvents = DefaultDict[EthereumToken, List[BalancerEvent]]


class BalancerPoolEventsBalance(NamedTuple):
    address: ChecksumAddress
    pool_address_token: EthereumToken
    events: List[BalancerEvent]
    profit_loss_amounts: List[AssetAmount]
    usd_profit_loss: FVal

    def serialize(self) -> Dict[str, Any]:
        profit_loss_amounts: Dict[str, Any] = {}  # Includes all assets, even with zero amount
        for pool_token, profit_loss_amount in zip(self.pool_address_token.underlying_tokens, self.profit_loss_amounts):  # noqa: E501
            token_identifier = ethaddress_to_identifier(pool_token.address)
            profit_loss_amounts[token_identifier] = str(profit_loss_amount)

        return {
            'pool_address': self.pool_address_token.ethereum_address,
            'pool_tokens': [
                ethaddress_to_identifier(x.address) for x in self.pool_address_token.underlying_tokens],  # noqa: E501
            'events': [event.serialize(pool_tokens=self.pool_address_token.underlying_tokens) for event in self.events],  # noqa: E501
            'profit_loss_amounts': profit_loss_amounts,
            'usd_profit_loss': str(self.usd_profit_loss),
        }


AddressToPoolEventsBalances = Dict[ChecksumEthAddress, List[BalancerPoolEventsBalance]]
DDAddressToProfitLossAmounts = DefaultDict[EthereumToken, List[AssetAmount]]
