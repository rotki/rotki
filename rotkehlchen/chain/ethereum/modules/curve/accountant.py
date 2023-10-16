import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import DepositableAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_CURVE

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveAccountant(DepositableAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[int, TxEventSettings]:  # pylint: disable=unused-argument
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
            get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
            get_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
            ),
            get_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
            ),
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=True,
                count_cost_basis_pnl=True,
            ),
            get_event_type_identifier(HistoryEventType.TRADE, HistoryEventSubType.SPEND, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
        }
