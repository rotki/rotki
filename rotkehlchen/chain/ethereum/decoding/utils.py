from typing import List, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.types import ChecksumEvmAddress

from .constants import ETHADDRESS_TO_KNOWN_NAME


def address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:
    name = ETHADDRESS_TO_KNOWN_NAME.get(address)
    if name and 'Kraken' in name:
        return CPT_KRAKEN
    return None


def _swap_event_indices(event1: HistoryBaseEntry, event2: HistoryBaseEntry) -> None:
    old_event1_index = event1.sequence_index
    event1.sequence_index = event2.sequence_index
    event2.sequence_index = old_event1_index


def maybe_reshuffle_events(
        out_event: Optional[HistoryBaseEntry],
        in_event: Optional[HistoryBaseEntry],
        events_list: Optional[List[HistoryBaseEntry]] = None,
) -> None:
    """Takes 2 events and makes sure that the sequence index of out_event comes first.
    Also make sure that the events are consecutive.

    This is for two reasons.
    1. So that it appears uniformly in the UI
    2. So that during accounting we know which type of event comes first in a swap-like event.
    We expect two consecutive events with the first being the out event and the second the in.

    The events are optional since it's also possible they may not be found.
    """
    if out_event is None or in_event is None:
        return

    if out_event.sequence_index > in_event.sequence_index:
        _swap_event_indices(out_event, in_event)

    # If given, check the events list to make sure events are consecutive
    if events_list is not None:
        events_num = len(events_list)
        for idx, event in enumerate(events_list):
            if event == out_event:
                next_idx = idx + 1
                if next_idx >= events_num:  # if no more events, then use push in event after out
                    in_event.sequence_index = event.sequence_index + 1
                    break
                if events_list[next_idx] != in_event and events_list[next_idx].sequence_index != event.sequence_index + 1:  # noqa: E501
                    # else if we have more events and next sequence index is free
                    in_event.sequence_index = event.sequence_index + 1
                    break  # use it for the in event

                # otherwise swap index of next event with the in event
                _swap_event_indices(events_list[next_idx], in_event)
                break
