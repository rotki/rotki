from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.typing import Timestamp


class DefiEventType(Enum):
    DSR_LOAN_GAIN = 0
    MAKERDAO_VAULT_DEPOSIT = 1
    MAKERDAO_VAULT_WITHDRAWAL = 2
    MAKERDAO_VAULT_LOSS = 3

    def __str__(self) -> str:
        if self == DefiEventType.DSR_LOAN_GAIN:
            return "DSR loan gain"
        elif self == DefiEventType.MAKERDAO_VAULT_DEPOSIT:
            return "Makerdao vault deposit"
        elif self == DefiEventType.MAKERDAO_VAULT_WITHDRAWAL:
            return "Makerdao vault withdrawal"
        elif self == DefiEventType.MAKERDAO_VAULT_LOSS:
            return "Makerdao vault loss"

        raise RuntimeError(f'Corrupt value {self} for DefiEventType -- Should never happen')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DefiEvent:
    timestamp: Timestamp
    event_type: DefiEventType
    asset: Asset
    amount: FVal


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class Balance:
    amount: FVal = ZERO
    usd_value: FVal = ZERO

    def serialize(self) -> Dict[str, str]:
        return {'amount': str(self.amount), 'usd_value': str(self.usd_value)}

    def to_dict(self) -> Dict[str, FVal]:
        return {'amount': self.amount, 'usd_value': self.usd_value}

    def __add__(self, other: Any) -> 'Balance':
        other = _evaluate_balance_input(other, 'addition')
        return Balance(
            amount=self.amount + other.amount,
            usd_value=self.usd_value + other.usd_value,
        )


def _evaluate_balance_input(other: Any, operation: str) -> Balance:
    transformed_input = other
    if isinstance(other, dict):
        if len(other) == 2 and 'amount' in other and 'usd_value' in other:
            try:
                amount = FVal(other['amount'])
                usd_value = FVal(other['usd_value'])
            except ValueError:
                raise InputError(
                    f'Found valid dict object but with invalid values during Balance {operation}',
                )
            transformed_input = Balance(amount=amount, usd_value=usd_value)
        else:
            raise InputError(f'Found invalid dict object during Balance {operation}')
    elif not isinstance(other, Balance):
        raise InputError(f'Found a {type(other)} object during Balance {operation}')

    return transformed_input
