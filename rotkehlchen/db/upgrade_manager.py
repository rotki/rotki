from typing import List, Tuple

from eth_utils.address import to_checksum_address

from rotkehlchen.typing import SupportedBlockchain


class DBUpgradeManager():
    """Separate class to manage DB upgrades/migrations"""

    def __init__(self, db):
        self.db = db

    def run_upgrades(self) -> None:
        self._upgrade_1_to_2()
        self._upgrade_2_to_3()
        self._upgrade_3_to_4()
        self._upgrade_4_to_5()

    def rename_assets_in_db(self, rename_pairs: List[Tuple[str, str]]) -> None:
        """
        Renames assets in all the relevant tables in the Database.

        Takes a list of tuples in the form:
        [(from_name_1, to_name_1), (from_name_2, to_name_2), ...]

        Good for DB version 1 until Now.
        """
        cursor = self.db.conn.cursor()
        # [(to_name_1, from_name_1), (to_name_2, from_name_2), ...]
        changed_symbols = [(e[1], e[0]) for e in rename_pairs]

        cursor.executemany(
            'UPDATE multisettings SET value=? WHERE value=? and name="ignored_asset";',
            changed_symbols,
        )

        cursor.executemany(
            'UPDATE timed_balances SET currency=? WHERE currency=?',
            changed_symbols,
        )

        replaced_symbols = [e[0] for e in rename_pairs]
        replaced_symbols_q = ['pair LIKE "%' + s + '%"' for s in replaced_symbols]
        query_str = (
            f'SELECT id, pair, fee_currency FROM trades WHERE fee_currency IN '
            f'({",".join("?"*len(replaced_symbols))}) OR ('
            f'{" OR ".join(replaced_symbols_q)})'
        )
        cursor.execute(query_str, replaced_symbols)
        updated_trades = []
        for q in cursor:
            new_pair = q[1]
            for rename_pair in rename_pairs:
                from_asset = rename_pair[0]
                to_asset = rename_pair[1]

                if from_asset not in q[1] and from_asset != q[2]:
                    # It's not this rename pair
                    continue

                if from_asset in q[1]:
                    new_pair = q[1].replace(from_asset, to_asset)

                new_fee_currency = q[2]
                if from_asset == q[2]:
                    new_fee_currency = to_asset

                updated_trades.append((new_pair, new_fee_currency, q[0]))

        cursor.executemany(
            'UPDATE trades SET pair=?, fee_currency=? WHERE id=?',
            updated_trades,
        )

    def _upgrade_1_to_2(self) -> None:
        current_version = self.db.get_version()
        if current_version != 1:
            return

        # apply the 1 -> 2 updates
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

    def _upgrade_2_to_3(self) -> None:
        """Update BCHSV to BSV"""
        current_version = self.db.get_version()
        if current_version != 2:
            return

        self.rename_assets_in_db(rename_pairs=[('BCHSV', 'BSV')])

    def _upgrade_3_to_4(self) -> None:
        """Upgrade the eth_rpc_port setting to eth_rpc_endpoint"""
        current_version = self.db.get_version()
        if current_version != 3:
            return

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

    def _upgrade_4_to_5(self) -> None:
        """Update BCC to BCH"""
        current_version = self.db.get_version()
        if current_version != 4:
            return

        self.rename_assets_in_db(rename_pairs=[('BCC', 'BCH')])
