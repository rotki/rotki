from typing import Callable, Dict, List, NamedTuple, Union

from typing_extensions import Literal

from rotkehlchen.accounting.structures import Balance, BalanceSheet
from rotkehlchen.typing import ChecksumEthAddress


class DefiProtocol(NamedTuple):
    name: str
    description: str
    url: str
    version: int

    def serialize(self) -> Dict[str, str]:
        return {'name': self.name}


class DefiBalance(NamedTuple):
    token_address: ChecksumEthAddress
    token_name: str
    token_symbol: str
    balance: Balance


class DefiProtocolBalances(NamedTuple):
    protocol: DefiProtocol
    balance_type: Literal['Asset', 'Debt']
    base_balance: DefiBalance
    underlying_balances: List[DefiBalance]


# Type of the argument given to functions that need the defi balances
GIVEN_DEFI_BALANCES = Union[
    Dict[ChecksumEthAddress, List[DefiProtocolBalances]],
    Callable[[], Dict[ChecksumEthAddress, List[DefiProtocolBalances]]],
]

# Type of the argument given to functions that need the eth balances
GIVEN_ETH_BALANCES = Union[
    Dict[ChecksumEthAddress, BalanceSheet],
    Callable[[], Dict[ChecksumEthAddress, BalanceSheet]],
]
