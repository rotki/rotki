from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _create_new_tables(db: 'DBHandler') -> None:
    """Create new tables added in this upgrade"""
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS ethereum_accounts_details (
    account VARCHAR[42] NOT NULL PRIMARY KEY,
    tokens_list TEXT NOT NULL,
    time INTEGER NOT NULL
    );""")


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
    _create_new_tables(db)
