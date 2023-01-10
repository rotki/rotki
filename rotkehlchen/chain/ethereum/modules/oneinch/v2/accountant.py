from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings, TxMultitakeTreatment

from ..constants import CPT_ONEINCH_V2

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class Oneinchv2Accountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.TRADE, HistoryEventSubType.SPEND, CPT_ONEINCH_V2): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='spend',
                take=2,
                multitake_treatment=TxMultitakeTreatment.SWAP,
            ),
        }
