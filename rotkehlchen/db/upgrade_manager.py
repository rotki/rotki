import logging
import os
import shutil
import traceback
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants.misc import USERDB_NAME
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.upgrades.v26_v27 import upgrade_v26_to_v27
from rotkehlchen.db.upgrades.v27_v28 import upgrade_v27_to_v28
from rotkehlchen.db.upgrades.v28_v29 import upgrade_v28_to_v29
from rotkehlchen.db.upgrades.v29_v30 import upgrade_v29_to_v30
from rotkehlchen.db.upgrades.v30_v31 import upgrade_v30_to_v31
from rotkehlchen.db.upgrades.v31_v32 import upgrade_v31_to_v32
from rotkehlchen.db.upgrades.v32_v33 import upgrade_v32_to_v33
from rotkehlchen.db.upgrades.v33_v34 import upgrade_v33_to_v34
from rotkehlchen.db.upgrades.v34_v35 import upgrade_v34_to_v35
from rotkehlchen.db.upgrades.v35_v36 import upgrade_v35_to_v36
from rotkehlchen.db.upgrades.v36_v37 import upgrade_v36_to_v37
from rotkehlchen.db.upgrades.v37_v38 import upgrade_v37_to_v38
from rotkehlchen.db.upgrades.v38_v39 import upgrade_v38_to_v39
from rotkehlchen.db.upgrades.v39_v40 import upgrade_v39_to_v40
from rotkehlchen.db.upgrades.v40_v41 import upgrade_v40_to_v41
from rotkehlchen.db.upgrades.v41_v42 import upgrade_v41_to_v42
from rotkehlchen.db.upgrades.v42_v43 import upgrade_v42_to_v43
from rotkehlchen.db.upgrades.v43_v44 import upgrade_v43_to_v44
from rotkehlchen.db.upgrades.v44_v45 import upgrade_v44_to_v45
from rotkehlchen.db.upgrades.v45_v46 import upgrade_v45_to_v46
from rotkehlchen.db.upgrades.v46_v47 import upgrade_v46_to_v47
from rotkehlchen.db.upgrades.v47_v48 import upgrade_v47_to_v48
from rotkehlchen.db.upgrades.v48_v49 import upgrade_v48_to_v49
from rotkehlchen.db.upgrades.v49_v50 import upgrade_v49_to_v50
from rotkehlchen.db.upgrades.v50_v51 import upgrade_v50_to_v51
from rotkehlchen.db.upgrades.v51_v52 import upgrade_v51_to_v52
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.upgrades import DBUpgradeProgressHandler, UpgradeRecord

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

MIN_SUPPORTED_USER_DB_VERSION = 26

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


UPGRADES_LIST = [
    UpgradeRecord(from_version=26, function=upgrade_v26_to_v27),
    UpgradeRecord(from_version=27, function=upgrade_v27_to_v28),
    UpgradeRecord(from_version=28, function=upgrade_v28_to_v29),
    UpgradeRecord(from_version=29, function=upgrade_v29_to_v30),
    UpgradeRecord(from_version=30, function=upgrade_v30_to_v31),
    UpgradeRecord(from_version=31, function=upgrade_v31_to_v32),
    UpgradeRecord(from_version=32, function=upgrade_v32_to_v33),
    UpgradeRecord(from_version=33, function=upgrade_v33_to_v34),
    UpgradeRecord(from_version=34, function=upgrade_v34_to_v35),
    UpgradeRecord(from_version=35, function=upgrade_v35_to_v36),
    UpgradeRecord(from_version=36, function=upgrade_v36_to_v37),
    UpgradeRecord(from_version=37, function=upgrade_v37_to_v38),
    UpgradeRecord(from_version=38, function=upgrade_v38_to_v39),
    UpgradeRecord(from_version=39, function=upgrade_v39_to_v40),
    UpgradeRecord(from_version=40, function=upgrade_v40_to_v41),
    UpgradeRecord(from_version=41, function=upgrade_v41_to_v42),
    UpgradeRecord(from_version=42, function=upgrade_v42_to_v43),
    UpgradeRecord(from_version=43, function=upgrade_v43_to_v44),
    UpgradeRecord(from_version=44, function=upgrade_v44_to_v45),
    UpgradeRecord(from_version=45, function=upgrade_v45_to_v46),
    UpgradeRecord(from_version=46, function=upgrade_v46_to_v47),
    UpgradeRecord(from_version=47, function=upgrade_v47_to_v48),
    UpgradeRecord(from_version=48, function=upgrade_v48_to_v49),
    UpgradeRecord(from_version=49, function=upgrade_v49_to_v50),
    UpgradeRecord(from_version=50, function=upgrade_v50_to_v51),
    UpgradeRecord(from_version=51, function=upgrade_v51_to_v52),
]


class DBUpgradeManager:
    """Separate class to manage DB upgrades/migrations"""

    def __init__(self, db: 'DBHandler'):
        self.db = db

    def run_upgrades(self) -> bool:
        """Run all required database upgrades

        Returns true for fresh database and false otherwise.

        May raise:
        - DBUpgradeError if the user uses a newer version than the one we
        upgrade to or if there is a problem during upgrade or if the version is older
        than the one supported.
        """
        with self.db.conn.write_ctx() as cursor:
            try:
                our_version = self.db.get_setting(cursor, 'version')
            except sqlcipher.OperationalError:  # pylint: disable=no-member
                return True  # fresh database. Nothing to upgrade.

            if our_version < MIN_SUPPORTED_USER_DB_VERSION:
                raise DBUpgradeError(
                    f'Your account was last opened by a very old version of rotki and its '
                    f'version is {our_version}. To be able to use it you will need to '
                    f'first use a previous version of rotki and then use this one. '
                    f'Refer to the documentation for more information. '
                    f'https://docs.rotki.com/usage-guides#upgrading-rotki-after-a-long-time',
                )

            if our_version > ROTKEHLCHEN_DB_VERSION:
                raise DBUpgradeError(
                    'Your database version is newer than the version expected by the '
                    'executable. Did you perhaps try to revert to an older rotki version? '
                    'Please only use the latest version of the software.',
                )

        progress_handler = DBUpgradeProgressHandler(
            messages_aggregator=self.db.msg_aggregator,
            target_version=ROTKEHLCHEN_DB_VERSION,
        )
        for upgrade in UPGRADES_LIST:
            self._perform_single_upgrade(upgrade, progress_handler)

        # Finally make sure to always have latest version in the DB
        with self.db.user_write() as cursor:
            self.db.set_setting(cursor, name='version', value=ROTKEHLCHEN_DB_VERSION)
        return False

    def _perform_single_upgrade(
            self,
            upgrade: UpgradeRecord,
            progress_handler: DBUpgradeProgressHandler,
    ) -> None:
        """
        This is the wrapper function that performs each DB upgrade

        The logic is:
            1. Check version, if not at from_version get out.
            2. If at from_version make a DB backup before performing the upgrade
            3. Perform the upgrade action
            4. If something went wrong during upgrade restore backup and quit
            5. If all went well set version and delete the backup

        We do a WAL checkpoint at the start. That blocks until there is no database
        writer and all readers are reading from the most recent database snapshot. It
        then checkpoints all frames in the log file and syncs the database file.
        FULL blocks concurrent writers while it is running, but readers can proceed.

        Reason for this is to make sure the .db file is the only thing needed for the DB
        backup as we only copy that file.
        """
        self.db.conn.wal_checkpoint('(FULL)')
        with self.db.conn.read_ctx() as cursor:
            current_version = self.db.get_setting(cursor, 'version')
        if current_version != upgrade.from_version:
            return
        to_version = upgrade.from_version + 1
        progress_handler.new_round(version=to_version)

        # First make a backup of the DB
        tmp_db_filename = f'{ts_now()}_rotkehlchen_db_v{upgrade.from_version}.backup'
        shutil.copyfile(
            os.path.join(self.db.user_data_dir, USERDB_NAME),
            os.path.join(self.db.user_data_dir, tmp_db_filename),
        )

        # Add a flag to the db that an upgrade is happening
        with self.db.user_write() as write_cursor:
            self.db.set_setting(
                write_cursor=write_cursor,
                name='ongoing_upgrade_from_version',
                value=upgrade.from_version,
            )

        try:
            kwargs = upgrade.kwargs if upgrade.kwargs is not None else {}
            upgrade.function(db=self.db, progress_handler=progress_handler, **kwargs)
        except BaseException as e:
            # Problem .. restore DB backup, log all info and bail out
            error_message = (
                f'Failed at database upgrade from version {upgrade.from_version} to '
                f'{to_version}: {e!s}'
            )
            stacktrace = traceback.format_exc()
            log.error(f'{error_message}\n{stacktrace}')
            shutil.copyfile(
                os.path.join(self.db.user_data_dir, tmp_db_filename),
                os.path.join(self.db.user_data_dir, USERDB_NAME),
            )
            raise DBUpgradeError(error_message) from e

        # Upgrade success all is good - Note: We keep the backups even for success
        with self.db.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM settings WHERE name=?', ('ongoing_upgrade_from_version',))  # noqa: E501
            self.db.set_setting(write_cursor=write_cursor, name='version', value=to_version)
            if to_version >= 41:
                self.db.set_static_cache(write_cursor=write_cursor, name=DBCacheStatic.LAST_DB_UPGRADE, value=ts_now())  # noqa: E501
