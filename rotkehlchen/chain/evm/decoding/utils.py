from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent


def _swap_event_indices(event1: 'EvmEvent', event2: 'EvmEvent') -> None:
    old_event1_index = event1.sequence_index
    event1.sequence_index = event2.sequence_index
    event2.sequence_index = old_event1_index


def maybe_reshuffle_events(
        ordered_events: Sequence[Optional['EvmEvent']],
        events_list: list['EvmEvent'],
) -> None:
    """Takes a list of events to order and makes sure that the sequence index of each
    of them is in ascending order and that the the events are consecutive in the
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
