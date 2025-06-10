"""Repository for database connection management operations."""
import logging
from pathlib import Path
from typing import Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants.misc import USERDB_NAME
from rotkehlchen.db.constants import TRANSIENT_DB_NAME
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType
from rotkehlchen.db.misc import detect_sqlcipher_version
from rotkehlchen.db.utils import protect_password_sqlcipher
from rotkehlchen.errors.api import AuthenticationError
from rotkehlchen.errors.misc import SystemPermissionError

log = logging.getLogger(__name__)

KDF_ITER = 64000


class ConnectionManagementRepository:
    """Repository for handling database connection management operations."""

    def __init__(self, user_data_dir: Path, sql_vm_instructions_cb: int) -> None:
        """Initialize the connection management repository."""
        self.user_data_dir = user_data_dir
        self.sql_vm_instructions_cb = sql_vm_instructions_cb
        self.sqlcipher_version = detect_sqlcipher_version()

    def connect(
            self,
            password: str,
            conn_attribute: Literal['conn', 'conn_transient'] = 'conn',
    ) -> DBConnection:
        """Connect to the DB using password

        May raise:
        - SystemPermissionError if we are unable to open the DB file,
        probably due to permission errors
        - AuthenticationError if the given password is not the right one for the DB
        """
        if conn_attribute == 'conn':
            fullpath = self.user_data_dir / USERDB_NAME
            connection_type = DBConnectionType.USER
        else:
            fullpath = self.user_data_dir / TRANSIENT_DB_NAME
            connection_type = DBConnectionType.TRANSIENT
        try:
            conn = DBConnection(
                path=str(fullpath),
                connection_type=connection_type,
                sql_vm_instructions_cb=self.sql_vm_instructions_cb,
            )
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            raise SystemPermissionError(
                f'Could not open database file: {fullpath}. Permission errors?',
            ) from e

        password_for_sqlcipher = protect_password_sqlcipher(password)
        script = f"PRAGMA key='{password_for_sqlcipher}';"
        if self.sqlcipher_version == 3:
            script += f'PRAGMA kdf_iter={KDF_ITER};'
        try:
            conn.executescript(script)
            conn.execute('PRAGMA foreign_keys=ON')
            # Optimizations for the combined trades view
            # the following will fail with DatabaseError in case of wrong password.
            # If this goes away at any point it needs to be replaced by something
            # that checks the password is correct at this same point in the code
            conn.execute('PRAGMA cache_size = -32768')
            # switch to WAL mode: https://www.sqlite.org/wal.html
            conn.execute('PRAGMA journal_mode=WAL;')
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            conn.close()
            raise AuthenticationError(
                'Wrong password or invalid/corrupt database for user',
            ) from e

        return conn

    def change_password(
            self,
            conn: DBConnection,
            new_password: str,
            conn_attribute: Literal['conn', 'conn_transient'],
    ) -> bool:
        """Change the password for a database connection."""
        new_password_for_sqlcipher = protect_password_sqlcipher(new_password)
        script = f"PRAGMA rekey='{new_password_for_sqlcipher}';"
        if self.sqlcipher_version == 3:
            script += f'PRAGMA kdf_iter={KDF_ITER};'
        try:
            conn.executescript(script)
        except sqlcipher.OperationalError as e:  # pylint: disable=no-member
            log.error(
                f'At change password could not re-key the open {conn_attribute} '
                f'database: {e!s}',
            )
            return False
        return True

    @staticmethod
    def disconnect(conn: DBConnection | None) -> None:
        """Disconnect from the database."""
        if conn:
            conn.close()
