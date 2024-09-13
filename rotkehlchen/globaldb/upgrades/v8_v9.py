from typing import TYPE_CHECKING

from rotkehlchen.db.upgrades.utils import fix_address_book_duplications
from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor


@enter_exit_debug_log()
def _addressbook_schema_update(write_cursor: 'DBCursor') -> None:
    """Make the blockchain column to a non nullable column for address_book"""
    fix_address_book_duplications(write_cursor=write_cursor)


@enter_exit_debug_log()
def _add_uniswap_to_price_history_source_types(write_cursor: 'DBCursor') -> None:
    """Add entries for Uniswap V2 and V3 to price_history_source_types table"""
    write_cursor.executemany(
        'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?);',
        [('G', 7), ('H', 8)],
    )


@enter_exit_debug_log()
def _remove_bad_cache_entries(write_cursor: 'DBCursor') -> None:
    """Removes entries from the globaldb cache for curve pools that might be keeping
    an invalid last_queried_ts.
    """
    write_cursor.execute(
        'DELETE FROM general_cache WHERE last_queried_ts=0 AND key LIKE "CURVE_LP_TOKENS%"',
    )


@enter_exit_debug_log(name='globaldb v8->v9 upgrade')
def migrate_to_v9(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - make the blockchain column not nullable since we use `NONE` as string

    This upgrade takes place in v1.35.0"""
    with connection.write_ctx() as write_cursor:
        _addressbook_schema_update(write_cursor)
        _add_uniswap_to_price_history_source_types(write_cursor)
        _remove_bad_cache_entries(write_cursor)
