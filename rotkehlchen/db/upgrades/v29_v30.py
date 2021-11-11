from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v29_to_v30(db: 'DBHandler') -> None:
    """Upgrades the DB from v29 to v30

    - Add category table to manually_tracked_balances
    """
    cursor = db.conn.cursor()
    # We need to disable foreign_keys to add the table due the following constraint
    # Cannot add a REFERENCES column with non-NULL default value
    cursor.execute('PRAGMA foreign_keys = 0;')
    db.conn.commit()
    cursor.execute(
        "ALTER TABLE manually_tracked_balances ADD category "
        "CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category);",
    )
    cursor.execute('PRAGMA foreign_keys = 1;')
    # Insert the new bitpanda location
    cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("b", 34);')
    db.conn.commit()
