from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

ICN_NAME = 'yyDAI+yUSDC+yUSDT+yTUSD'


def _create_new_tables(db: 'DBHandler') -> None:
    """Create new tables added in this upgrade"""
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS xpubs (
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    label TEXT,
    PRIMARY KEY (xpub, derivation_path)
    );""")
    db.conn.executescript("""
    CREATE TABLE IF NOT EXISTS xpub_mappings (
    address TEXT NOT NULL,
    xpub TEXT NOT NULL,
    derivation_path TEXT NOT NULL,
    account_index INTEGER,
    derived_index INTEGER,
    FOREIGN KEY(address) REFERENCES blockchain_accounts(account) ON DELETE CASCADE
    FOREIGN KEY(xpub, derivation_path) REFERENCES xpubs(xpub, derivation_path) ON DELETE CASCADE
    PRIMARY KEY (address, xpub, derivation_path)
    );""")  # noqa: E501


def _delete_cached_yusd_icons(db: 'DBHandler') -> None:
    datadir = db.user_data_dir.parent
    icons_dir = datadir / 'icons'
    if not icons_dir.is_dir():
        return

    for size in ('thumb', 'small', 'large'):
        try:
            (icons_dir / f'{ICN_NAME}_{size}.png').unlink()
        except OSError:
            pass


def upgrade_v17_to_v18(db: 'DBHandler') -> None:
    """Upgrades the DB from v17 to v18

    - Deletes all aave historical data and cache to allow for fixes after
    https://github.com/rotki/rotki/issues/1491 to happen immediately
    - Deletes the yyDAI+yUSDC+yUSDT+yTUSD cached icons if existing
    https://github.com/rotki/rotki/issues/1494
    """
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM aave_events;')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')
    _create_new_tables(db)
    db.conn.commit()
    _delete_cached_yusd_icons(db)
