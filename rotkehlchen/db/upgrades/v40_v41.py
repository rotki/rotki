import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _add_cache_table(write_cursor: 'DBCursor') -> None:
    """Add a new key-value cache table for this upgrade"""
    log.debug('Enter _add_cache_table')
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS key_value_cache (
        name TEXT NOT NULL PRIMARY KEY,
        value TEXT
    );""")
    log.debug('Exit _add_cache_table')


def _move_non_settings_mappings_to_cache(write_cursor: 'DBCursor') -> None:
    """Move the non-settings value from `settings` to a seperate `key_value_cache` table"""
    log.debug('Enter _move_non_settings_mappings_to_cache')
    settings_moved = (
        'last_balance_save',
        'last_data_upload_ts',
        'last_data_updates_ts',
        'last_owned_assets_update',
        'last_evm_accounts_detect_ts',
        'last_spam_assets_detect_key',
        'last_augmented_spam_assets_detect_key',
    )
    movable_settings = write_cursor.execute(
        f'SELECT name, value FROM settings WHERE name IN ({",".join(["?"] * len(settings_moved))});',  # noqa: E501
        settings_moved,
    ).fetchall()
    write_cursor.executemany(
        'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES(?, ?);',
        movable_settings,
    )
    write_cursor.execute(
        f'DELETE FROM settings WHERE name IN ({",".join(["?"] * len(movable_settings))});',
        [setting[0] for setting in movable_settings],
    )
    log.debug('Exit _move_non_settings_mappings_to_cache')


def maybe_move_value(write_cursor: 'DBCursor', pattern: str) -> None:
    """An auxiliary function to move `name` and `end_ts` from `used_query_ranges` table to
    `key_value_cache` table if it matches the given pattern"""
    rows = write_cursor.execute(
        'SELECT name, end_ts FROM used_query_ranges WHERE name LIKE ?',
        (pattern, ),
    ).fetchall()
    if len(rows) != 0:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO key_value_cache(name, value) VALUES(?, ?);', rows,
        )
        write_cursor.executemany(
            'DELETE FROM used_query_ranges WHERE name = ?', [(row[0],) for row in rows],
        )


def _move_non_intervals_from_used_query_ranges_to_cache(write_cursor: 'DBCursor') -> None:
    """Move timestamps that are not ranges from `used_query_ranges` to the `key_value_cache` table"""  # noqa: E501
    log.debug('Enter _move_non_intervals_from_used_query_ranges_to_cache')
    value_patterns = {
        '{pattern}%': (  # to match patterns with prefixes
            'ethwithdrawalsts_',
            'ethwithdrawalsidx_',
        ),
        '%{pattern}': (  # to match patterns with suffixes
            '_last_cryptotx_offset',
            '_last_query_ts',
            '_last_query_id',
        ),
        '{pattern}': (  # to match patterns as exact names
            'last_produced_blocks_query_ts',
            'last_withdrawals_exit_query_ts',
            'last_events_processing_task_ts',
        ),
    }
    for key, patterns in value_patterns.items():
        for pattern in patterns:
            maybe_move_value(write_cursor, key.format(pattern=pattern))
    log.debug('Exit _move_non_intervals_from_used_query_ranges_to_cache')


def _add_new_supported_locations(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _add_new_supported_locations')
    write_cursor.execute(
        'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
        ('m', 45),
    )
    log.debug('Exit _add_new_supported_locations')


def upgrade_v40_to_v41(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v40 to v41. This was in v1.32 release.

        - Create a new table for key-value cache
        - Move non-settings and non-used query ranges to the new cache
        - Add new supported locations
    """
    log.debug('Enter userdb v40->v41 upgrade')
    progress_handler.set_total_steps(4)
    with db.user_write() as write_cursor:
        _add_cache_table(write_cursor)
        progress_handler.new_step()
        _move_non_settings_mappings_to_cache(write_cursor)
        progress_handler.new_step()
        _move_non_intervals_from_used_query_ranges_to_cache(write_cursor)
        progress_handler.new_step()
        _add_new_supported_locations(write_cursor)
    progress_handler.new_step()

    log.debug('Finish userdb v40->v41 upgrade')
