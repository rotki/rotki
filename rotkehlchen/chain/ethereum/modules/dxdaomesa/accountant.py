from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.evm_event import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings

from .constants import CPT_DXDAO_MESA

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class DxdaomesaAccountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, TxEventSettings]:  # pylint: disable=unused-argument
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_DXDAO_MESA): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                accounting_treatment=None,
            ),
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_DXDAO_MESA): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                accounting_treatment=None,
            ),
        }
