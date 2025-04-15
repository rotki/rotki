from typing import TYPE_CHECKING

from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType

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
        if (result := read_cursor.execute(  # Get the event_identifier and beginning sequence index of the group, selecting by the identifier of the first event.  # noqa: E501
            'SELECT event_identifier, sequence_index FROM history_events WHERE identifier=?',
            (events[0].identifier,),
        ).fetchone()) is not None:
            event_identifier, sequence_index = result
        else:
            raise InputError(f'Tried to edit event with id {events[0].identifier} but could not find it in the DB')  # noqa: E501

        if (entry_type := events[0].entry_type) == HistoryBaseEntryType.EVM_SWAP_EVENT:
            # There can be multiple groups of EvmSwapEvents in a single transaction.
            # Only count events in this group using the consecutive sequence indexes of the
            # spend/receive/fee events.
            existing_event_count = read_cursor.execute(
                'SELECT COUNT(*) FROM history_events WHERE event_identifier=? AND entry_type=? '
                'AND ((subtype=? AND sequence_index=?) OR (subtype=? AND sequence_index=?) '
                'OR (subtype=? AND sequence_index=?))',
                (event_identifier, entry_type.serialize_for_db(),
                 HistoryEventSubType.SPEND.serialize(), sequence_index,
                 HistoryEventSubType.RECEIVE.serialize(), sequence_index + 1,
                 HistoryEventSubType.FEE.serialize(), sequence_index + 2),
            ).fetchone()[0]
        else:  # Other types of grouped events will only have one group per event_identifier.
            existing_event_count = read_cursor.execute(
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
