import logging
import traceback
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple

from rotkehlchen.data_migrations.migrations.migration_1 import data_migration_1
from rotkehlchen.data_migrations.migrations.migration_2 import data_migration_2
from rotkehlchen.data_migrations.migrations.migration_3 import data_migration_3
from rotkehlchen.data_migrations.migrations.migration_5 import data_migration_5
from rotkehlchen.data_migrations.migrations.migration_10 import data_migration_10
from rotkehlchen.data_migrations.migrations.migration_11 import data_migration_11
from rotkehlchen.data_migrations.migrations.migration_20 import data_migration_20
from rotkehlchen.data_migrations.migrations.migration_21 import data_migration_21
from rotkehlchen.data_migrations.migrations.migrations_13 import data_migration_13
from rotkehlchen.data_migrations.migrations.migrations_14 import data_migration_14
from rotkehlchen.data_migrations.migrations.migrations_18 import data_migration_18
from rotkehlchen.data_migrations.migrations.migrations_19 import data_migration_19
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import LAST_DATA_MIGRATION
from .progress import MigrationProgressHandler

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MigrationRecord(NamedTuple):
    version: int
    function: Callable[['Rotkehlchen', MigrationProgressHandler], None]


MIGRATION_LIST = [  # remember to bump LAST_DATA_MIGRATION if editing this
    MigrationRecord(version=1, function=data_migration_1),
    MigrationRecord(version=2, function=data_migration_2),
    MigrationRecord(version=3, function=data_migration_3),
    MigrationRecord(version=5, function=data_migration_5),
    MigrationRecord(version=10, function=data_migration_10),
    MigrationRecord(version=11, function=data_migration_11),
    MigrationRecord(version=13, function=data_migration_13),
    MigrationRecord(version=14, function=data_migration_14),
    MigrationRecord(version=18, function=data_migration_18),
    MigrationRecord(version=19, function=data_migration_19),
    MigrationRecord(version=20, function=data_migration_20),
    MigrationRecord(version=21, function=data_migration_21),
]


class DataMigrationManager:

    def __init__(self, rotki: 'Rotkehlchen'):
        self.rotki = rotki

    def maybe_migrate_data(self) -> None:
        with self.rotki.data.db.conn.read_ctx() as cursor:
            last_migration_version = self.rotki.data.db.get_setting(cursor, 'last_data_migration')

        self.progress_handler = MigrationProgressHandler(
            messages_aggregator=self.rotki.msg_aggregator,
            target_version=LAST_DATA_MIGRATION,
        )
        for migration in MIGRATION_LIST:
            if last_migration_version is not None and last_migration_version < migration.version:
                if self._perform_migration(migration) is False:
                    break  # a migration failed -- no point continuing

                log.debug(f'Successfully applied migration {migration.version}')
                last_migration_version = migration.version
                with self.rotki.data.db.user_write() as write_cursor:
                    write_cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        ('last_data_migration', last_migration_version),
                    )
        else:  # no break -- all migrations completed okay, so remember last one
            with self.rotki.data.db.user_write() as write_cursor:
                write_cursor.execute(  # even if no migration happens we need to remember last one
                    'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                    ('last_data_migration', LAST_DATA_MIGRATION),
                )

    def _perform_migration(self, migration: MigrationRecord) -> bool:
        """Performs a single data migration and returns boolean for success/failure"""
        self.progress_handler.new_round(version=migration.version)
        try:
            migration.function(self.rotki, self.progress_handler)
        except BaseException as e:
            stacktrace = traceback.format_exc()
            error = f'Failed to run soft data migration to version {migration.version} due to {e!s}'  # noqa: E501
            self.rotki.msg_aggregator.add_error(error)
            log.error(f'{error}\n{stacktrace}')
            return False

        return True
