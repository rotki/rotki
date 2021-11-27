from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v30_to_v31(db: 'DBHandler') -> None:
    """Upgrades the DB from v30 to v31

    - Add the new eth2 validator table and upgrade the old ones to have foreign key relationships.
    """
    cursor = db.conn.cursor()
    cursor.execute('DROP TABLE IF EXISTS eth2_deposits;')
    cursor.execute('DROP TABLE IF EXISTS eth2_daily_staking_details;')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_validators (
    validator_index INTEGER NOT NULL PRIMARY KEY,
    public_key TEXT NOT NULL UNIQUE
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_deposits (
    tx_hash BLOB NOT NULL,
    tx_index INTEGER NOT NULL,
    from_address VARCHAR[42] NOT NULL,
    timestamp INTEGER NOT NULL,
    pubkey TEXT NOT NULL,
    withdrawal_credentials TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    FOREIGN KEY(pubkey) REFERENCES eth2_validators(public_key) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(tx_hash, pubkey, amount) /* multiple deposits can exist for same pubkey */
);
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth2_daily_staking_details (
    validator_index INTEGER NOT NULL,
    timestamp integer NOT NULL,
    start_usd_price TEXT NOT NULL,
    end_usd_price TEXT NOT NULL,
    pnl TEXT NOT NULL,
    start_amount TEXT NOT NULL,
    end_amount TEXT NOT NULL,
    missed_attestations INTEGER,
    orphaned_attestations INTEGER,
    proposed_blocks INTEGER,
    missed_blocks INTEGER,
    orphaned_blocks INTEGER,
    included_attester_slashings INTEGER,
    proposer_attester_slashings INTEGER,
    deposits_number INTEGER,
    amount_deposited TEXT,
    FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (validator_index, timestamp));""")  # noqa: E501
    db.conn.commit()
