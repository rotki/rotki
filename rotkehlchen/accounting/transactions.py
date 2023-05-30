import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Union

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment, TxEventSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def evm_events_iterator(
        events_iterator: Iterator[AccountingEventMixin],
        associated_event: EvmEvent,
) -> Iterator[EvmEvent]:
    """
    Takes an iterator of accounting events and transforms it into a history base entries iterator.
    Takes associated event as an argument to be able to log it in case of errors.
    """
    for event in events_iterator:
        if not isinstance(event, EvmEvent) and not isinstance(event, HistoryEvent):  # TODO: undo. Is a temporary hack  # noqa: E501
            log.error(
                f'At accounting for tx_event {associated_event.notes} with hash '
                f'{associated_event.tx_hash.hex()} we expected to take an additional '
                f'event but found a non history base entry event',
            )
            return

        yield event  # type: ignore[misc]


class TransactionsAccountant():

    def __init__(
            self,
            evm_accounting_aggregators: 'EVMAccountingAggregators',
            pot: 'AccountingPot',
    ) -> None:
        self.evm_accounting_aggregators = evm_accounting_aggregators
        self.pot = pot
        self.tx_event_settings: dict[str, TxEventSettings] = {}

    def reset(self) -> None:
        self.evm_accounting_aggregators.reset()
        self.tx_event_settings = self.evm_accounting_aggregators.get_accounting_settings(self.pot)

    def process(
            self,
            event: Union[HistoryEvent, EvmEvent],
            events_iterator: Iterator[AccountingEventMixin],
    ) -> int:
        """Process a transaction event and return amount of actions consumed from the iterator"""
        timestamp = event.get_timestamp_in_sec()
        type_identifier = event.get_type_identifier()
        event_settings = self.tx_event_settings.get(type_identifier, None)
        if event_settings is None:
            event_settings = self.tx_event_settings.get(
                event.get_type_identifier(include_counterparty=False),
            )
            if (  # For swaps we have a default treatment but for the rest we bail
                event_settings is None or
                event_settings.accounting_treatment != TxAccountingTreatment.SWAP
            ):
                log.debug(
                    f'During transaction accounting found transaction event {event} '
                    f'with no mapped event settings. Skipping...',
                )
                return 1

        # if there is any module specific accountant functionality call it
        if event_settings.accountant_cb is not None and isinstance(event, EvmEvent):
            event_settings.accountant_cb(
                pot=self.pot,
                event=event,
                other_events=evm_events_iterator(events_iterator, event),
            )

        if event_settings.accounting_treatment == TxAccountingTreatment.SWAP:
            in_event = next(evm_events_iterator(events_iterator, event), None)  # type: ignore[arg-type] # noqa: E501
            if in_event is None:
                log.error(
                    f'Tried to process accounting swap but could not find the in '
                    f'event for {event}',
                )
                return 1
            return self._process_tx_swap(
                timestamp=timestamp,
                out_event=event,
                in_event=in_event,
                event_settings=event_settings,
            )

        self.pot.add_asset_change_event(
            method=event_settings.method,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=event.notes if event.notes else '',
            location=event.location,
            timestamp=timestamp,
            asset=event.asset,
            amount=event.balance.amount,
            taxable=event_settings.taxable,
            count_entire_amount_spend=event_settings.count_entire_amount_spend,
            count_cost_basis_pnl=event_settings.count_cost_basis_pnl,
            extra_data={
                'tx_hash': event.tx_hash.hex() if isinstance(event, EvmEvent) else event.event_identifier,  # TODO: undo. Is a temporary hack  # noqa: E501
            },
        )
        return 1

    def _process_tx_swap(
            self,
            timestamp: Timestamp,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            event_settings: TxEventSettings,
    ) -> int:
        prices = self.pot.get_prices_for_swap(
            timestamp=timestamp,
            amount_in=in_event.balance.amount,
            asset_in=in_event.asset,
            amount_out=out_event.balance.amount,
            asset_out=out_event.asset,
            fee_info=None,
        )
        if prices is None:
            log.debug(f'Skipping {self} at accounting for a swap due to inability to find a price')
            return 2

        base_group_id = out_event.tx_hash.hex() if isinstance(out_event, EvmEvent) else out_event.event_identifier  # TODO: undo. Is a temporary hack  # noqa: E501
        group_id = base_group_id + str(out_event.sequence_index) + str(in_event.sequence_index)  # noqa: E501
        self.pot.add_spend(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=out_event.notes if out_event.notes else '',
            location=out_event.location,
            timestamp=timestamp,
            asset=out_event.asset,
            amount=out_event.balance.amount,
            taxable=event_settings.taxable,
            given_price=prices[0],
            count_entire_amount_spend=False,
            extra_data={
                'tx_hash': base_group_id,  # TODO: undo. Is a temporary hack
                'group_id': group_id,
            },
        )
        self.pot.add_acquisition(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=in_event.notes if in_event.notes else '',
            location=in_event.location,
            timestamp=timestamp,
            asset=in_event.asset,
            amount=in_event.balance.amount,
            taxable=False,  # acquisitions in swaps are never taxable
            given_price=prices[1],
            extra_data={
                'tx_hash': base_group_id,  # TODO: undo. Is a temporary hack
                'group_id': group_id,
            },
        )
        return 2
