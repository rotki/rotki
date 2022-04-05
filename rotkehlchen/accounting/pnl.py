from collections import defaultdict
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional

from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal

if TYPE_CHECKING:
    from rotkehlchen.accounting.mixins.event import AccountingEventType

# The various fields seen in overview and as type in all events
OVR_TRADE_PNL = 'trades_pnl'
OVR_LOAN_PROFIT = 'loan_profit'
OVR_MARGIN_PNL = 'margin_positions_profit_loss'
OVR_LEDGER_ACTIONS_PNL = 'ledger_actions_profit_loss'
OVR_STAKING_PROFIT = 'staking_profit'
OVR_SETTLEMENT_LOSS = 'settlement_loss'
OVR_FEES = 'fees'
OVR_ASSET_MOVEMENTS_FEES = 'asset_movement_fees'
OVR_GAS_FEES = 'ethereum_transaction_gas_fees'
OVR_STAKING = 'ethereum_staking'


@dataclass(init=True, repr=False, eq=True, order=False, unsafe_hash=False, frozen=False)
class PNL():
    free: FVal = ZERO
    taxable: FVal = ZERO

    def serialize(self) -> Dict[str, str]:
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

    def __init__(self, totals: Optional[Dict['AccountingEventType', PNL]] = None) -> None:
        self.totals: Dict['AccountingEventType', PNL] = defaultdict(PNL)
        if totals is not None:
            for event_type, entry in totals.items():
                self.totals[event_type] = entry

    def reset(self) -> None:
        self.totals = defaultdict(PNL)

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

    def get_net_taxable_pnl(self) -> FVal:
        return FVal(sum(self.totals.values()))  # type: ignore
