from dataclasses import dataclass
from enum import Enum

from rotkehlchen.assets.asset import Asset
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
