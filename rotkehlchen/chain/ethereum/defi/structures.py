from collections.abc import Callable
from typing import Literal, NamedTuple

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.types import ChecksumEvmAddress


class DefiProtocol(NamedTuple):
    name: str
    description: str
    url: str
    version: int

    def serialize(self) -> dict[str, str]:
        return {'name': self.name}


class DefiBalance(NamedTuple):
    token_address: ChecksumEvmAddress
    token_name: str
    token_symbol: str
    balance: Balance


class DefiProtocolBalances(NamedTuple):
    protocol: DefiProtocol
    balance_type: Literal['Asset', 'Debt']
    base_balance: DefiBalance
    underlying_balances: list[DefiBalance]


# Type of the argument given to functions that need the defi balances
GIVEN_DEFI_BALANCES = (
    dict[ChecksumEvmAddress, list[DefiProtocolBalances]] |
    Callable[[], dict[ChecksumEvmAddress, list[DefiProtocolBalances]]]
)

# Type of the argument given to functions that need the eth balances
GIVEN_ETH_BALANCES = (
    dict[ChecksumEvmAddress, BalanceSheet] |
    Callable[[], dict[ChecksumEvmAddress, BalanceSheet]]
)
