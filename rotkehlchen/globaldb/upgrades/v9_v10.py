from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.client import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v9->v10 upgrade')
def migrate_to_v10(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:

    1. Adds main_asset column to asset_collections table.

    This upgrade took place in v1.37
    """

    @progress_step('Adding main_asset column to asset_collections')
    def add_main_asset_column(write_cursor: 'DBCursor') -> None:
        # Disable foreign keys to prevent cascade deletion of multiasset_mappings entries
        write_cursor.executescript('PRAGMA foreign_keys = OFF;')

        collections = write_cursor.execute('SELECT id, name, symbol FROM asset_collections').fetchall()  # noqa: E501
        new_collections = []
        for id_, name, symbol in collections:
            if id_ == 23:
                main_asset = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F'
            elif (main_asset := (write_cursor.execute(
                'SELECT MIN(asset) FROM multiasset_mappings WHERE collection_id = ?',
                (id_,),
            ).fetchone()[0])) is None:  # only aave stableDebtWBTC doesn't have assets in its collection  # noqa: E501
                continue

            new_collections.append((id_, name, symbol, main_asset))

        write_cursor.execute('DROP TABLE asset_collections')
        write_cursor.execute("""
            CREATE TABLE asset_collections(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                main_asset TEXT NOT NULL UNIQUE,
                FOREIGN KEY(main_asset) REFERENCES assets(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
                UNIQUE(name, symbol)
            )
        """)  # noqa: E501
        write_cursor.executemany('INSERT INTO asset_collections VALUES (?, ?, ?, ?)', new_collections)  # noqa: E501
        write_cursor.executescript('PRAGMA foreign_keys = ON;')

    perform_globaldb_upgrade_steps(
        connection=connection,
        progress_handler=progress_handler,
        should_vacuum=True,
    )
