import logging
from typing import TYPE_CHECKING, Dict, Iterator, List

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.chain.ethereum.accounting.structures import TxEventSettings, TxMultitakeTreatment
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.ethereum.accounting.aggregator import EVMAccountingAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class TransactionsAccountant():

    def __init__(
            self,
            evm_accounting_aggregator: 'EVMAccountingAggregator',
            pot: 'AccountingPot',
    ) -> None:
        self.evm_accounting_aggregator = evm_accounting_aggregator
        self.pot = pot
        self.tx_event_settings: Dict[str, TxEventSettings] = {}

    def reset(self) -> None:
        self.evm_accounting_aggregator.reset()
        self.tx_event_settings = self.evm_accounting_aggregator.get_accounting_settings(self.pot)

    def process(
            self,
            event: HistoryBaseEntry,
            events_iterator: Iterator[AccountingEventMixin],
    ) -> int:
        """Process a transaction event and return amount of actions consumed from the iterator"""
        timestamp = event.get_timestamp_in_sec()
        type_identifier = event.get_type_identifier()
        event_settings = self.tx_event_settings.get(type_identifier, None)
        if event_settings is None:
            log.debug(
                f'During transaction accounting found transaction event {event} '
                f'with no mapped event settings. Skipping...',
            )
            return 1

        notes = event.notes if event.notes else ''
        counter = 1
        other_events: List[HistoryBaseEntry] = []
        while counter < event_settings.take:
            next_event = next(events_iterator, None)
            if next_event is None:
                log.debug(
                    f'At accounting for tx_event {notes} we expected to take '
                    f'{event_settings.take} additional events but found no more',
                )
                return counter
            if not isinstance(next_event, HistoryBaseEntry):
                log.debug(
                    f'At accounting for tx_event {notes} we expected to take '
                    f'{event_settings.take} additional events but found a '
                    f'non history base entry event',
                )
                return counter

            other_events.append(next_event)
            counter += 1

        # if there is any module specific accountant functionality call it
        if event_settings.accountant_cb is not None:
            event_settings.accountant_cb(
                pot=self.pot,
                event=event,
                other_events=other_events,
            )

        if event_settings.multitake_treatment == TxMultitakeTreatment.SWAP:  # noqa: E501
            return self._process_tx_swap(
                timestamp=timestamp,
                out_event=event,
                in_event=other_events[0],
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
            extra_data={'tx_hash': event.serialized_event_identifier},
        )
        return 1

    def _process_tx_swap(
            self,
            timestamp: Timestamp,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            event_settings: TxEventSettings,
    ) -> int:  # noqa: E501
        prices = self.pot.get_prices_for_swap(
            timestamp=timestamp,
            amount_in=in_event.balance.amount,
            asset_in=in_event.asset,
            amount_out=out_event.balance.amount,
            asset_out=out_event.asset,
            fee=None,
            fee_asset=None,
        )
        if prices is None:
            log.debug(f'Skipping {self} at accounting for a swap due to inability to find a price')
            return 2

        group_id = out_event.serialized_event_identifier + str(out_event.sequence_index) + str(in_event.sequence_index)  # noqa: E501
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
                'tx_hash': out_event.serialized_event_identifier,
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
            taxable=event_settings.taxable,
            given_price=prices[1],
            extra_data={
                'tx_hash': in_event.serialized_event_identifier,
                'group_id': group_id,
            },
        )
        return 2
