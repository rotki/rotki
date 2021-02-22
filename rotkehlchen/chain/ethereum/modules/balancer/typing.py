from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, NamedTuple, Set, Union

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UNKNOWN_TOKEN_KEYS, UnknownEthereumToken
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress, Price


@dataclass(init=True, repr=True)
class BalancerPoolToken:
    token: Union[EthereumToken, UnknownEthereumToken]
    total_amount: FVal
    user_balance: Balance
    weight: FVal
    usd_price: Price = Price(ZERO)

    def serialize(self) -> Dict:
        serialized_token: Union[str, Dict[str, Any]]
        if isinstance(self.token, EthereumToken):
            serialized_token = self.token.serialize()
        elif isinstance(self.token, UnknownEthereumToken):
            serialized_token = self.token.serialize_as_dict(keys=UNKNOWN_TOKEN_KEYS)
        else:
            raise AssertionError(f'Unexpected type: {type(self.token)}')

        return {
            'token': serialized_token,
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
            'usd_price': self.usd_price,
            'weight': self.weight,
        }


@dataclass(init=True, repr=True)
class BalancerPool:
    address: ChecksumEthAddress
    tokens: List[BalancerPoolToken]
    total_amount: FVal
    user_balance: Balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'tokens': [token.serialize() for token in self.tokens],
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
        }


AddressBalances = Dict[ChecksumEthAddress, List[BalancerPool]]
DDAddressBalances = DefaultDict[ChecksumEthAddress, List[BalancerPool]]
TokenPrices = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_balances: AddressBalances
    known_tokens: Set[EthereumToken]
    unknown_tokens: Set[UnknownEthereumToken]
