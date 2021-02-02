import json
from typing import TYPE_CHECKING
from rotkehlchen.utils.misc import get_or_make_price_history_dir
import os
from pathlib import Path
import glob
import shutil

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


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
