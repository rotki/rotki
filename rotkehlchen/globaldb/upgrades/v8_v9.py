from typing import TYPE_CHECKING

from rotkehlchen.db.upgrades.utils import fix_address_book_duplications
from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor


@enter_exit_debug_log()
def _addressbook_schema_update(write_cursor: 'DBCursor') -> None:
    """Make the blockchain column to a non nullable column for address_book"""
    fix_address_book_duplications(write_cursor=write_cursor)


@enter_exit_debug_log(name='globaldb v8->v9 upgrade')
def migrate_to_v9(connection: 'DBConnection') -> None:
    """This globalDB upgrade does the following:
    - make the blockchain column not nullable since we use `NONE` as string

    This upgrade takes place in v1.35.0"""
    with connection.write_ctx() as write_cursor:
        _addressbook_schema_update(write_cursor)
