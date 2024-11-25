from rotkehlchen.chain.evm.accounting.interfaces import DepositableAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import EventsAccountantCallback
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V1
from rotkehlchen.history.events.structures.base import get_event_type_identifier
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType


class Balancerv1Accountant(DepositableAccountantInterface):

    def event_callbacks(self) -> dict[int, tuple[int, EventsAccountantCallback]]:
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED, CPT_BALANCER_V1): (-1, self._process_deposit_or_withdrawal),  # noqa: E501
            get_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_BALANCER_V1): (-1, self._process_deposit_or_withdrawal),  # noqa: E501
        }
