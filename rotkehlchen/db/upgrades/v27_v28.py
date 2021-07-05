from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v27_to_v28(db: 'DBHandler') -> None:
    """Upgrades the DB from v27 to v28

    - Adds new column to yearn vaults events representing the version of the protocol for the event
    - Deletes aave information due to the addition of aave 2
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
    db.conn.commit()
