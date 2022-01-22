from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures import HistoryBaseEntry

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v31_to_v32(db: 'DBHandler') -> None:
    """Upgrades the DB from v31 to v32

    After changing the HistoryBaseEntry the identifiers for the events
    stored in database need to be updated to make them reliable. The reason
    is that the function that generates the identifier has been modified.

    Also adds the subtype REWARD to staking rewards (before they had type staking
    and no subtype)
    """
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
    cursor.execute(
        'UPDATE history_events SET subtype="reward" WHERE type="staking" AND subtype IS NULL;',
    )
    db.conn.commit()
