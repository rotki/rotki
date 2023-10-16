from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import AssetWithSymbol
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog


def maybe_reshuffle_events(
        ordered_events: Sequence[Optional['EvmEvent']],
        events_list: list['EvmEvent'],
) -> None:
    """Takes a list of events to order and makes sure that the sequence index of each
    of them is in ascending order and that the events are consecutive in the
    decoded events list.

    This is for two reasons.
    1. So that it appears uniformly in the UI
    2. So that during accounting we know which type of event comes first in a swap-like event.

    For example for swaps we expect two consecutive events with the first
    being the out event and the second the in event,

    The events are optional since it's also possible they may not be found.
    """
    actual_events = [x for x in ordered_events if x is not None]
    if len(actual_events) <= 1:
        return  # nothing to do

    all_other_events = []
    max_seq_index = -1
    for event in events_list:
        if event not in actual_events:
            all_other_events.append(event)
            if event.sequence_index > max_seq_index:
                max_seq_index = event.sequence_index

    for idx, event in enumerate(actual_events):
        event.sequence_index = max_seq_index + idx + 1
    events_list = all_other_events + actual_events


def bridge_prepare_data(
        tx_log: 'EvmTxReceiptLog',
        deposit_topics: Sequence[bytes],
        source_chain: ChainID,
        target_chain: ChainID,
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
) -> tuple[HistoryEventType, HistoryEventType, ChainID, ChainID, ChecksumEvmAddress]:
    """Method to prepare the bridge variables

    When coming here the caller has to make sure that:
    - tx_log topics is either in deposit_topics or else is a withdrawal
    """
    # Determine whether it is a deposit or a withdrawal
    if tx_log.topics[0] in deposit_topics:
        expected_event_type = HistoryEventType.SPEND
        expected_location_label = from_address
        new_event_type = HistoryEventType.DEPOSIT
        from_chain, to_chain = source_chain, target_chain
    else:  # withdrawal
        expected_event_type = HistoryEventType.RECEIVE
        expected_location_label = to_address
        new_event_type = HistoryEventType.WITHDRAWAL
        from_chain, to_chain = target_chain, source_chain

    return expected_event_type, new_event_type, from_chain, to_chain, expected_location_label


def bridge_match_transfer(
        event: 'EvmEvent',
        from_address: ChecksumEvmAddress,
        to_address: ChecksumEvmAddress,
        from_chain: ChainID,
        to_chain: ChainID,
        amount: FVal,
        asset: AssetWithSymbol,
        expected_event_type: HistoryEventType,
        new_event_type: HistoryEventType,
        counterparty: CounterpartyDetails,
) -> None:
    """Action to take when matching a bridge transfer event"""
    from_label, to_label = f' address {from_address}', f' address {to_address}'
    if expected_event_type == HistoryEventType.SPEND:
        if event.location_label == from_address:
            from_label = ''
        if to_address == from_address:
            to_label = ''
    elif expected_event_type == HistoryEventType.RECEIVE:
        if event.location_label == to_address:
            to_label = ''
        if to_address == from_address:
            from_label = ''

    event.event_type = new_event_type
    event.event_subtype = HistoryEventSubType.BRIDGE
    event.counterparty = counterparty.identifier
    event.notes = (
        f'Bridge {amount} {asset.symbol} from {from_chain.label()}{from_label} to '
        f'{to_chain.label()}{to_label} via {counterparty.label} bridge'
    )
