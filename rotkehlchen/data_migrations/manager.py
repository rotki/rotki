import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Optional

from rotkehlchen.data_migrations.migrations.migration_1 import data_migration_1
from rotkehlchen.data_migrations.migrations.migration_2 import data_migration_2
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class MigrationRecord(NamedTuple):
    version: int
    function: Callable
    kwargs: Optional[Dict[str, Any]] = None


MIGRATION_LIST = [
    MigrationRecord(version=1, function=data_migration_1),
    MigrationRecord(version=2, function=data_migration_2),
]


class DataMigrationManager:

    def __init__(self, rotki: 'Rotkehlchen'):
        self.rotki = rotki

    def maybe_migrate_data(self) -> None:
        settings = self.rotki.data.db.get_settings()
        current_migration = settings.last_data_migration
        for migration in MIGRATION_LIST:
            if current_migration < migration.version:
                if self._perform_migration(migration) is False:
                    break  # a migration failed -- no point continuing

                current_migration += 1
                log.debug(f'Successfuly applied migration {current_migration}')
                self.rotki.data.db.conn.cursor().execute(
                    'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                    ('last_data_migration', current_migration),
                )
                self.rotki.data.db.conn.commit()

    def _perform_migration(self, migration: MigrationRecord) -> bool:
        """Performs a single data migration and returns boolean for success/failure"""
        try:
            kwargs = migration.kwargs if migration.kwargs is not None else {}
            migration.function(rotki=self.rotki, **kwargs)
        except BaseException as e:  # lgtm[py/catch-base-exception]
            error = f'Failed to run soft data migration to version {migration.version} due to {str(e)}'  # noqa: E501
            self.rotki.msg_aggregator.add_error(error)
            return False

        return True
