import logging
import os
import shutil
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Optional

from eth_utils.address import to_checksum_address
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.db.asset_rename import rename_assets_in_db
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.upgrades.v5_v6 import upgrade_v5_to_v6
from rotkehlchen.db.upgrades.v6_v7 import upgrade_v6_to_v7
from rotkehlchen.db.upgrades.v7_v8 import upgrade_v7_to_v8
from rotkehlchen.db.upgrades.v8_v9 import upgrade_v8_to_v9
from rotkehlchen.db.upgrades.v10_v11 import upgrade_v10_to_v11
from rotkehlchen.db.upgrades.v11_v12 import upgrade_v11_to_v12
from rotkehlchen.db.upgrades.v12_v13 import upgrade_v12_to_v13
from rotkehlchen.db.upgrades.v13_v14 import upgrade_v13_to_v14
from rotkehlchen.db.upgrades.v14_v15 import upgrade_v14_to_v15
from rotkehlchen.db.upgrades.v15_v16 import upgrade_v15_to_v16
from rotkehlchen.db.upgrades.v16_v17 import upgrade_v16_to_v17
from rotkehlchen.db.upgrades.v17_v18 import upgrade_v17_to_v18
from rotkehlchen.db.upgrades.v18_v19 import upgrade_v18_to_v19
from rotkehlchen.db.upgrades.v19_v20 import upgrade_v19_to_v20
from rotkehlchen.db.upgrades.v20_v21 import upgrade_v20_to_v21
from rotkehlchen.db.upgrades.v21_v22 import upgrade_v21_to_v22
from rotkehlchen.db.upgrades.v22_v23 import upgrade_v22_to_v23
from rotkehlchen.db.upgrades.v23_v24 import upgrade_v23_to_v24
from rotkehlchen.db.upgrades.v24_v25 import upgrade_v24_to_v25
from rotkehlchen.db.upgrades.v25_v26 import upgrade_v25_to_v26
from rotkehlchen.db.upgrades.v26_v27 import upgrade_v26_to_v27
from rotkehlchen.db.upgrades.v27_v28 import upgrade_v27_to_v28
from rotkehlchen.db.upgrades.v28_v29 import upgrade_v28_to_v29
from rotkehlchen.db.upgrades.v29_v30 import upgrade_v29_to_v30
from rotkehlchen.db.upgrades.v30_v31 import upgrade_v30_to_v31
from rotkehlchen.db.upgrades.v31_v32 import upgrade_v31_to_v32
from rotkehlchen.db.upgrades.v32_v33 import upgrade_v32_to_v33
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UpgradeRecord(NamedTuple):
    from_version: int
    function: Callable
    kwargs: Optional[Dict[str, Any]] = None


def _checksum_eth_accounts_v1_to_v2(db: 'DBHandler') -> None:
    """Make sure all eth accounts are checksummed when saved in the DB"""
    cursor = db.conn.cursor()
    query = cursor.execute('SELECT account FROM blockchain_accounts where blockchain=?;', ('ETH',))
    accounts = [x[0] for x in query]
    cursor.execute(
        'DELETE FROM blockchain_accounts WHERE blockchain=?;', ('ETH',),
    )
    db.conn.commit()
    tuples = [('ETH', to_checksum_address(account)) for account in accounts]
    cursor.executemany('INSERT INTO blockchain_accounts(blockchain, account) VALUES(?, ?)', tuples)
    db.conn.commit()


def _eth_rpc_port_to_eth_rpc_endpoint(db: 'DBHandler') -> None:
    """Upgrade the eth_rpc_port setting to eth_rpc_endpoint"""
    cursor = db.conn.cursor()
    query = cursor.execute('SELECT value FROM settings where name="eth_rpc_port";')
    result = query.fetchall()
    if len(result) == 0:
        port = '8545'
    else:
        port = result[0][0]

    cursor.execute('DELETE FROM settings where name="eth_rpc_port";')
    cursor.execute(
        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?);',
        ('eth_rpc_endpoint', f'http://localhost:{port}'),
    )
    db.conn.commit()


def _delete_used_query_range_entries(db: 'DBHandler') -> None:
    """Delete all entries from the used_query_ranges table"""
    cursor = db.conn.cursor()
    cursor.execute('DELETE FROM used_query_ranges;')
    db.conn.commit()


UPGRADES_LIST = [
    UpgradeRecord(from_version=1, function=_checksum_eth_accounts_v1_to_v2),
    UpgradeRecord(
        from_version=2,
        function=rename_assets_in_db,
        kwargs={'rename_pairs': [('BCHSV', 'BSV')]},
    ),
    UpgradeRecord(
        from_version=3,
        function=_eth_rpc_port_to_eth_rpc_endpoint,
    ),
    UpgradeRecord(
        from_version=4,
        function=rename_assets_in_db,
        kwargs={'rename_pairs': [('BCC', 'BCH')]},
    ),
    UpgradeRecord(
        from_version=5,
        function=upgrade_v5_to_v6,
    ),
    UpgradeRecord(
        from_version=6,
        function=upgrade_v6_to_v7,
    ),
    UpgradeRecord(
        from_version=7,
        function=upgrade_v7_to_v8,
    ),
    UpgradeRecord(
        from_version=8,
        function=upgrade_v8_to_v9,
    ),
    UpgradeRecord(
        from_version=9,
        function=_delete_used_query_range_entries,
    ),
    UpgradeRecord(
        from_version=10,
        function=upgrade_v10_to_v11,
    ),
    UpgradeRecord(
        from_version=11,
        function=upgrade_v11_to_v12,
    ),
    UpgradeRecord(
        from_version=12,
        function=upgrade_v12_to_v13,
    ),
    UpgradeRecord(
        from_version=13,
        function=upgrade_v13_to_v14,
    ),
    UpgradeRecord(
        from_version=14,
        function=upgrade_v14_to_v15,
    ),
    UpgradeRecord(
        from_version=15,
        function=upgrade_v15_to_v16,
    ),
    UpgradeRecord(
        from_version=16,
        function=upgrade_v16_to_v17,
    ),
    UpgradeRecord(
        from_version=17,
        function=upgrade_v17_to_v18,
    ),
    UpgradeRecord(
        from_version=18,
        function=upgrade_v18_to_v19,
    ),
    UpgradeRecord(
        from_version=19,
        function=upgrade_v19_to_v20,
    ),
    UpgradeRecord(
        from_version=20,
        function=upgrade_v20_to_v21,
    ),
    UpgradeRecord(
        from_version=21,
        function=upgrade_v21_to_v22,
    ),
    UpgradeRecord(
        from_version=22,
        function=upgrade_v22_to_v23,
    ),
    UpgradeRecord(
        from_version=23,
        function=upgrade_v23_to_v24,
    ),
    UpgradeRecord(
        from_version=24,
        function=upgrade_v24_to_v25,
    ),
    UpgradeRecord(
        from_version=25,
        function=upgrade_v25_to_v26,
    ),
    UpgradeRecord(
        from_version=26,
        function=upgrade_v26_to_v27,
    ),
    UpgradeRecord(
        from_version=27,
        function=upgrade_v27_to_v28,
    ),
    UpgradeRecord(
        from_version=28,
        function=upgrade_v28_to_v29,
    ),
    UpgradeRecord(
        from_version=29,
        function=upgrade_v29_to_v30,
    ),
    UpgradeRecord(
        from_version=30,
        function=upgrade_v30_to_v31,
    ),
    UpgradeRecord(
        from_version=31,
        function=upgrade_v31_to_v32,
    ),
    UpgradeRecord(
        from_version=32,
        function=upgrade_v32_to_v33,
    ),
]


class DBUpgradeManager():
    """Separate class to manage DB upgrades/migrations"""

    def __init__(self, db: 'DBHandler'):
        self.db = db

    def run_upgrades(self) -> bool:
        """Run all required database upgrades

        Returns true for fresh database and false otherwise.

        May raise:
        - DBUpgradeError if the user uses a newer version than the one we
        upgrade to or if there is a problem during upgrade.
        """
        with self.db.conn.write_ctx() as cursor:
            try:
                our_version = self.db.get_setting(cursor, 'version')
            except sqlcipher.OperationalError:  # pylint: disable=no-member
                return True  # fresh database. Nothing to upgrade.

            if our_version > ROTKEHLCHEN_DB_VERSION:
                raise DBUpgradeError(
                    'Your database version is newer than the version expected by the '
                    'executable. Did you perhaps try to revert to an older rotki version? '
                    'Please only use the latest version of the software.',
                )

            cursor.execute(
                'SELECT value FROM settings WHERE name=?;', ('version',),
            )
            if cursor.fetchone() is None:
                # temporary due to https://github.com/rotki/rotki/issues/3744.
                # Figure out if an upgrade needs to actually run.
                cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name="eth2_validators"')  # noqa: E501
                if cursor.fetchone()[0] == 0:  # count always returns
                    # it's wrong and at least v30
                    self.db.set_setting(write_cursor=cursor, name='version', value=30)

        for upgrade in UPGRADES_LIST:
            self._perform_single_upgrade(upgrade)

        # Finally make sure to always have latest version in the DB
        with self.db.user_write() as cursor:
            self.db.set_setting(cursor, name='version', value=ROTKEHLCHEN_DB_VERSION)
        return False

    def _perform_single_upgrade(self, upgrade: UpgradeRecord) -> None:
        """
        This is the wrapper function that performs each DB upgrade

        The logic is:
            1. Check version, if not at from_version get out.
            2. If at from_version make a DB backup before performing the upgrade
            3. Perform the upgrade action
            4. If something went wrong during upgrade restore backup and quit
            5. If all went well set version and delete the backup

        """
        with self.db.conn.read_ctx() as cursor:
            current_version = self.db.get_setting(cursor, 'version')
        if current_version != upgrade.from_version:
            return
        to_version = upgrade.from_version + 1

        # First make a backup of the DB
        with TemporaryDirectory() as tmpdirname:
            tmp_db_filename = f'{ts_now()}_rotkehlchen_db_v{upgrade.from_version}.backup'
            tmp_db_path = os.path.join(tmpdirname, tmp_db_filename)
            shutil.copyfile(
                os.path.join(self.db.user_data_dir, 'rotkehlchen.db'),
                tmp_db_path,
            )

            try:
                kwargs = upgrade.kwargs if upgrade.kwargs is not None else {}
                upgrade.function(db=self.db, **kwargs)
            except BaseException as e:  # lgtm[py/catch-base-exception]
                # Problem .. restore DB backup and bail out
                error_message = (
                    f'Failed at database upgrade from version {upgrade.from_version} to '
                    f'{to_version}: {str(e)}'
                )
                log.error(error_message)
                shutil.copyfile(
                    tmp_db_path,
                    os.path.join(self.db.user_data_dir, 'rotkehlchen.db'),
                )
                raise DBUpgradeError(error_message) from e

            # for some upgrades even for success keep the backup of the previous db
            if upgrade.from_version >= 24:
                shutil.copyfile(
                    tmp_db_path,
                    os.path.join(self.db.user_data_dir, tmp_db_filename),
                )

        # Upgrade success all is good
        with self.db.user_write() as cursor:
            self.db.set_setting(write_cursor=cursor, name='version', value=to_version)
