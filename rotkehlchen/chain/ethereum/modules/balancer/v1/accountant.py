import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V1
from rotkehlchen.chain.evm.accounting.interfaces import DepositableAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv1Accountant(DepositableAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED, CPT_BALANCER_V1): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_BALANCER_V1): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
        }

    @property
    def name(self) -> str:
        return 'balancer'
