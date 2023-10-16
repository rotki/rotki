from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings
from rotkehlchen.chain.evm.decoding.constants import CPT_HOP

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class HopAccountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[int, TxEventSettings]:  # pylint: disable=unused-argument
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.BRIDGE, CPT_HOP): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                accounting_treatment=None,
            ),
        }
