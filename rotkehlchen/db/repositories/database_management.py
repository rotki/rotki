"""Repository for managing database operations."""
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants.misc import USERDB_NAME
from rotkehlchen.db.dbhandler import DBINFO_FILENAME
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.types import Location
from rotkehlchen.utils.hashing import file_md5
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.serialization import rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

log = logging.getLogger(__name__)


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