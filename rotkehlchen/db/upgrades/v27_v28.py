from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v27_to_v28(db: 'DBHandler') -> None:
    """Upgrades the DB from v27 to v28

    - Adds new column to yearn vaults events representing the version of the protocol for the event
    - Deletes aave information due to the addition of aave 2
    - Adds the Gitcoin tables
    """
    cursor = db.conn.cursor()
    cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master WHERE type="yearn_vaults_events" AND name="version"',
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'ALTER TABLE yearn_vaults_events ADD COLUMN version INTEGER NOT NULL DEFAULT 1;',
        )
    db.delete_aave_data()
    # Create the gitcoin tables that are added in this DB version
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS gitcoin_tx_type (
    type    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );
    /* Ethereum Transaction */
    INSERT OR IGNORE INTO gitcoin_tx_type(type, seq) VALUES ('A', 1);
    /* ZKSync Transaction */
    INSERT OR IGNORE INTO gitcoin_tx_type(type, seq) VALUES ('B', 2);

    CREATE TABLE IF NOT EXISTS ledger_actions_gitcoin_data (
    parent_id INTEGER NOT NULL,
    tx_id TEXT NOT NULL UNIQUE,
    grant_id INTEGER NOT NULL,
    clr_round INTEGER,
    tx_type NOT NULL DEFAULT('A') REFERENCES gitcoin_tx_type(type),
    FOREIGN KEY(parent_id) REFERENCES ledger_actions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY(parent_id, tx_id, grant_id)
    );

    CREATE TABLE IF NOT EXISTS gitcoin_grant_metadata (
    grant_id INTEGER NOT NULL PRIMARY KEY,
    grant_name TEXT NOT NULL,
    created_on INTEGER NOT NULL
    );""")  # noqa: E501
    db.conn.commit()
