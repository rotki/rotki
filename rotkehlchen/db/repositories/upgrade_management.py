"""Repository for database upgrade management operations."""
from contextlib import suppress
from typing import TYPE_CHECKING, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.schema import DB_SCRIPT_CREATE_TABLES
from rotkehlchen.db.schema_transient import DB_SCRIPT_CREATE_TRANSIENT_TABLES
from rotkehlchen.db.settings import (
    ROTKEHLCHEN_DB_VERSION,
    ROTKEHLCHEN_TRANSIENT_DB_VERSION,
)
from rotkehlchen.db.upgrade_manager import DBUpgradeManager

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor


class UpgradeManagementRepository:
    """Repository for handling database upgrade operations."""

    def __init__(self, db_handler: 'DBHandler') -> None:
        """Initialize the upgrade management repository."""
        self.db = db_handler

    def run_actions_after_first_connection(self) -> None:
        """Perform the actions that are needed after the first DB connection

        Such as:
            - DB Upgrades
            - Create tables that are missing for new version
            - sanity checks

        May raise:
        - AuthenticationError if a wrong password is given or if the DB is corrupt
        - DBUpgradeError if there is a problem with DB upgrading or if the version
        is older than the one supported.
        - DBSchemaError if database schema is malformed.
        """
        # Run upgrades if needed -- only for user DB
        fresh_db = DBUpgradeManager(self.db).run_upgrades()
        if fresh_db:  # create tables during the first run and add the DB version
            self.db.conn.executescript(DB_SCRIPT_CREATE_TABLES)
            cursor = self.db.conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                ('version', str(ROTKEHLCHEN_DB_VERSION)),
            )

        # run checks on the database
        self.db.conn.schema_sanity_check()
        self._check_settings()

        # This logic executes only for the transient db
        self.db._connect(conn_attribute='conn_transient')
        transient_version = 0
        cursor = self.db.conn_transient.cursor()
        with suppress(sqlcipher.DatabaseError):  # pylint: disable=no-member  # not created yet
            result = cursor.execute('SELECT value FROM settings WHERE name=?', ('version',)).fetchone()  # noqa: E501
            if result is not None:
                transient_version = int(result[0])

        if transient_version != ROTKEHLCHEN_TRANSIENT_DB_VERSION:
            # "upgrade" transient DB
            tables = list(cursor.execute("SELECT name FROM sqlite_master WHERE type IS 'table'"))
            cursor.executescript('PRAGMA foreign_keys = OFF;')
            cursor.executescript(';'.join([f'DROP TABLE IF EXISTS {name[0]}' for name in tables]))
            cursor.executescript('PRAGMA foreign_keys = ON;')
        self.db.conn_transient.executescript(DB_SCRIPT_CREATE_TRANSIENT_TABLES)
        cursor.execute(
            'INSERT OR IGNORE INTO settings(name, value) VALUES(?, ?)',
            ('version', str(ROTKEHLCHEN_TRANSIENT_DB_VERSION)),
        )
        self.db.conn_transient.commit()

    def _check_settings(self) -> None:
        """Check that the non_syncing_exchanges setting only has active locations."""
        from rotkehlchen.db.settings import serialize_db_setting
        from rotkehlchen.exchanges.constants import SUPPORTED_EXCHANGES

        with self.db.conn.read_ctx() as cursor:
            non_syncing_exchanges = self.db.get_setting(
                cursor=cursor,
                name='non_syncing_exchanges',
            )

        valid_locations = [
            exchange_location_id
            for exchange_location_id in non_syncing_exchanges
            if exchange_location_id.location in SUPPORTED_EXCHANGES
        ]
        if len(valid_locations) != len(non_syncing_exchanges):
            with self.db.user_write() as write_cursor:
                self.db.set_setting(
                    write_cursor=write_cursor,
                    name='non_syncing_exchanges',
                    value=serialize_db_setting(
                        value=valid_locations,
                        setting='non_syncing_exchanges',
                        is_modifiable=True,
                    ),
                )