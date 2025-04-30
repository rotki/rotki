from typing import TYPE_CHECKING

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryBaseEntryType

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.history_events import DBHistoryEvents


def edit_grouped_events_with_optional_fee(
        events_db: 'DBHistoryEvents',
        write_cursor: 'DBCursor',
        events: list[HistoryBaseEntry],
        events_type: HistoryBaseEntryType,
        identifiers: list[int] | None = None,
) -> None:
    """
    Handle grouped events, including fee-related modifications:
    - Delete fee entry if it existed but is now removed
    - Create fee entry if it wasn't present before
    - Update existing events when modifications occur

    Evm swaps are more complex and must rely on the identifiers specified. This is handled
    in edit_grouped_evm_swap_events.

    May raise:
    - InputError
    """
    if (result := write_cursor.execute(  # Get the event_identifier, selecting by the identifier of the first event.  # noqa: E501
        'SELECT event_identifier FROM history_events WHERE identifier=?',
        (events[0].identifier,),
    ).fetchone()) is not None:
        event_identifier = result[0]
    else:
        raise InputError(f'Tried to edit event with id {events[0].identifier} but could not find it in the DB')  # noqa: E501

    if events_type == HistoryBaseEntryType.EVM_SWAP_EVENT:
        edit_grouped_evm_swap_events(  # Evm swaps must be handled differently.
            events_db=events_db,
            write_cursor=write_cursor,
            events=events,
            identifiers=identifiers,  # type: ignore[arg-type]  # will not be none for evm swaps
            event_identifier=event_identifier,
        )
        return

    existing_event_count = write_cursor.execute(
        'SELECT COUNT(*) FROM history_events WHERE event_identifier=?',
        (event_identifier,),
    ).fetchone()[0]
    no_fee_num = 1 if events_type == HistoryBaseEntryType.ASSET_MOVEMENT_EVENT else 2
    with_fee_num = no_fee_num + 1

    if (new_event_count := len(events)) == no_fee_num and existing_event_count == with_fee_num:
        # in the db we had a fee entry and now we have removed it
        events_to_edit = events[:new_event_count]
        write_cursor.execute(
            'DELETE FROM history_events WHERE event_identifier=? and sequence_index=?',
            (events[0].event_identifier, events[0].sequence_index + no_fee_num),
        )
    elif new_event_count == with_fee_num and existing_event_count == no_fee_num:
        # we didn't have a fee in the db and we have it now
        events_to_edit = events[:existing_event_count]
        events_db.add_history_event(  # Add the new fee event. Mark as customized since its being manually added by the user.  # noqa: E501
            write_cursor=write_cursor,
            event=events[-1],
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
    else:
        assert new_event_count == existing_event_count and existing_event_count in (no_fee_num, with_fee_num)  # noqa: E501
        events_to_edit = events

    for event in events_to_edit:
        events_db.edit_history_event(write_cursor=write_cursor, event=event)


def edit_grouped_evm_swap_events(
        events_db: 'DBHistoryEvents',
        write_cursor: 'DBCursor',
        events: list[HistoryBaseEntry],
        identifiers: list[int],
        event_identifier: str,
) -> None:
    """Handle editing of grouped evm swap events.
    Determines which events to add, edit, or remove using the `identifiers`
    and `events` lists as follows:
    - Inserts events that have no identifier.
    - Edits events whose identifier is set.
    - Removes events whose identifier is present in `identifiers`,
       but have no corresponding event in `events`.

    May raise InputError if a new event is added that collides
    with the sequence index of an existing event.
    """
    edited_identifiers, new_events = [], []
    for event in events:
        if event.identifier is None:  # No existing identifier - this is a new event.
            new_events.append(event)
        else:  # Already has an identifier - edit existing event.
            events_db.edit_history_event(write_cursor=write_cursor, event=event)
            edited_identifiers.append(event.identifier)

    if identifiers != edited_identifiers:  # There are identifiers with no corresponding events - these events need to be deleted.  # noqa: E501
        write_cursor.executemany(
            'DELETE FROM history_events WHERE identifier=?',
            [(identifier,) for identifier in set(identifiers) - set(edited_identifiers)],
        )

    for event in new_events:
        if write_cursor.execute(  # Check if this event will hit a sequence_index that is already in use.  # noqa: E501
            'SELECT COUNT(*) FROM history_events WHERE event_identifier=? AND sequence_index=?',
            (event_identifier, event.sequence_index),
        ).fetchone()[0] != 0:
            raise InputError(
                f'Tried to insert an event with event_identifier {event_identifier} and '
                f'sequence_index {event.sequence_index}, but an event already exists at '
                'that sequence_index.',
            )

        # Add the new event marking it as customized since its being manually added by the user.
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=event,
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
