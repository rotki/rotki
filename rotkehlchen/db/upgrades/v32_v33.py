from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlite3 import Cursor

    from rotkehlchen.db.dbhandler import DBHandler


def _refactor_xpub_mappings(cursor: 'Cursor') -> None:
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
        FOREIGN KEY(xpub, derivation_path) REFERENCES xpubs(
            xpub,
            derivation_path
        ) ON DELETE CASCADE
        PRIMARY KEY (address, xpub, derivation_path)
    );
    """)
    cursor.execute("""
    INSERT INTO xpub_mappings_copy(
        address, xpub,
        derivation_path,
        account_index,
        derived_index,
        blockchain
    )
    SELECT address, xpub, derivation_path, account_index, derived_index, blockchain
    FROM xpub_mappings;
    """)
    cursor.execute('DROP TABLE xpub_mappings;')
    cursor.execute('ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings;')


def upgrade_v32_to_v33(db: 'DBHandler') -> None:
    """Upgrades the DB from v32 to v33
    - Change the schema of `blockchain` column in `xpub_mappings` table to be required.
    """
    cursor = db.conn.cursor()
    _refactor_xpub_mappings(cursor)
    db.conn.commit()
