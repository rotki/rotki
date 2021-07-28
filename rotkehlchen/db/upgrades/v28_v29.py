from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v28_to_v29(db: 'DBHandler') -> None:
    """Upgrades the DB from v28 to v29

    - Updates values in type column for uniswap_events
    - Changes table name from uniswap_events to amm_events
    """
    cursor = db.conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS uniswap_events;')
    db.conn.commit()
