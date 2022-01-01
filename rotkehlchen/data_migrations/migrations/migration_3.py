from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures import HistoryBaseEntry

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen


def data_migration_3(rotki: 'Rotkehlchen') -> None:
    """
    After changing the HistoryBaseEntry the identifiers for the events
    stored in database need to be updated to make them reliable. The reason
    is that the function that generates the identifier has been modified.
    """
    db = rotki.data.db
    cursor = db.conn.cursor()
    events = cursor.execute('SELECT * FROM history_events ')
    rewrites = []
    for event_data in events:
        event = HistoryBaseEntry.deserialize_from_db(event_data)
        rewrites.append((event.identifier, event_data[0]))

    cursor.executemany(
        'UPDATE history_events SET identifier=? WHERE identifier=?',
        rewrites,
    )
