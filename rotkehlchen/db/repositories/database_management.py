"""Repository for managing database operations."""
import json
import logging
import os
import re
import typing
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants.misc import USERDB_NAME
from rotkehlchen.errors.api import RotkehlchenPermissionError
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

log = logging.getLogger(__name__)

DB_BACKUP_RE = re.compile(r'(\d+)_rotkehlchen_db_v(\d+).backup')


class DatabaseManagementRepository:
    """Repository for handling database management operations."""

    def __init__(self, user_data_dir: Path, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the database management repository."""
        self.user_data_dir = user_data_dir
        self.msg_aggregator = msg_aggregator

    def export_unencrypted(
            self,
            conn: 'DBConnection',
            tempdbpath: Path,
    ) -> Path:
        """Export the unencrypted DB to the temppath as plaintext DB

        The critical section is absolutely needed as a context switch
        from inside this execute script can result in:
        1. coming into this code again from another greenlet which can result
        to DB plaintext already in use
        2. Having a DB transaction open between the attach and detach and not
        closed when we detach which will result in DB plaintext locked.

        Returns the Path of the new temp DB file
        """
        with conn.critical_section():
            # flush the wal file to have up to date information when exporting data
            conn.execute('PRAGMA wal_checkpoint;')
            conn.executescript(
                f"ATTACH DATABASE '{tempdbpath}' AS plaintext KEY '';"
                "SELECT sqlcipher_export('plaintext');"
                "DETACH DATABASE plaintext;",
            )
        return tempdbpath

    def create_db_backup(self, conn: 'DBConnection', version: int) -> Path:
        """Create a backup of the database.

        May raise:
        - OSError
        """
        new_db_filename = f'{ts_now()}_rotkehlchen_db_v{version}.backup'
        new_db_path = self.user_data_dir / new_db_filename
        import shutil
        shutil.copyfile(
            self.user_data_dir / USERDB_NAME,
            new_db_path,
        )
        return new_db_path

    def add_skipped_external_event(
            self,
            write_cursor: 'DBCursor',
            location: Location,
            data: dict[str, Any],
            extra_data: dict[str, Any] | None,
    ) -> None:
        """Add a skipped external event to the DB. Duplicates are ignored."""
        serialized_extra_data = None
        if extra_data is not None:
            serialized_extra_data = json.dumps(extra_data, separators=(',', ':'))
        write_cursor.execute(
            'INSERT OR IGNORE INTO skipped_external_events(data, location, extra_data) VALUES(?, ?, ?)',  # noqa: E501
            (json.dumps(data, separators=(',', ':')), location.serialize_for_db(), serialized_extra_data),  # noqa: E501
        )

    def get_db_info(self, version: int) -> dict[str, Any]:
        """Get database info including path, size and version."""
        filepath = self.user_data_dir / USERDB_NAME
        size = Path(self.user_data_dir / USERDB_NAME).stat().st_size
        return {
            'filepath': str(filepath),
            'size': int(size),
            'version': int(version),
        }

    def get_backups(self) -> list[dict[str, Any]]:
        """Returns a list of tuples with possible backups of the user DB"""
        backups = []
        for root, _, files in os.walk(self.user_data_dir):
            for filename in files:
                match = DB_BACKUP_RE.search(filename)
                if match:
                    timestamp = match.group(1)
                    version = match.group(2)
                    try:
                        size: int | None = Path(Path(root) / filename).stat().st_size
                    except OSError:
                        size = None
                    backups.append({
                        'time': int(timestamp),
                        'version': int(version),
                        'size': size,
                    })

        return backups

    def check_unfinished_upgrades(
            self,
            conn: 'DBConnection',
            get_setting_fn: typing.Callable[
                ['DBCursor', typing.Literal['ongoing_upgrade_from_version']], int | None,
            ],
            resume_from_backup: bool,
            disconnect_fn: typing.Callable[[], None],
            connect_fn: typing.Callable[[typing.Literal['conn', 'conn_transient']], None],
    ) -> None:
        """
        Checks the database whether there are any not finished upgrades and automatically uses a
        backup if there are any. If no backup found, throws an error to the user
        """
        with conn.read_ctx() as cursor:
            try:
                ongoing_upgrade_from_version = get_setting_fn(
                    cursor,
                    'ongoing_upgrade_from_version',
                )
            except sqlcipher.OperationalError:  # pylint: disable=no-member
                return  # fresh database. Nothing to upgrade.
        if ongoing_upgrade_from_version is None:
            return  # We are all good

        # if there is an unfinished upgrade, check user approval to resume from backup
        if resume_from_backup is False:
            raise RotkehlchenPermissionError(
                error_message=(
                    'The encrypted database is in a semi upgraded state. '
                    'Either resume from a backup or solve the issue manually.'
                ),
                payload=None,
            )

        # If resume_from_backup is True, the user gave approval.
        # Replace the db with a backup and reconnect
        disconnect_fn()
        backup_postfix = f'rotkehlchen_db_v{ongoing_upgrade_from_version}.backup'
        found_backups = list(filter(
            lambda x: x[-len(backup_postfix):] == backup_postfix,
            os.listdir(self.user_data_dir),
        ))
        if len(found_backups) == 0:
            raise DBUpgradeError(
                f'Your encrypted database is in a half-upgraded state at '
                f'v{ongoing_upgrade_from_version} and there was no backup '
                'found. Please open an issue on our github or contact us in our discord server.',
            )

        backup_to_use = max(found_backups)  # Use latest backup
        import shutil
        shutil.copyfile(
            self.user_data_dir / backup_to_use,
            self.user_data_dir / USERDB_NAME,
        )
        self.msg_aggregator.add_warning(
            f'Your encrypted database was in a half-upgraded state. '
            f'Trying to login with a backup {backup_to_use}',
        )
        connect_fn('conn')
