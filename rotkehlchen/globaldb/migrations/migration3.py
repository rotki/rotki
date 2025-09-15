from typing import TYPE_CHECKING

from rotkehlchen.data_migrations.common import migrate_addressbook_none_to_ecosystem_key

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection


def globaldb_data_migration_3(conn: 'DBConnection') -> None:
    """Introduced at 1.40.1: replace 'NONE' with ecosystem-specific key in address_book"""
    migrate_addressbook_none_to_ecosystem_key(connection=conn)
