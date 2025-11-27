import logging
from typing import TYPE_CHECKING, Any, TypeVar, cast

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.rules import AccountingRulesManager
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants import ONE
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import EventDirection, HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from collections.abc import Callable

    from more_itertools import peekable

    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
T = TypeVar('T', bound=HistoryBaseEntry)


class EventsAccountant:
    """
    This class contains the different rules applied to history events during the accounting
    process. It applies special rules for evm events and also the default defined rules.
    """

    def __init__(
            self,
            evm_accounting_aggregators: 'EVMAccountingAggregators',
            pot: 'AccountingPot',
    ) -> None:
        self.evm_accounting_aggregators = evm_accounting_aggregators
        self.pot = pot
        self.rules_manager = AccountingRulesManager(
            database=self.pot.database,
            evm_aggregators=self.evm_accounting_aggregators,
            pot=self.pot,
        )

    def reset(self) -> None:
        self.rules_manager.reset()

    def process(
            self,
            event: HistoryBaseEntry,
            events_iterator: "peekable['AccountingEventMixin']",
    ) -> int:
        """Process a history base entry and return number of actions consumed from the iterator"""
        event_direction = event.maybe_get_direction()
        if event_direction is None:
            log.error(
                f'Failed to retrieve direction for {event.event_type=} {event.event_subtype}. '
                f'Skipping...',
            )
            return 1

        if event_direction == EventDirection.NEUTRAL:
            log.debug(f'Skipping neutral event {event.identifier=}')
            return 1

        timestamp = event.get_timestamp_in_sec()
        event_settings, event_callback = self.rules_manager.get_event_settings(event)
        if event_settings is None:
            log.debug(
                f'During transaction accounting found history base entry {event} '
                f'with no mapped event settings. Skipping...',
            )
            return 1

        # if there is any module specific accountant functionality call it
        if isinstance(event, EvmEvent) and event_callback is not None:
            event_callback(
                pot=self.pot,
                event=event,  # ignore is due to callbacks being only for evm events
                other_events=events_iterator,  # type: ignore
            )

        general_extra_data = {}
        if isinstance(event, EvmEvent | SolanaEvent):
            general_extra_data['tx_ref'] = str(event.tx_ref)

        if event_settings.accounting_treatment == TxAccountingTreatment.SWAP:
            processed_event_count = 1
            next_event = events_iterator.peek(None)
            if next_event is None:
                log.error(
                    f'Tried to process accounting swap but could not find the in '
                    f'event for {event}',
                )
                return 1

            if not isinstance(next_event, HistoryBaseEntry) or next_event.group_identifier != event.group_identifier:  # noqa: E501
                log.error(
                    f'Tried to process accounting swap but the in '
                    f'event for {event} is not there',
                )
                return 1

            in_event = cast('HistoryBaseEntry', next(events_iterator))  # guaranteed by the if check  # noqa: E501
            processed_event_count += 1
            fee_events = []
            while (
                (next_event := events_iterator.peek(None)) and
                isinstance(next_event, HistoryBaseEntry) and
                next_event.group_identifier == event.group_identifier and
                next_event.event_type == event.event_type and
                next_event.event_subtype == HistoryEventSubType.FEE
            ):
                fee_events.append(cast('HistoryBaseEntry', next(events_iterator)))  # guaranteed by if check  # noqa: E501
                processed_event_count += 1

            with self.pot.database.conn.read_ctx() as cursor:
                if (
                        event.asset in (ignored_assets := self.pot.database.get_ignored_asset_ids(cursor)) or  # noqa: E501
                        in_event.asset in ignored_assets or
                        any(fee_event.asset in ignored_assets for fee_event in fee_events)
                ):  # return early if any events in the swap group have ignored assets.
                    return processed_event_count

            return self._process_swap(
                timestamp=timestamp,
                out_event=event,
                in_event=in_event,
                fee_events=fee_events,
                event_settings=event_settings,
                general_extra_data=general_extra_data,
            )

        self.pot.add_asset_change_event(
            direction=event_direction,
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes=event.notes or '',
            location=event.location,
            timestamp=timestamp,
            asset=event.asset,
            amount=event.amount,
            taxable=event_settings.taxable,
            count_entire_amount_spend=event_settings.count_entire_amount_spend,
            count_cost_basis_pnl=event_settings.count_cost_basis_pnl,
            extra_data=general_extra_data,
        )
        return 1

    def _process_swap(
            self,
            timestamp: Timestamp,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            fee_events: list[HistoryBaseEntry],
            event_settings: BaseEventSettings,
            general_extra_data: dict[str, Any],
    ) -> int:
        """
        Takes out_event (spend part), in_event (acquisition part), optionally fee part
        and generates corresponding accounting events prioritising the following order:
        1. out_event is always first
        2. fee_event comes just after the other event (in/out) with the same asset
        3. sequence of the in_event and fee_event is preserved
        """
        prices = self.pot.get_prices_for_swap(
            timestamp=timestamp,
            amount_in=in_event.amount,
            asset_in=in_event.asset,
            amount_out=out_event.amount,
            asset_out=out_event.asset,
            fees_info=[(fee_event.amount, fee_event.asset) for fee_event in fee_events],
        )
        if prices is None:
            log.debug(f'Skipping {self} at accounting for a swap due to inability to find a price')
            return 2

        group_id = out_event.group_identifier + str(out_event.sequence_index) + str(in_event.sequence_index)  # noqa: E501
        extra_data = general_extra_data | {'group_id': group_id}
        _, trade_taxable_amount = self.pot.add_out_event(
            originating_event_id=out_event.identifier,
            event_type=out_event.get_accounting_event_type(),
            notes=out_event.notes or '',
            location=out_event.location,
            timestamp=timestamp,
            asset=out_event.asset,
            amount=out_event.amount,
            # Determine taxability for the out_event:
            # - Event is only taxable if explicitly allowed in event_settings
            # - AND either:
            #   - It's a crypto-to-fiat trade (receiving fiat), OR
            #   - It's a crypto-to-crypto trade and include_crypto2crypto is enabled
            taxable=(in_event.asset.is_fiat() or self.pot.settings.include_crypto2crypto) and event_settings.taxable,  # noqa: E501
            given_price=prices[0],
            count_entire_amount_spend=False,
            extra_data=extra_data,
        )

        add_in_event_kwargs = {
            'event_type': in_event.get_accounting_event_type(),
            'notes': in_event.notes or '',
            'location': in_event.location,
            'timestamp': timestamp,
            'asset': in_event.asset,
            'amount': in_event.amount,
            'taxable': False,  # acquisitions in swaps are never taxable
            'given_price': prices[1],
            'extra_data': extra_data,
        }
        events_to_add_queue: list[tuple[Callable, dict[str, Any]]] = [
            (self.pot.add_in_event, add_in_event_kwargs),
        ]
        for fee_event in fee_events:
            fee_price = None
            if fee_event.asset == self.pot.profit_currency:
                fee_price = Price(ONE)
            elif fee_event.asset == in_event.asset:
                fee_price = prices[1]
            elif fee_event.asset == out_event.asset:
                fee_price = prices[0]

            if self.pot.settings.include_fees_in_cost_basis:
                # If fee is included in cost basis, we just reduce the amount of fee asset owned
                fee_taxable = False
                fee_taxable_amount_ratio = ONE
            else:
                # Otherwise we make it a normal spend event
                fee_taxable = True
                fee_taxable_amount_ratio = trade_taxable_amount / out_event.amount

            fee_out_event = (self.pot.add_out_event, {
                'originating_event_id': fee_event.identifier,
                'event_type': AccountingEventType.FEE,
                'notes': fee_event.notes,
                'location': fee_event.location,
                'timestamp': timestamp,
                'asset': fee_event.asset,
                'amount': fee_event.amount,
                'taxable': fee_taxable,
                'given_price': fee_price,
                # By setting the taxable amount ratio we determine how much of the fee
                # spending should be a taxable spend and how much free.
                'taxable_amount_ratio': fee_taxable_amount_ratio,
                'count_cost_basis_pnl': True,
                'count_entire_amount_spend': True,
                'extra_data': extra_data,
            })
            if fee_event.asset == out_event.asset or fee_event.sequence_index < in_event.sequence_index:  # noqa: E501
                events_to_add_queue.insert(0, fee_out_event)  # we add fee first
            else:
                events_to_add_queue.append(fee_out_event)

        for adding_method, kwargs in events_to_add_queue:
            adding_method(**kwargs)  # add the queued events
        return 1 + len(events_to_add_queue)  # consumed events
