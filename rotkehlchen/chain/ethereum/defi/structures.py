from typing import Literal, NamedTuple

from rotkehlchen.accounting.structures.balance import Balance
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
