import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, TypeVar
from rotkehlchen.accounting.ledger_actions import LedgerActionType

from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.accounting.structures import (
    BaseEventSettins,
    TxAccountingTreatment,
    TxEventSettings,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def make_default_accounting_settings(pot: 'AccountingPot') -> dict[str, BaseEventSettins]:
    """
    Returns accounting settings for events that can come from various decoders and thus don't have
    any particular protocol. These settings also allow users to customize events in the UI.
    Users are supposed to apply these settings in the history view.
    """
    result = {}
    gas_key = str(HistoryEventType.SPEND) + '__' + str(HistoryEventSubType.FEE) + '__' + CPT_GAS  # noqa: E501
    result[gas_key] = BaseEventSettins(
        taxable=pot.settings.include_gas_costs,
        count_entire_amount_spend=pot.settings.include_gas_costs,
        count_cost_basis_pnl=pot.settings.include_crypto2crypto,
        method='spend',
    )
    spend_key = str(HistoryEventType.SPEND) + '__' + str(HistoryEventSubType.NONE)
    result[spend_key] = BaseEventSettins(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='spend',
    )
    receive_key = str(HistoryEventType.RECEIVE) + '__' + str(HistoryEventSubType.NONE)
    result[receive_key] = BaseEventSettins(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='acquisition',
    )
    deposit_key = str(HistoryEventType.DEPOSIT) + '__' + str(HistoryEventSubType.NONE)
    result[deposit_key] = BaseEventSettins(
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='spend',
    )
    withdraw_key = str(HistoryEventType.WITHDRAWAL) + '__' + str(HistoryEventSubType.NONE)
    result[withdraw_key] = BaseEventSettins(
        taxable=False,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    fee_key = str(HistoryEventType.SPEND) + '__' + str(HistoryEventSubType.FEE)
    result[fee_key] = BaseEventSettins(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='spend',
    )
    renew_key = str(HistoryEventType.RENEW) + '__' + str(HistoryEventSubType.NONE)
    result[renew_key] = BaseEventSettins(
        taxable=True,
        count_entire_amount_spend=True,
        count_cost_basis_pnl=True,
        method='spend',
    )
    swap_key = str(HistoryEventType.TRADE) + '__' + str(HistoryEventSubType.SPEND)
    result[swap_key] = BaseEventSettins(
        taxable=True,
        count_entire_amount_spend=False,
        count_cost_basis_pnl=True,
        method='spend',
        accounting_treatment=TxAccountingTreatment.SWAP,
    )
    airdrop_key = str(HistoryEventType.RECEIVE) + '__' + str(HistoryEventSubType.AIRDROP)
    result[airdrop_key] = BaseEventSettins(
        taxable=LedgerActionType.AIRDROP in pot.settings.taxable_ledger_actions,
        # count_entire_amount_spend and count_cost_basis_pnl don't matter for acquisitions.
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    reward_key = str(HistoryEventType.RECEIVE) + '__' + str(HistoryEventSubType.REWARD)
    result[reward_key] = BaseEventSettins(
        taxable=True,
        # count_entire_amount_spend and count_cost_basis_pnl don't matter for acquisitions.
        count_entire_amount_spend=False,
        count_cost_basis_pnl=False,
        method='acquisition',
    )
    return result


T = TypeVar('T', bound=HistoryBaseEntry)


def history_base_entries_iterator(
        events_iterator: Iterator[AccountingEventMixin],
        associated_event: T,
) -> Iterator[T]:
    """
    Takes an iterator of accounting events and transforms it into a history base entries iterator.
    Takes associated event as an argument to be able to log it in case of errors.
    """
    for event in events_iterator:
        if isinstance(event, type(associated_event)) is False:
            log.error(
                f'At accounting for event {associated_event.notes} with identifier '
                f'{associated_event.event_identifier} we expected to take an additional '
                f'event but found a non {type(associated_event)} event',
            )
            return

        yield event  # type: ignore[misc]  # event is guaranteed to be of type T


class HistoryBaseEntriesAccountant:

    def __init__(
            self,
            evm_accounting_aggregators: 'EVMAccountingAggregators',
            pot: 'AccountingPot',
    ) -> None:
        self.evm_accounting_aggregators = evm_accounting_aggregators
        self.pot = pot
        self.tx_event_settings: dict[str, BaseEventSettins] = {}

    def reset(self) -> None:
        self.evm_accounting_aggregators.reset()
        self.tx_event_settings = (  # Using | operator is fine since keys are unique
            self.evm_accounting_aggregators.get_accounting_settings(self.pot) |
            make_default_accounting_settings(self.pot)
        )

    def process(
            self,
            event: HistoryBaseEntry,
            events_iterator: Iterator[AccountingEventMixin],
    ) -> int:
        """Process a history base entry and return number of actions consumed from the iterator"""
        timestamp = event.get_timestamp_in_sec()
        event_settings = self.tx_event_settings.get(event.get_type_identifier(), None)
        if event_settings is None:
            if isinstance(event, EvmEvent) is False:
                return 1

            # For evm events try to find settings without counterparty
            event_settings = self.tx_event_settings.get(
                event.get_type_identifier(include_counterparty=False),
            )
            if event_settings is None:
                log.debug(
                    f'During transaction accounting found history base entry {event} '
                    f'with no mapped event settings. Skipping...',
                )
                return 1

        # if there is any module specific accountant functionality call it
        if (
            isinstance(event, EvmEvent) and
            isinstance(event_settings, TxEventSettings) and
            event_settings.accountant_cb is not None
        ):
            event_settings.accountant_cb(
                pot=self.pot,
                event=event,
                other_events=history_base_entries_iterator(events_iterator, event),
            )

        general_extra_data = {}
        if isinstance(event, EvmEvent):
            general_extra_data['tx_hash'] = event.tx_hash.hex()
        if event_settings.accounting_treatment == TxAccountingTreatment.SWAP:
            in_event = next(history_base_entries_iterator(events_iterator, event), None)
            if in_event is None:
                log.error(
                    f'Tried to process accounting swap but could not find the in '
                    f'event for {event}',
                )
                return 1
            return self._process_swap(
                timestamp=timestamp,
                out_event=event,
                in_event=in_event,
                event_settings=event_settings,
                general_extra_data=general_extra_data,
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
            extra_data=general_extra_data,
        )
        return 1

    def _process_swap(
            self,
            timestamp: Timestamp,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            event_settings: BaseEventSettins,
            general_extra_data: dict[str, Any],
    ) -> int:
        """
        Takes out_event (spend part), in_event (acquisition part) and generates corresponding
        accounting events.
        """
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

        group_id = out_event.event_identifier + str(out_event.sequence_index) + str(in_event.sequence_index)  # noqa: E501
        extra_data = general_extra_data | {'group_id': group_id}
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
            extra_data=extra_data,
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
            extra_data=extra_data,
        )
        return 2
