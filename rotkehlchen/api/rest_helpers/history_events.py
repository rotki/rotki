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
) -> None:
    """
    Handle grouped events, including fee-related modifications:
    - Delete fee entry if it existed but is now removed
    - Create fee entry if it wasn't present before
    - Update existing events when modifications occur

    May raise:
    - InputError
    """
    db = events_db.db
    with db.conn.read_ctx() as read_cursor:
        read_cursor.execute(
            'SELECT event_identifier FROM history_events WHERE identifier=?',
            (events[0].identifier,),
        )
        if (result := read_cursor.fetchone()) is not None:
            event_identifier = result[0]
        else:
            raise InputError(f'Tried to edit event with id {events[0].identifier} but could not find it in the DB')  # noqa: E501

        existing_events_num = read_cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE event_identifier=?',
            (event_identifier,),
        ).fetchone()[0]

    no_fee_num = 1 if events_type == HistoryBaseEntryType.ASSET_MOVEMENT_EVENT else 2
    with_fee_num = no_fee_num + 1

    if (edit_events_num := len(events)) == no_fee_num and existing_events_num == with_fee_num:
        # in the db we had a fee entry and now we have removed it
        for idx in range(edit_events_num):
            events_db.edit_history_event(
                event=events[idx],
                write_cursor=write_cursor,
            )
        write_cursor.execute(
            'DELETE FROM history_events WHERE event_identifier=? and sequence_index=?',
            (events[0].event_identifier, events[0].sequence_index + no_fee_num),
        )
    elif edit_events_num == with_fee_num and existing_events_num == no_fee_num:
        # we didn't have a fee in the db and we have it now
        for idx in range(existing_events_num):
            events_db.edit_history_event(
                event=events[idx],
                write_cursor=write_cursor,
            )
        # Add the new fee event. Since its being manually added by the user it must be marked as customized.  # noqa: E501
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=events[-1],
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
    else:
        assert edit_events_num == existing_events_num and existing_events_num in (no_fee_num, with_fee_num)  # noqa: E501
        for event in events:
            events_db.edit_history_event(
                event=event,
                write_cursor=write_cursor,
            )
