from collections import defaultdict
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.accounting.mixins.event import AccountingEventType


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=False, frozen=False)
class PNL:
    free: FVal = ZERO
    taxable: FVal = ZERO

    def serialize(self) -> dict[str, str]:
        return {
            'free_pnl': str(self.free),
            'taxable_pnl': str(self.taxable),
        }

    @property
    def total(self) -> FVal:
        return self.taxable + self.free

    def __str__(self) -> str:
        return f'{self.free}/{self.taxable}'

    def __add__(self, x: Any) -> 'PNL':
        if isinstance(x, PNL):
            return PNL(taxable=self.taxable + x.taxable, free=self.free + x.free)
        if isinstance(x, (FVal, int)):
            return PNL(taxable=self.taxable + x, free=self.free + x)

        raise TypeError(f'Cant add type {type(x)} to PNL')

    __radd__ = __add__

    def __sub__(self, x: Any) -> 'PNL':
        if isinstance(x, PNL):
            return PNL(taxable=self.taxable - x.taxable, free=self.free - x.free)
        if isinstance(x, (FVal, int)):
            return PNL(taxable=self.taxable - x, free=self.free - x)

        raise TypeError(f'Cant sub type {type(x)} from PNL')

    __rsub__ = __sub__

    def __mul__(self, x: Any) -> 'PNL':
        if isinstance(x, PNL):
            return PNL(taxable=self.taxable * x.taxable, free=self.free * x.free)
        if isinstance(x, (FVal, int)):
            return PNL(taxable=self.taxable * x, free=self.free * x)

        raise TypeError(f'Cant mul type {type(x)} with PNL')

    __rmul__ = __mul__


class PnlTotals(MutableMapping):

    def __init__(self, totals: Optional[dict['AccountingEventType', PNL]] = None) -> None:
        self.totals: dict[AccountingEventType, PNL] = defaultdict(PNL)
        if totals is not None:
            for event_type, entry in totals.items():
                self.totals[event_type] = entry

    def reset(self) -> None:
        self.totals = defaultdict(PNL)

    def __repr__(self) -> str:
        result = ','.join(f'{event_type}: {totals}' for event_type, totals in self.totals.items())
        return result

    def __getitem__(self, key: 'AccountingEventType') -> PNL:
        return self.totals[key]

    def __setitem__(self, key: 'AccountingEventType', value: PNL) -> None:
        self.totals[key] = value

    def __delitem__(self, key: 'AccountingEventType') -> None:
        del self.totals[key]

    def __iter__(self) -> Iterator['AccountingEventType']:
        return self.totals.__iter__()

    def __len__(self) -> int:
        return len(self.totals)

    @property
    def taxable(self) -> FVal:
        return FVal(sum(x.taxable for x in self.totals.values()))

    @property
    def free(self) -> FVal:
        return FVal(sum(x.free for x in self.totals.values()))
