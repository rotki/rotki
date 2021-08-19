from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v28_to_v29(db: 'DBHandler') -> None:
    """Upgrades the DB from v28 to v29

    - Alters the primary key of blockchain accounts to be blockchain type + account
    """
    cursor = db.conn.cursor()
    query = cursor.execute('SELECT blockchain, account, label FROM blockchain_accounts;')
    accounts_data = query.fetchall()
    cursor.execute('DROP TABLE IF EXISTS blockchain_accounts;')
    # create the new table and insert all values into it
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blockchain_accounts (
    blockchain VARCHAR[24] NOT NULL,
    account TEXT NOT NULL,
    label TEXT,
    PRIMARY KEY (blockchain, account)
    );
    """)
    cursor.executemany(
        'INSERT INTO blockchain_accounts(blockchain, account, label) VALUES(?, ?, ?);',
        accounts_data,
    )
    db.conn.commit()
