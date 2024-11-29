from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.accounting.interfaces import DepositableAccountantInterface
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.history.events.structures.base import get_event_type_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.accounting.structures import EventsAccountantCallback


class AuraFinanceAccountant(DepositableAccountantInterface):
    def event_callbacks(self) -> dict[int, tuple[int, 'EventsAccountantCallback']]:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED, CPT_AURA_FINANCE): (-1, self._process_deposit_or_withdrawal),  # noqa: E501
            get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_AURA_FINANCE): (-1, self._process_deposit_or_withdrawal),  # noqa: E501
        }
