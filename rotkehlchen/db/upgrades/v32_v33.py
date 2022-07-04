from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


def _refactor_xpubs_and_xpub_mappings(cursor: 'DBCursor') -> None:
    # Keep a copy of the xpub_mappings because it will get deleted once
    # xpubs table is dropped.
    xpub_mappings = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
    cursor.execute("""
    CREATE TABLE xpubs_copy (
        xpub TEXT NOT NULL,
        derivation_path TEXT NOT NULL,
        label TEXT,
        blockchain TEXT NOT NULL,
        PRIMARY KEY (xpub, derivation_path, blockchain)
    );
    """)
    cursor.execute("""
    INSERT INTO xpubs_copy(xpub, derivation_path, label, blockchain)
    SELECT xpub, derivation_path, label, 'BTC' FROM xpubs;
    """)
    cursor.execute('DROP TABLE xpubs;')
    cursor.execute('ALTER TABLE xpubs_copy RENAME TO xpubs;')

    # Now populate the xpub_mappings table with its previous data
    # and set `blockchain` column to NOT NULL
    cursor.execute("""
    CREATE TABLE xpub_mappings_copy (
        address TEXT NOT NULL,
        xpub TEXT NOT NULL,
        derivation_path TEXT NOT NULL,
        account_index INTEGER,
        derived_index INTEGER,
        blockchain TEXT NOT NULL,
        FOREIGN KEY(blockchain, address)
        REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
        FOREIGN KEY(xpub, derivation_path, blockchain) REFERENCES xpubs(
            xpub,
            derivation_path,
            blockchain
        ) ON DELETE CASCADE
        PRIMARY KEY (address, xpub, derivation_path)
    );
    """)
    cursor.executemany("""
    INSERT INTO xpub_mappings_copy(
        address,
        xpub,
        derivation_path,
        account_index,
        derived_index,
        blockchain
    )
    VALUES(?, ?, ?, ?, ?, ?);
    """, xpub_mappings)
    cursor.execute('DROP TABLE xpub_mappings;')
    cursor.execute('ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings;')


def _create_new_tables(cursor: 'DBCursor') -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS address_book (
        address TEXT NOT NULL,
        blockchain TEXT NOT NULL DEFAULT "ETH",
        name TEXT NOT NULL,
        PRIMARY KEY(address, blockchain)
    );
""")


def _create_nodes(cursor: 'DBCursor') -> None:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS web3_nodes(
        name TEXT NOT NULL PRIMARY KEY,
        address TEXT NOT NULL,
        owned BOOLEAN NOT NULL DEFAULT FALSE
    );
""")
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("etherscan", "", FALSE)')  # noqa: E501
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("mycrypto", "https://api.mycryptoapi.com/eth", FALSE);')  # noqa: E501
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("blockscout", "https://mainnet-nethermind.blockscout.com/", FALSE);')  # noqa: E501
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("avado pool", "https://mainnet.eth.cloud.ava.do/", FALSE);')  # noqa: E501
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("1inch", "https://web3.1inch.exchange", FALSE);')  # noqa: E501
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("myetherwallet", "https://nodes.mewapi.io/rpc/eth", FALSE);')  # noqa: E501
    cursor.execute('INSERT OR IGNORE INTO web3_nodes(name, address, owned) VALUES ("cloudflare", "https://cloudflare-eth.com/", FALSE);')  # noqa: E501


def _refactor_blockchain_account_labels(cursor: 'DBCursor') -> None:
    cursor.execute('UPDATE blockchain_accounts SET label = NULL WHERE label = ""')


def upgrade_v32_to_v33(db: 'DBHandler') -> None:
    """Upgrades the DB from v32 to v33
    - Change the schema of `blockchain` column in `xpub_mappings` table to be required.
    - Add blockchain column to `xpubs` table.
    """
    cursor = db.conn.cursor()
    _refactor_xpubs_and_xpub_mappings(cursor)
    _create_new_tables(cursor)
    _refactor_blockchain_account_labels(cursor)
    _create_nodes(cursor)
    db.conn.commit()
