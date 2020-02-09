from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _upgrade_blockchain_accounts_table(db: 'DBHandler') -> None:
    cursor = db.conn.cursor()
    # This is the user credentiaals trades table at v10
    query = cursor.execute('SELECT blockchain, account from blockchain_accounts;')
    account_tuples = []
    for result in query:
        account_tuples.append((result[0], result[1], None))

    # We got all data. Now delete the old table and create the new one
    cursor.execute('DROP TABLE blockchain_accounts;')
    db.conn.commit()
    # Now create blockchain accounts table at v11
    cursor.execute("""CREATE TABLE IF NOT EXISTS blockchain_accounts (
    blockchain VARCHAR[24],
    account TEXT NOT NULL PRIMARY KEY,
    label TEXT
);""")
    db.conn.commit()
    # and finally move the data to the new table
    cursor.executemany(
        'INSERT INTO blockchain_accounts(blockchain, account, label) '
        'VALUES (?, ?, ?)',
        account_tuples,
    )
    db.conn.commit()


def upgrade_v10_to_v11(db: 'DBHandler') -> None:
    """Upgrades the DB from v10 to v11

    - Adds the label column to blockchain accounts
    """
    _upgrade_blockchain_accounts_table(db)
