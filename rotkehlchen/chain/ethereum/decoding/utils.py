from typing import Optional

from rotkehlchen.accounting.structures import HistoryBaseEntry


def maybe_reshuffle_events(
        out_event: Optional[HistoryBaseEntry],
        in_event: Optional[HistoryBaseEntry],
) -> None:
    """Takes 2 events and makes sure that the sequence index of out_event comes first.

    This is for two reasons.
    1. So that it appears uniformly in the UI
    2. So that during accounting we know which type of event comes first in a swap-like event.

    The events are optional since it's also possible they may not be found.
    """
    if out_event is None or in_event is None:
        return

    if out_event.sequence_index > in_event.sequence_index:
        old_out_index = out_event.sequence_index
        out_event.sequence_index = in_event.sequence_index
        in_event.sequence_index = old_out_index
