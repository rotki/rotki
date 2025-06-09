from typing import TYPE_CHECKING

from rotkehlchen.db.upgrades.utils import fix_address_book_duplications
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


@enter_exit_debug_log(name='globaldb v8->v9 upgrade')
def migrate_to_v9(connection: 'DBConnection', progress_handler: 'DBUpgradeProgressHandler') -> None:  # noqa: E501
    """This globalDB upgrade does the following:
    - make the blockchain column not nullable since we use `NONE` as string

    This upgrade takes place in v1.35.0"""
    @progress_step('Fixing addressbook duplications.')
    def _addressbook_schema_update(write_cursor: 'DBCursor') -> None:
        """Make the blockchain column to a non nullable column for address_book"""
        fix_address_book_duplications(write_cursor=write_cursor)

    @progress_step('Enabling uniswap v2, v3 as history sources.')
    def _add_uniswap_to_price_history_source_types(write_cursor: 'DBCursor') -> None:
        """Add entries for Uniswap V2 and V3 to price_history_source_types table"""
        write_cursor.executemany(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?);',
            [('G', 7), ('H', 8)],
        )

    @progress_step('Removing bad curve cache entries.')
    def _remove_bad_cache_entries(write_cursor: 'DBCursor') -> None:
        """Removes entries from the globaldb cache for curve pools that might be keeping
        an invalid last_queried_ts.
        """
        write_cursor.execute(
            'DELETE FROM general_cache WHERE last_queried_ts=0 AND key LIKE ? ESCAPE ?',
            ('CURVE\\_LP\\_TOKENS%', '\\'),
        )

    @progress_step('Removing underlying tokens pointing to themselves.')
    def _remove_own_underlying_tokens(write_cursor: 'DBCursor') -> None:
        """Moved here from userdb (lol) migration 16 (v1.34.2)

        Removes the underlying token entries from the global DB that have themselves
        as the underlying token.
        """
        write_cursor.execute(
            'DELETE FROM underlying_tokens_list WHERE identifier=parent_token_entry;',
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
