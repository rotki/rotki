from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v17_to_v18(db: 'DBHandler') -> None:
    """Upgrades the DB from v17 to v18

    - Deletes all aave historical data and cache to allow for fixes after
    https://github.com/rotki/rotki/issues/1491 to happen immediately
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM aave_events;')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')
    db.conn.commit()
