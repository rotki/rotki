from typing import TYPE_CHECKING
from unittest.mock import patch

from rotkehlchen.data_migrations.manager import MIGRATION_LIST, DataMigrationManager
from rotkehlchen.tests.data_migrations.test_migrations import MockRotkiForMigrations

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def run_single_migration(database: 'DBHandler', migration: int) -> None:
    """Helper function to run a single migration in the migration tests."""
    migration_record = None
    for record in MIGRATION_LIST:
        if record.version == migration:
            migration_record = record
            break

    assert migration_record is not None, f'Migration {migration} not found in MIGRATION_LIST'
    with patch(
        target='rotkehlchen.data_migrations.manager.MIGRATION_LIST',
        new=[migration_record],
    ):
        DataMigrationManager(MockRotkiForMigrations(database)).maybe_migrate_data()
