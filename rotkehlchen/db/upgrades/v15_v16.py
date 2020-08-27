from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v15_to_v16(db: 'DBHandler') -> None:
    """Upgrades the DB from v15 to v16

    - Deletes all ethereum transactions from the DB so they can be saved again
      along with the used query ranges.
    - Deletes all asset movements and remakes the table to that the newly
      pulled data can now include the src/dst address and transaction id
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM ethereum_transactions;')
    db.conn.commit()
    cursor.execute('DELETE FROM asset_movements;')
    cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
        ('%\\_asset_movements', '\\'),
    )
    cursor.execute('DROP TABLE IF EXISTS asset_movements;')
    # and create the table. Same schema as was in launch of v1.7.0
    cursor.execute("""CREATE TABLE IF NOT EXISTS asset_movements (
    id TEXT PRIMARY KEY,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES asset_movement_category(category),
    address TEXT,
    transaction_id TEXT,
    time INTEGER,
    asset VARCHAR[10],
    amount TEXT,
    fee_asset VARCHAR[10],
    fee TEXT,
    link TEXT
    );""")
