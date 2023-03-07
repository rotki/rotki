import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.base import get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Balancerv2Accountant(ModuleAccountantInterface):

    def event_settings(self, pot: 'AccountingPot') -> dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.TRADE, HistoryEventSubType.SPEND, CPT_BALANCER_V2): TxEventSettings(  # noqa: E501
                taxable=True,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=True,
                method='spend',
                accounting_treatment=TxAccountingTreatment.SWAP,
            ),
        }
