import glob
import json
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def get_or_make_price_history_dir(data_directory: Path) -> Path:
    price_history_dir = data_directory / 'price_history'
    price_history_dir.mkdir(parents=True, exist_ok=True)
    return price_history_dir


def _create_new_tables(db: 'DBHandler') -> None:
    """Create new tables added in this upgrade"""
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS yearn_vaults_events (
    address VARCHAR[42] NOT NULL,
    event_type VARCHAR[10] NOT NULL,
    from_asset TEXT NOT NULL,
    from_amount TEXT NOT NULL,
    from_usd_value TEXT NOT NULL,
    to_asset TEXT NOT NULL,
    to_amount TEXT NOT NULL,
    to_usd_value TEXT NOT NULL,
    pnl_amount TEXT,
    pnl_usd_value TEXT,
    block_number INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    tx_hash VARCHAR[66] NOT NULL,
    log_index INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (event_type, tx_hash, log_index)
    );""")
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS ledger_action_type (
    type    CHAR(1)       PRIMARY KEY NOT NULL,
    seq     INTEGER UNIQUE
    );
    /* Income Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('A', 1);
    /* Expense Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('B', 2);
    /* Loss Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('C', 3);
    /* Dividends Income Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('D', 4);
    /* Donation Received Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('E', 5);
    /* Airdrop Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('F', 6);
    /* Gift Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('G', 7);
    /* Grant Action Type */
    INSERT OR IGNORE INTO ledger_action_type(type, seq) VALUES ('H', 8);""")
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS ledger_actions (
    identifier INTEGER NOT NULL PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    type CHAR(1) NOT NULL DEFAULT('A') REFERENCES ledger_action_type(type),
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    amount TEXT NOT NULL,
    asset TEXT NOT NULL,
    rate TEXT,
    rate_asset TEXT,
    link TEXT,
    notes TEXT,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    FOREIGN KEY(rate_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
    );""")


def upgrade_v22_to_v23(db: 'DBHandler') -> None:
    """Upgrades the DB from v22 to v23

    - Migrates the settings entries 'thousand_separator', 'decimal_separator'
    and 'currency_location' into the 'frontend_settings' entry.
    - Deletes Bitfinex trades and their used query range, so trades can be
    populated again with the right `fee_asset`.
    - Delete all cryptocompare price cache files. Move forex price cache to price_history directory
    """
    settings = ('"thousand_separator"', '"decimal_separator"', '"currency_location"')
    cursor = db.conn.cursor()
    # Get the settings and put them in a dict
    setting_value_map = dict(
        cursor.execute(
            f'SELECT name, value FROM settings WHERE name IN ({",".join(settings)});',
        ).fetchall(),
    )
    # If the settings exist, migrate them into the 'frontend_settings' entry
    if setting_value_map:
        frontend_settings = cursor.execute(
            'SELECT value FROM settings WHERE name = "frontend_settings";',
        ).fetchone()

        if frontend_settings is not None:
            setting_value_map.update(json.loads(frontend_settings[0]))

        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('frontend_settings', json.dumps(setting_value_map)),
        )
    # Delete the settings
    cursor.execute(f'DELETE FROM settings WHERE name IN ({",".join(settings)});')
    # Delete Bitfinex used_query_ranges
    cursor.execute('DELETE FROM used_query_ranges WHERE name = "bitfinex_trades";')
    # Delete Bitfinex trades
    cursor.execute('DELETE FROM trades WHERE location = "T";')
    # Delete deprecated historical data start setting
    cursor.execute('DELETE from settings WHERE name="historical_data_start";')
    _create_new_tables(db)
    db.conn.commit()

    # -- Now move forex history to the new directory and remove all old cache files
    # We botched this. Should have been forex_history_file.json -> price_history_forex.json
    # and not the other way around
    data_directory = db.user_data_dir.parent
    price_history_dir = get_or_make_price_history_dir(data_directory)
    forex_history_file = data_directory / 'price_history_forex.json'
    if forex_history_file.is_file():
        shutil.move(
            forex_history_file,  # type: ignore
            price_history_dir / 'forex_history_file.json',
        )

    prefix = os.path.join(str(data_directory), 'price_history_')
    prefix = prefix.replace('\\', '\\\\')
    files_list = glob.glob(prefix + '*.json')
    for file_ in files_list:
        file_ = file_.replace('\\\\', '\\')
        try:
            Path(file_).unlink()
        except OSError:
            pass
