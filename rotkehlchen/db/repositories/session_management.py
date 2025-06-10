"""Repository for session management operations."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.db.dbhandler import DBINFO_FILENAME
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.utils.hashing import file_md5
from rotkehlchen.utils.serialization import rlk_jsondumps

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

log = logging.getLogger(__name__)


class SessionManagementRepository:
    """Repository for handling session management operations."""

    def __init__(self, db_handler: 'DBHandler') -> None:
        """Initialize the session management repository."""
        self.db = db_handler

    def logout(self) -> None:
        """Logout from the database and save dbinfo."""
        self.db.password = ''
        if self.db.conn is not None:
            self.db.disconnect(conn_attribute='conn')
        if self.db.conn_transient is not None:
            self.db.disconnect(conn_attribute='conn_transient')
        try:
            dbinfo = {
                'sqlcipher_version': self.db.sqlcipher_version,
                'md5_hash': self.db.get_md5hash(),
            }
        except (SystemPermissionError, FileNotFoundError) as e:
            # If there is problems opening the DB at destruction just log and exit
            log.error(f'At DB teardown could not open the DB: {e!s}')
            return

        Path(self.db.user_data_dir / DBINFO_FILENAME).write_text(
            rlk_jsondumps(dbinfo), encoding='utf8',
        )