from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, NamedTuple

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChecksumEvmAddress, Price


class BalancerV1EventTypes(Enum):
    JOIN = auto()
    EXIT = auto()


@dataclass(init=True, repr=True)
class BalancerPoolTokenBalance:
    token: EvmToken
    total_amount: FVal  # token amount in the pool
    user_balance: Balance  # user token balance
    weight: FVal
    usd_price: Price = ZERO_PRICE

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
DDAddressToPoolBalances = defaultdict[ChecksumEvmAddress, list[BalancerPoolBalance]]
TokenToPrices = dict[ChecksumEvmAddress, Price]


class ProtocolBalance(NamedTuple):
    address_to_pool_balances: AddressToPoolBalances
    known_tokens: set[EvmToken]
    unknown_tokens: set[EvmToken]
