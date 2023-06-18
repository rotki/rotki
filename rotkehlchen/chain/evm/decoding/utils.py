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

    events_list.sort(key=lambda event: event.sequence_index)
    events_num = len(events_list)
    current_event = actual_events.pop(0)
    for idx, event in enumerate(events_list):
        next_idx = idx + 1

        if next_idx >= events_num:  # if no more events, push events after
            for next_event_idx, next_event in enumerate(actual_events):
                next_event.sequence_index = current_event.sequence_index + next_event_idx + 1
            break  # and we are done

        if event == current_event:
            if events_list[next_idx] != actual_events[0] and events_list[next_idx].sequence_index != event.sequence_index + 1:  # noqa: E501
                # if we have more events and next sequence index is free
                current_event = actual_events.pop(0)
                current_event.sequence_index = event.sequence_index + 1
                continue  # use it for the following event

            if events_list[next_idx] == actual_events[0]:  # if next event follows just continue
                current_event = actual_events.pop(0)
                continue

            # otherwise swap index of next event with the event that should be current here
            _swap_event_indices(events_list[next_idx], current_event)
