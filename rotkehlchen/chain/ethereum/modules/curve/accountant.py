import logging
from typing import TYPE_CHECKING, Iterator, Literal
from rotkehlchen.accounting.mixins.event import AccountingEventType

from rotkehlchen.accounting.structures.base import HistoryBaseEntry, get_tx_event_type_identifier
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.interfaces import ModuleAccountantInterface
from rotkehlchen.chain.evm.accounting.structures import TxEventSettings
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_CURVE

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class CurveAccountant(ModuleAccountantInterface):
    def _process_deposit_or_withdrawal(
            self,
            pot: 'AccountingPot',  # pylint: disable=unused-argument
            event: HistoryBaseEntry,
            other_events: Iterator[HistoryBaseEntry],  # pylint: disable=unused-argument
    ) -> None:
        """
        Process a deposits and withdrawals from Curve. There are multiple events that we have to
        consume from the iterator.
        """
        method: Literal['acquisition', 'spend']
        if event.event_type == HistoryEventType.RECEIVE:
            # Pool token is received, which means it is a deposit
            events_to_consume = event.extra_data.get('deposit_events_num', None) if event.extra_data is not None else None  # noqa: E501
            method = 'spend'
        else:  # Withdrawal
            events_to_consume = event.extra_data.get('withdrawal_events_num', None) if event.extra_data is not None else None  # noqa: E501
            method = 'acquisition'

        if events_to_consume is None:
            log.debug(
                f'Could not find the number of events to consume for curve deposit/withdrawal'
                f' transaction {event.serialized_event_identifier}',
            )
            return

        # Consume the events
        for _ in range(events_to_consume):
            next_event = next(other_events, None)
            if next_event is None:
                log.debug('Could not find the event to consume for curve deposit/withdrawal')
                return

            if next_event.balance.amount == ZERO:
                continue

            pot.add_asset_change_event(
                method=method,
                event_type=AccountingEventType.TRANSACTION_EVENT,
                notes=next_event.notes if next_event.notes else '',
                location=next_event.location,
                timestamp=next_event.get_timestamp_in_sec(),
                asset=next_event.asset,
                amount=next_event.balance.amount,
                taxable=False,  # Deposits and withdrawals are not taxable
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                extra_data={'tx_hash': next_event.serialized_event_identifier},
            )

    def event_settings(self, pot: 'AccountingPot') -> dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.RETURN_WRAPPED, CPT_CURVE): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                accountant_cb=self._process_deposit_or_withdrawal,
            ),
        }
