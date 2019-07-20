import logging
import os
import shutil
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable

from eth_utils.address import to_checksum_address

from rotkehlchen.db.asset_rename import rename_assets_in_db
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBUpgradeManager():
    """Separate class to manage DB upgrades/migrations"""

    def __init__(self, db: 'DBHandler'):
        self.db = db

    def run_upgrades(self) -> None:
        self._perform_single_upgrade(1, 2, self._checksum_eth_accounts)
        self._perform_single_upgrade(
            from_version=2,
            to_version=3,
            upgrade_action=rename_assets_in_db,
            cursor=self.db.conn.cursor(),
            rename_pairs=[('BCHSV', 'BSV')],
        )
        self._perform_single_upgrade(3, 4, self._eth_rpc_port_to_eth_rpc_endpoint)
        self._perform_single_upgrade(
            from_version=4,
            to_version=5,
            upgrade_action=rename_assets_in_db,
            cursor=self.db.conn.cursor(),
            rename_pairs=[('BCC', 'BCH')],
        )

    def _perform_single_upgrade(
            self,
            from_version: int,
            to_version: int,
            upgrade_action: Callable,
            **kwargs: Any,
    ) -> None:
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
        if current_version != from_version:
            return

        # First make a backup of the DB
        with TemporaryDirectory() as tmpdirname:
            tmp_db_filename = os.path.join(tmpdirname, f'rotkehlchen_db.backup')
            shutil.copyfile(
                os.path.join(self.db.user_data_dir, 'rotkehlchen.db'),
                tmp_db_filename,
            )

            try:
                upgrade_action(**kwargs)
            except BaseException as e:
                # Problem .. restore DB backup and bail out
                log.error(
                    f'Failed at database upgrade from version {from_version} to '
                    f'{to_version}: {str(e)}',
                )
                shutil.copyfile(
                    tmp_db_filename,
                    os.path.join(self.db.user_data_dir, 'rotkehlchen.db'),
                )
                # TODO: Test how this looks like
                raise

        # Upgrade success all is good
        self.db.set_version(to_version)

    def _checksum_eth_accounts(self) -> None:
        """Make sure all eth accounts are checksummed when saved in the DB"""
        accounts = self.db.get_blockchain_accounts()
        cursor = self.db.conn.cursor()
        cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=?;', ('ETH',),
        )
        self.db.conn.commit()
        for account in accounts.eth:
            self.db.add_blockchain_account(
                blockchain=SupportedBlockchain.ETHEREUM,
                account=to_checksum_address(account),
            )

    def _eth_rpc_port_to_eth_rpc_endpoint(self) -> None:
        """Upgrade the eth_rpc_port setting to eth_rpc_endpoint"""
        cursor = self.db.conn.cursor()
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
        self.db.conn.commit()
