from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def upgrade_v27_to_v28(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v27 to v28

    - Adds new column to yearn vaults events representing the version of the protocol for the event
    - Deletes aave information due to the addition of aave 2
    - Adds the Gitcoin tables
    """
    progress_handler.set_total_steps(3)
    with db.user_write() as cursor:
        progress_handler.new_step(name='Adding version column to yearn vaults table.')
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='yearn_vaults_events' AND name='version'",  # noqa: E501
        )
        if cursor.fetchone()[0] == 0:  # should return a value here
            cursor.execute(
                'ALTER TABLE yearn_vaults_events ADD COLUMN version INTEGER NOT NULL DEFAULT 1;',
            )

        progress_handler.new_step(name='Removing Aave data due to addition of Aave 2.')
        cursor.execute('DELETE FROM aave_events;')
        cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
            ('aave\\_events%', '\\'),
        )

        progress_handler.new_step(name='Creating Gitcoin tables.')
        # Create the gitcoin tables that are added in this DB version
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gitcoin_tx_type (
        type    CHAR(1)       PRIMARY KEY NOT NULL,
        seq     INTEGER UNIQUE
        )""")
        # Ethereum Transaction
        cursor.execute("INSERT OR IGNORE INTO gitcoin_tx_type(type, seq) VALUES ('A', 1)")
        # ZKSync Transaction
        cursor.execute("INSERT OR IGNORE INTO gitcoin_tx_type(type, seq) VALUES ('B', 2)")

        cursor.execute("""CREATE TABLE IF NOT EXISTS ledger_actions_gitcoin_data (
        parent_id INTEGER NOT NULL,
        tx_id TEXT NOT NULL UNIQUE,
        grant_id INTEGER NOT NULL,
        clr_round INTEGER,
        tx_type NOT NULL DEFAULT('A') REFERENCES gitcoin_tx_type(type),
        FOREIGN KEY(parent_id) REFERENCES ledger_actions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
        PRIMARY KEY(parent_id, tx_id, grant_id)
        )""")  # noqa: E501

        cursor.execute("""CREATE TABLE IF NOT EXISTS gitcoin_grant_metadata (
        grant_id INTEGER NOT NULL PRIMARY KEY,
        grant_name TEXT NOT NULL,
        created_on INTEGER NOT NULL
        )""")
