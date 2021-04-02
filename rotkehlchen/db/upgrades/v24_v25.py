import json
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from rotkehlchen.chain.ethereum.modules.adex.utils import ADEX_EVENTS_PREFIX
from rotkehlchen.chain.ethereum.modules.balancer.typing import BALANCER_TRADES_PREFIX
from rotkehlchen.chain.ethereum.modules.uniswap.typing import (
    UNISWAP_EVENTS_PREFIX,
    UNISWAP_TRADES_PREFIX,
)
from rotkehlchen.constants.ethereum import YEARN_VAULTS_PREFIX
from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_movement_category_from_db,
    deserialize_location_from_db,
    deserialize_trade_type_from_db,
)
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from sqlite3 import Cursor

    from rotkehlchen.db.dbhandler import DBHandler


def pair_get_asset_ids(pair: str) -> Tuple[str, str]:
    """Split a pair into asset ids.
    Not using the functions in the code as they may go away and return assets

    If a pair can't be split it raises a ValueError.
    """
    assets = pair.split('_')
    if len(assets) != 2:
        raise ValueError(f'could not split pair {pair}')

    if len(assets[0]) == 0 or len(assets[1]) == 0:
        raise ValueError(f'could not split {pair}. It is missing either base or quote asset')

    return assets[0], assets[1]


class V24V25UpgradeHelper():

    def __init__(self, msg_aggregator: MessagesAggregator) -> None:
        """For this DB upgrade we will need the old assets mapping"""
        self.msg_aggregator = msg_aggregator
        root_dir = Path(__file__).resolve().parent.parent.parent
        assets_data_dir = root_dir / 'data'
        with open(assets_data_dir / 'all_assets.json', 'r') as f:
            self.assets = json.loads(f.read())

    def __del__(self) -> None:
        del self.assets

    def get_new_asset_identifier(self, old_id: str) -> Optional[str]:
        try:
            asset = self.assets[old_id]
            if asset['type'] == 'ethereum token':
                address = asset['ethereum_address']  # should be checksummed

                return ETHEREUM_DIRECTIVE + address

        except KeyError as e:
            self.msg_aggregator.add_warning(
                f'During v24 -> v25 DB upgrade could not find key {str(e)} at asset with '
                f'id {old_id} lookup in the all_assets json mapping. '
                f'Should happen only for custom ethereum token. Assuming same id.',
            )

        return None

    def get_new_asset_identifier_if_existing(self, identifier: str) -> str:
        new_id = self.get_new_asset_identifier(identifier)
        return new_id if new_id else identifier

    def update_table(
            self,
            cursor: 'Cursor',
            select_str: str,
            update_str: str,
    ) -> None:
        query = cursor.execute(select_str)
        cursor_tuples = []
        for entry in query:
            old_id = entry[0]
            new_id = self.get_new_asset_identifier(old_id)
            if new_id is not None:
                cursor_tuples.append((new_id, old_id))
        cursor.executemany(update_str, cursor_tuples)

    def update_margin_positions(self, cursor: 'Cursor') -> None:
        """Upgrades the margin positions table to use the new asset ids if they are ethereum tokens

        And also makes sure the new primary key id matches the rules used in the app
        """
        query = cursor.execute(
            'SELECT id, location, open_time, close_time, profit_loss,'
            'pl_currency,fee,fee_currency,link,notes from margin_positions;',
        )
        m_tuples = query.fetchall()

        cursor.execute('DELETE from margin_positions;')

        new_tuples = []
        for entry in m_tuples:
            new_pl_currency = self.get_new_asset_identifier_if_existing(entry[5])
            new_fee_currency = self.get_new_asset_identifier_if_existing(entry[7])
            # formulate the new DB identifier primary key. Copy the identifier() functionality
            open_time_str = 'None' if entry[2] == 0 else str(entry[2])
            new_id_string = (
                str(deserialize_location_from_db(entry[1])) +
                open_time_str +
                str(entry[3]) +
                new_pl_currency +
                new_fee_currency +
                entry[8]
            )
            new_id = hash_id(new_id_string)
            new_tuples.append((
                new_id,
                entry[1],
                entry[2],
                entry[3],
                entry[4],
                new_pl_currency,
                entry[6],
                new_fee_currency,
                entry[8],
                entry[9],
            ))

        cursor.executemany(
            'INSERT INTO margin_positions('
            'id, location, open_time, close_time, profit_loss,'
            'pl_currency,fee,fee_currency,link,notes) '
            'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_tuples,
        )

    def update_asset_movements(self, cursor: 'Cursor') -> None:
        """Upgrades the asset movements table to use the new asset ids if they are ethereum tokens

        And also makes sure the new primary key id matches the rules used in the app
        """
        query = cursor.execute(
            'SELECT id, location, category, address, transaction_id, time,'
            'asset,amount,fee_asset,fee,link from asset_movements;',
        )
        m_tuples = query.fetchall()

        cursor.execute('DELETE from asset_movements;')

        new_tuples = []
        for entry in m_tuples:
            new_asset = self.get_new_asset_identifier_if_existing(entry[6])
            new_fee_asset = self.get_new_asset_identifier_if_existing(entry[8])
            # formulate the new DB identifier primary key. Copy the identifier() functionality
            new_id_string = (
                str(deserialize_location_from_db(entry[1])) +
                str(deserialize_asset_movement_category_from_db(entry[2])) +
                str(entry[5]) +
                new_asset +
                new_fee_asset +
                entry[10]
            )
            new_id = hash_id(new_id_string)
            new_tuples.append((
                new_id,
                entry[1],
                entry[2],
                entry[3],
                entry[4],
                entry[5],
                new_asset,
                entry[7],
                new_fee_asset,
                entry[9],
                entry[10],
            ))

        cursor.executemany(
            'INSERT INTO asset_movements('
            'id, location, category, address, transaction_id, time,'
            'asset, amount, fee_asset, fee, link) '
            'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_tuples,
        )

    def update_trades(self, cursor: 'Cursor') -> None:
        """Upgrades the trades table to use base/quote asset instead of a pair

        Also upgrades all asset ids if they are ethereum tokens

        And also makes sure the new primary key id matches the rules used in the app
        """
        # Get all old data and transform it to the new schema
        query = cursor.execute(
            'SELECT id, '
            '       time, '
            '       location, '
            '       pair, '
            '       type, '
            '       amount, '
            '       rate, '
            '       fee, '
            '       fee_currency, '
            '       link, '
            '       notes from trades; ',
        )
        new_trade_tuples = []
        for entry in query:
            try:
                base, quote = pair_get_asset_ids(entry[3])
            except ValueError as e:
                self.msg_aggregator.add_warning(
                    f'During v24 -> v25 DB upgrade {str(e)}. This should not have happened.'
                    f' Removing the trade with id {entry[0]} at timestamp {entry[1]} '
                    f'and location {str(deserialize_location_from_db(entry[2]))} that '
                    f'contained the offending pair from the DB.',
                )
                continue

            new_id = self.get_new_asset_identifier(base)
            new_base = new_id if new_id else base
            new_id = self.get_new_asset_identifier(quote)
            new_quote = new_id if new_id else quote
            new_id = self.get_new_asset_identifier(entry[8])
            new_fee_currency = new_id if new_id else entry[8]
            timestamp = entry[1]
            amount = entry[5]
            rate = entry[6]
            link = entry[9]
            # Copy the identifier() functionality. This identifier does not sound like a good idea
            new_trade_id_string = (
                str(deserialize_location_from_db(entry[2])) +
                str(timestamp) +
                str(deserialize_trade_type_from_db(entry[4])) +
                new_base +
                new_quote +
                amount +
                rate +
                link
            )
            new_trade_id = hash_id(new_trade_id_string)
            new_trade_tuples.append((
                new_trade_id,
                entry[1],   # time
                entry[2],   # location
                new_base,
                new_quote,
                entry[4],   # type
                amount,
                rate,
                entry[7],   # fee
                new_fee_currency,
                link,
                entry[10],  # notes
            ))

        # Upgrade the table
        cursor.execute('DROP TABLE IF EXISTS trades;')
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        time INTEGER,
        location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        base_asset VARCHAR[10],
        quote_asset VARCHAR[10],
        type CHAR(1) NOT NULL DEFAULT ('A') REFERENCES trade_type(type),
        amount TEXT,
        rate TEXT,
        fee TEXT,
        fee_currency VARCHAR[10],
        link TEXT,
        notes TEXT
        );
        """)
        # Insert the new data
        executestr = """
        INSERT INTO trades(
              id,
              time,
              location,
              base_asset,
              quote_asset,
              type,
              amount,
              rate,
              fee,
              fee_currency,
              link,
              notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.executemany(executestr, new_trade_tuples)


def upgrade_v24_to_v25(db: 'DBHandler') -> None:
    """Upgrades the DB from v24 to v25.

    - Deletes data from all tables that may contain assset ids or trade pairs
      that can be easily repulled
    - Renames XD asset to SCRL
    - Removes pair from trade tables and turns it to base/quote asset
    - Purges coinbase/coinbasepro exchange data due to the changes in:
        * https://github.com/rotki/rotki/pull/2660
        * https://github.com/rotki/rotki/pull/2615

    Tables containing asset identifiers. [X] -> should not be deleted and repulled
    - amm_swaps
    - uniswap_events
    - adex_events
    - aave_events
    - yearn_vaults_events
    - ethereum_accounts_details
    - timed_balances [X]
    - manually_tracked_balances [X]
    - margin_positions [X]
    - asset_movements [X]
    - ledger_actions [X]
    - trades [X]

    Tables containing trade pairs to be switched to base/quote asset.
    [X] -> should not be deleted and repulled
    - trades [X]

    -> Remember to also clear relevant used_query_ranges
    """
    helper = V24V25UpgradeHelper(db.msg_aggregator)
    cursor = db.conn.cursor()
    # Firstly let's clear tables we can easily repopulate with new data
    cursor.execute('DELETE FROM amm_swaps;')
    cursor.execute(
        f'DELETE FROM used_query_ranges WHERE name LIKE "{BALANCER_TRADES_PREFIX}%";',
    )
    cursor.execute(
        f'DELETE FROM used_query_ranges WHERE name LIKE "{UNISWAP_TRADES_PREFIX}%";',
    )
    cursor.execute('DELETE FROM uniswap_events;')
    cursor.execute(
        f'DELETE FROM used_query_ranges WHERE name LIKE "{UNISWAP_EVENTS_PREFIX}%";',
    )
    cursor.execute('DELETE FROM adex_events;')
    cursor.execute(
        f'DELETE FROM used_query_ranges WHERE name LIKE "{ADEX_EVENTS_PREFIX}%";',
    )
    cursor.execute('DELETE FROM aave_events;')
    cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "aave_events%";')
    cursor.execute('DELETE FROM yearn_vaults_events;')
    cursor.execute(f'DELETE FROM used_query_ranges WHERE name LIKE "{YEARN_VAULTS_PREFIX}%";')
    cursor.execute('DELETE FROM ethereum_accounts_details;')
    # Purge coinbase, coinbasepro exchange data
    cursor.execute('DELETE from trades where location IN ("G", "K");')
    cursor.execute('DELETE from asset_movements where location IN ("G", "K");')
    cursor.execute('DELETE from used_query_ranges where name LIKE "coinbase%";')

    # Update tables that need updating
    helper.update_table(
        cursor=cursor,
        select_str='SELECT currency from timed_balances;',
        update_str='UPDATE timed_balances SET currency=? WHERE currency=?;',
    )
    helper.update_table(
        cursor=cursor,
        select_str='SELECT asset from manually_tracked_balances;',
        update_str='UPDATE manually_tracked_balances SET asset=? WHERE asset=?;',
    )
    helper.update_table(
        cursor=cursor,
        select_str='SELECT asset from ledger_actions;',
        update_str='UPDATE ledger_actions  SET asset=? WHERE asset=?;',
    )
    helper.update_margin_positions(cursor)
    helper.update_asset_movements(cursor)
    helper.update_trades(cursor)

    del helper
    db.conn.commit()
