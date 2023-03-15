from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.evm_event import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings

from ..constants import CPT_UNISWAP_V3

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot


class Uniswapv3Accountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, 'TxEventSettings']:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.TRADE, HistoryEventSubType.SPEND, CPT_UNISWAP_V3): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='spend',
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.NFT, CPT_UNISWAP_V3): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='acquisition',
            ),
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_UNISWAP_V3): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='spend',
            ),
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_UNISWAP_V3): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='acquisition',
            ),
        }
