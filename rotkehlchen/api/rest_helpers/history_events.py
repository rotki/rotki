from typing import TYPE_CHECKING

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.asset_movement import AssetMovement

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.history_events import DBHistoryEvents


def edit_asset_movements(
        events_db: 'DBHistoryEvents',
        write_cursor: 'DBCursor',
        events: list[AssetMovement],
) -> None:
    """
    Handle asset movement events, including fee-related modifications:
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

        num_of_events = read_cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE event_identifier=?',
            (event_identifier,),
        ).fetchone()[0]

    if len(events) == 1 and num_of_events == 2:
        # in the db we had a fee entry and now we have removed it
        events_db.edit_history_event(
            event=events[0],
            write_cursor=write_cursor,
        )
        write_cursor.execute(
            'DELETE FROM history_events WHERE event_identifier=? and sequence_index=?',
            (events[0].event_identifier, events[0].sequence_index + 1),
        )
    elif len(events) == 2 and num_of_events == 1:
        # we didn't have a fee in the db and we have it now
        events_db.edit_history_event(
            event=events[0],
            write_cursor=write_cursor,
        )
        events_db.add_history_event(
            write_cursor=write_cursor,
            event=events[1],
            mapping_values={HISTORY_MAPPING_KEY_STATE: HISTORY_MAPPING_STATE_CUSTOMIZED},
        )
    else:
        assert len(events) == num_of_events and num_of_events in (1, 2)
        for event in events:
            events_db.edit_history_event(
                event=event,
                write_cursor=write_cursor,
            )
