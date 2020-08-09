from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _delete_bittrex_data(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the user credentials trades table at v10
    cursor.execute('DELETE FROM trades WHERE location="D";')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "bittrex_%";')
    db.conn.commit()


def upgrade_v11_to_v12(db: 'DBHandler') -> None:
    """Upgrades the DB from v11 to v12

    - Deletes all bittrex related DB data
    """
    _delete_bittrex_data(db)
