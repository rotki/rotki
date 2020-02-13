import logging
import os
import shutil
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.db.asset_rename import rename_assets_in_db
from rotkehlchen.db.settings import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.db.upgrades.v5_v6 import upgrade_v5_to_v6
from rotkehlchen.db.upgrades.v6_v7 import upgrade_v6_to_v7
from rotkehlchen.db.upgrades.v7_v8 import upgrade_v7_to_v8
from rotkehlchen.db.upgrades.v8_v9 import upgrade_v8_to_v9
from rotkehlchen.db.upgrades.v10_v11 import upgrade_v10_to_v11
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter

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
    query = query.fetchall()
    if len(query) == 0:
        port = '8545'
    else:
        port = query[0][0]

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
]


class DBUpgradeManager():
    """Separate class to manage DB upgrades/migrations"""

    def __init__(self, db: 'DBHandler'):
        self.db = db

    def run_upgrades(self) -> None:
        our_version = self.db.get_version()
        if our_version > ROTKEHLCHEN_DB_VERSION:
            raise DBUpgradeError(
                'Your database version is newer than the version expected by the '
                'executable. Did you perhaps try to revert to an older rotkehlchen version?'
                'Please only use the latest version of the software.',
            )

        for upgrade in UPGRADES_LIST:
            self._perform_single_upgrade(upgrade)

        # Finally make sure to always have latest version in the DB
        cursor = self.db.conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('version', str(ROTKEHLCHEN_DB_VERSION)),
        )
        self.db.conn.commit()

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
        current_version = self.db.get_version()
        if current_version != upgrade.from_version:
            return
        to_version = upgrade.from_version + 1

        # First make a backup of the DB
        with TemporaryDirectory() as tmpdirname:
            tmp_db_filename = os.path.join(tmpdirname, f'rotkehlchen_db.backup')
            shutil.copyfile(
                os.path.join(self.db.user_data_dir, 'rotkehlchen.db'),
                tmp_db_filename,
            )

            try:
                kwargs = upgrade.kwargs if upgrade.kwargs is not None else {}
                upgrade.function(db=self.db, **kwargs)
            except BaseException as e:
                # Problem .. restore DB backup and bail out
                error_message = (
                    f'Failed at database upgrade from version {upgrade.from_version} to '
                    f'{to_version}: {str(e)}'
                )
                log.error(error_message)
                shutil.copyfile(
                    tmp_db_filename,
                    os.path.join(self.db.user_data_dir, 'rotkehlchen.db'),
                )
                raise DBUpgradeError(error_message)

        # Upgrade success all is good
        self.db.set_version(to_version)
