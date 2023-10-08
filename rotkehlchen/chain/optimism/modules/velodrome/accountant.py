import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.evm_event import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import DepositableAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_VELODROME

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class VelodromeAccountant(DepositableAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, TxEventSettings]:  # pylint: disable=unused-argument
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED, CPT_VELODROME): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_VELODROME): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_VELODROME): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
            ),
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_VELODROME): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
            ),
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, CPT_VELODROME): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=True,
                count_cost_basis_pnl=True,
                method='acquisition',
            ),
            get_tx_event_type_identifier(HistoryEventType.TRADE, HistoryEventSubType.SPEND, CPT_VELODROME): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='spend',
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
        }
