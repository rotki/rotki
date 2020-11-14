from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures import BalanceType

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v20_to_v21(db: 'DBHandler') -> None:
    """Upgrades the DB from v20 to v21

    Upgrades the timed balances to also contain the balance type (category).
    Defaults to ASSET right now, but opens up the way to store liabilities too
    """
    cursor = db.conn.cursor()
    # Get the old data, appending the default value of ASSET for balance category
    query = cursor.execute('SELECT time, currency, amount, usd_value FROM timed_balances;')
    balances = []
    for entry in query:
        balances.append((
            BalanceType.ASSET.serialize_for_db(),  # append the default balance_category
            entry[0],  # time
            entry[1],  # currency
            entry[2],  # amount
            entry[3],  # usd_value
        ))
    # delete old table and create new one
    cursor.execute('DROP TABLE IF EXISTS timed_balances')
    cursor.execute("""
CREATE TABLE IF NOT EXISTS timed_balances (
    category CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category),
    time INTEGER,
    currency VARCHAR[12],
    amount TEXT,
    usd_value TEXT,
    PRIMARY KEY (time, currency, category)
);
""")
    # And add the old data with the new default value to the new table
    cursor.executemany(
        'INSERT INTO timed_balances(category, time, currency, amount, usd_value) '
        'VALUES (?, ?, ?, ?, ?)',
        balances,
    )
    db.conn.commit()
