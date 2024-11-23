from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.balance import Balance, BalanceType
    from rotkehlchen.fval import FVal


class CompoundBalance(NamedTuple):
    balance_type: 'BalanceType'
    balance: 'Balance'
    apy: 'FVal | None'

    def serialize(self) -> dict[str, str | dict[str, str] | None]:
        return {
            'balance': self.balance.serialize(),
            'apy': self.apy.to_percentage(precision=2) if self.apy else None,
        }
