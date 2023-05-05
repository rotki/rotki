from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def upgrade_v29_to_v30(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v29 to v30

    - Add category table to manually_tracked_balances
    """
    progress_handler.set_total_steps(1)
    with db.user_write() as cursor:
        # We need to disable foreign_keys to add the table due the following constraint
        # Cannot add a REFERENCES column with non-NULL default value
        cursor.switch_foreign_keys('OFF')
        cursor.execute(
            'ALTER TABLE manually_tracked_balances ADD category '
            "CHAR(1) NOT NULL DEFAULT('A') REFERENCES balance_category(category);",
        )
        cursor.switch_foreign_keys('ON')
        # Insert the new bitpanda location
        cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("b", 34);')
        progress_handler.new_step()
