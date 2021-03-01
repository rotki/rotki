from dataclasses import dataclass
from typing import Any, DefaultDict, Dict, List, NamedTuple, Set, Union

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.assets.utils import serialize_ethereum_token
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.typing import ChecksumEthAddress, Price

BALANCER_TRADES_PREFIX: Literal['balancer_trades'] = 'balancer_trades'


@dataclass(init=True, repr=True)
class BalancerPoolToken:
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
class BalancerPool:
    address: ChecksumEthAddress
    tokens: List[BalancerPoolToken]
    total_amount: FVal  # LP token amount
    user_balance: Balance  # user LP token balance

    def serialize(self) -> Dict[str, Any]:
        return {
            'address': self.address,
            'tokens': [token.serialize() for token in self.tokens],
            'total_amount': self.total_amount,
            'user_balance': self.user_balance.serialize(),
        }


AddressToBalances = Dict[ChecksumEthAddress, List[BalancerPool]]
DDAddressToBalances = DefaultDict[ChecksumEthAddress, List[BalancerPool]]
TokenToPrices = Dict[ChecksumEthAddress, Price]


class ProtocolBalance(NamedTuple):
    address_to_balances: AddressToBalances
    known_tokens: Set[EthereumToken]
    unknown_tokens: Set[UnknownEthereumToken]


AddressToSwaps = Dict[ChecksumEthAddress, List[AMMSwap]]
DDAddressToSwaps = DefaultDict[ChecksumEthAddress, List[AMMSwap]]
AddressToTrades = Dict[ChecksumEthAddress, List[AMMTrade]]
