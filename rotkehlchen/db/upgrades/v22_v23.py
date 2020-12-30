import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def upgrade_v22_to_v23(db: 'DBHandler') -> None:
    """Upgrades the DB from v22 to v23

    Migrates the settings entries 'thousand_separator', 'decimal_separator' and
    'currency_location' into the 'frontend_settings' entry.
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
        ).fetchone()[0]

        if frontend_settings != '':
            setting_value_map.update(json.loads(frontend_settings))

        cursor.execute(
            'UPDATE settings SET value=? WHERE name=?;',
            (json.dumps(setting_value_map), 'frontend_settings'),
        )
    # Delete the settings
    cursor.execute(f'DELETE from settings WHERE name IN ({",".join(settings)});')
    db.conn.commit()
