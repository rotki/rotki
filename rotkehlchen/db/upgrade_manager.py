import logging
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any, Callable, Dict, NamedTuple, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.crypto import sha3
from rotkehlchen.db.asset_rename import rename_assets_in_db
from rotkehlchen.db.utils import ROTKEHLCHEN_DB_VERSION
from rotkehlchen.errors import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class UpgradeRecord(NamedTuple):
    from_version: int
    function: Callable
    kwargs: Optional[Dict[str, Any]] = None


def _checksum_eth_accounts(db: 'DBHandler') -> None:
    """Make sure all eth accounts are checksummed when saved in the DB"""
    accounts = db.get_blockchain_accounts()
    cursor = db.conn.cursor()
    cursor.execute(
        'DELETE FROM blockchain_accounts WHERE blockchain=?;', ('ETH',),
    )
    db.conn.commit()
    for account in accounts.eth:
        db.add_blockchain_account(
            blockchain=SupportedBlockchain.ETHEREUM,
            account=to_checksum_address(account),
        )


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


def _remove_cache_files(user_data_dir: str) -> None:
    """At 5->6 version upgrade all cache files should be removed

    That's since we moved all trades in the DB and as such it no longer makes
    any sense to have the cache files.
    """
    for p in Path(user_data_dir).glob('*_trades.json'):
        try:
            p.unlink()
        except OSError:
            pass

    for p in Path(user_data_dir).glob('*_history.json'):
        try:
            p.unlink()
        except OSError:
            pass

    for p in Path(user_data_dir).glob('*_deposits_withdrawals.json'):
        try:
            p.unlink()
        except OSError:
            pass

    try:
        os.remove(os.path.join(user_data_dir, 'ethereum_tx_log.json'))
    except OSError:
        pass


def _upgrade_v5_to_v6(db: 'DBHandler') -> None:
    """Upgrades the DB from v5 to v6

    It removes all cache files and also upgrades all trade tables to:
    - use the new id scheme
    - use an enum table for trade type
    - use an enum table for location
    """
    _remove_cache_files(db.user_data_dir)
    cursor = db.conn.cursor()
    # This is the data trades table had at v5
    query = cursor.execute(
        """SELECT time, location, pair, type, amount, rate, fee, fee_currency,
        link, notes FROM trades;""",
    )
    trade_tuples = []
    for result in query:
        # This is the logic of trade addition in v6 of the DB
        time = result[0]
        pair = result[2]
        old_trade_type = result[3]
        # hand deserialize trade type from DB enum since this code is going to stay
        # here even if deserialize_trade_type_from_db() changes
        if old_trade_type == 'buy':
            trade_type = 'A'
        elif old_trade_type == 'sell':
            trade_type = 'B'
        else:
            raise DBUpgradeError(
                f'Unexpected trade_type "{trade_type}" found while upgrading '
                f'from DB version 5 to 6',
            )

        trade_id = sha3(('external' + str(time) + str(old_trade_type) + pair).encode()).hex()
        trade_tuples.append((
            trade_id,
            time,
            'A',  # Symbolizes external in the location enum
            pair,
            trade_type,
            result[4],
            result[5],
            result[6],
            result[7],
            result[8],
            result[9],
        ))

    # We got all the external trades data. Now delete the old table and create
    # the new one
    cursor.execute('DROP TABLE trades;')
    db.conn.commit()
    # This is the scheme of the trades table at v6 from db/utils.py
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    time INTEGER,
    location VARCHAR[24],
    pair VARCHAR[24],
    type CHAR(1) NOT NULL DEFAULT ('B') REFERENCES trade_type(type),
    amount TEXT,
    rate TEXT,
    fee TEXT,
    fee_currency VARCHAR[10],
    link TEXT,
    notes TEXT
    );""")
    db.conn.commit()

    # and finally move the data to the new table
    cursor.executemany(
        'INSERT INTO trades('
        '  id, '
        '  time,'
        '  location,'
        '  pair,'
        '  type,'
        '  amount,'
        '  rate,'
        '  fee,'
        '  fee_currency,'
        '  link,'
        '  notes)'
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        trade_tuples,
    )
    db.conn.commit()


UPGRADES_LIST = [
    UpgradeRecord(from_version=1, function=_checksum_eth_accounts),
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
        function=_upgrade_v5_to_v6,
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
