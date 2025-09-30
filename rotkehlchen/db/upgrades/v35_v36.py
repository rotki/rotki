import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.eth2.constants import MIN_EFFECTIVE_BALANCE
from rotkehlchen.constants import ONE
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.settings import DEFAULT_ACTIVE_MODULES
from rotkehlchen.db.utils import table_exists, update_table_schema
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import ChainID
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v35->v36 upgrade')
def upgrade_v35_to_v36(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v35 to v36. This was in v1.27.0 release.

        - Remove adex data
        - upgrade ignored actions ids for transactions
        - upgrade accounts details table to add chain id
        - rename all eth tables to evm and add chain id
        - upgrade history_events_mappings to have key/value schema
        - Upgrade nfts table to add image url, collection name and whether
          it's a uniswap LP NFT
        - rename web3_nodes to rpc_nodes
    """
    @progress_step(description='Removing adex.')
    def _remove_adex(write_cursor: 'DBCursor') -> None:
        """Remove all adex related tables, events, data in other tables"""
        write_cursor.execute('DROP TABLE IF EXISTS adex_events')
        if table_exists(write_cursor, 'used_query_ranges'):
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
                ('adex\\_events%', '\\'),
            )

        write_cursor.execute("SELECT value FROM settings where name='active_modules'")
        active_modules_result = write_cursor.fetchone()
        if active_modules_result is not None:
            active_modules_str = active_modules_result[0]
            try:
                new_value = json.loads(active_modules_str)
                if 'adex' in new_value:
                    new_value.remove('adex')

            except json.decoder.JSONDecodeError:
                log.error(
                    f'During v35->v36 DB upgrade a non-json active_modules entry was found: '
                    f'{active_modules_str}. Reverting to default.',
                )
                new_value = DEFAULT_ACTIVE_MODULES

            write_cursor.execute(
                "UPDATE OR IGNORE settings SET value=? WHERE name='active_modules'",
                (json.dumps(new_value),),
            )

    @progress_step(description='Upgrading ignored actionids.')
    def _upgrade_ignored_actionids(write_cursor: 'DBCursor') -> None:
        """ignored_action_ids of ActionType ETHEREUM_TRANSACTION need chainid prepended"""
        if table_exists(write_cursor, 'used_query_ranges'):
            write_cursor.execute("UPDATE ignored_actions SET identifier = '1' || identifier WHERE type='C'")  # noqa: E501

    @progress_step(description='Upgrading account details.')
    def _upgrade_account_details(write_cursor: 'DBCursor') -> None:
        """Upgrade the account_details table to evm_accounts_details"""
        new_data = []
        last_queried_timestamp_map: dict[str, int] = {}
        if table_exists(write_cursor, 'accounts_details'):
            write_cursor = write_cursor.execute('SELECT * FROM accounts_details')
            for entry in write_cursor:
                if entry[1] != 'eth':
                    log.error(
                        f'During v35->v36 DB upgrade a non-eth accounts_details entry '
                        f'{entry[1]} was found. Skipping it.',
                    )
                    continue

                if entry[2] == 'last_queried_timestamp':
                    # Fix duplicated last_queried timestamp as seen here:
                    # https://github.com/rotki/rotki/pull/5257
                    timestamp = int(entry[3])
                    last_seen_timestamp = last_queried_timestamp_map.get(entry[0], 0)
                    if timestamp > last_seen_timestamp:
                        last_queried_timestamp_map[entry[0]] = timestamp
                    continue

                new_data.append((entry[0], 1, entry[2], entry[3]))

        for address, last_queried_timestamp in last_queried_timestamp_map.items():
            new_data.append((address, 1, 'last_queried_timestamp', str(last_queried_timestamp)))

        write_cursor.execute('DROP TABLE IF EXISTS accounts_details;')
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_accounts_details (
            account VARCHAR[42] NOT NULL,
            chain_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (account, chain_id, key, value)
        );
        """)
        write_cursor.executemany(
            """INSERT OR IGNORE INTO evm_accounts_details(
            account, chain_id, key, value
            ) VALUES (?, ?, ?, ?)""",
            new_data,
        )

    @progress_step(description='Renaming eth to evm.')
    def _rename_eth_to_evm_add_chainid(write_cursor: 'DBCursor') -> None:
        """Rename all eth to evm tables, add chain id and adjust tx mappings"""
        # Get all data in memory and upgrade it
        transactions = []
        if table_exists(write_cursor, 'ethereum_transactions'):
            write_cursor.execute('SELECT * from ethereum_transactions')
            transactions.extend([(
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ) for entry in write_cursor])
        internal_transactions = []
        if table_exists(write_cursor, 'ethereum_internal_transactions'):
            write_cursor.execute('SELECT * from ethereum_internal_transactions')
            internal_transactions.extend([(
                entry[0],    # parent_ tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ) for entry in write_cursor])
        tx_receipts = []
        if table_exists(write_cursor, 'ethtx_receipts'):
            write_cursor.execute('SELECT * from ethtx_receipts')
            tx_receipts.extend([(
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ) for entry in write_cursor])
        tx_receipt_logs = []
        if table_exists(write_cursor, 'ethtx_receipt_logs'):
            write_cursor.execute('SELECT * from ethtx_receipt_logs')
            tx_receipt_logs.extend([(
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ) for entry in write_cursor])
        tx_receipt_log_topics = []
        if table_exists(write_cursor, 'ethtx_receipt_log_topics'):
            write_cursor.execute('SELECT * from ethtx_receipt_log_topics')
            tx_receipt_log_topics.extend([(
                entry[0],    # tx_hash
                1,           # chain_id
                *entry[1:],  # all the rest are the same
            ) for entry in write_cursor])
        tx_address_mappings = []
        if table_exists(write_cursor, 'ethtx_address_mappings'):
            write_cursor.execute('SELECT * from ethtx_address_mappings')
            tx_address_mappings.extend([(
                entry[0],    # address
                entry[1],    # tx_hash
                1,           # chain_id
                *entry[2:],  # all the rest are the same
            ) for entry in write_cursor])
        tx_mappings = []
        if table_exists(write_cursor, 'evm_tx_mappings'):
            write_cursor.execute('SELECT * from evm_tx_mappings')
            for entry in write_cursor:
                if entry[2] == 'decoded':
                    value = 0
                elif entry[2] == 'customized':
                    value = 1
                else:
                    log.error(
                        f'During v35->v36 DB upgrade unknown evm_tx_mappings '
                        f'value {entry[1]} was found. Skipping it.',
                    )
                    continue

                if entry[1] != 'ETH':
                    log.error(
                        f'During v35->v36 DB upgrade unknown evm_tx_mappings '
                        f'blockchain entry "{entry[1]}" was found. Skipping it.',
                    )
                    continue

                tx_mappings.append((entry[0], 1, value))

        # Kill tables
        write_cursor.execute('DROP TABLE IF EXISTS ethereum_transactions')
        write_cursor.execute('DROP TABLE IF EXISTS ethereum_internal_transactions')
        write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipts')
        write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipt_logs')
        write_cursor.execute('DROP TABLE IF EXISTS ethtx_receipt_log_topics')
        write_cursor.execute('DROP TABLE IF EXISTS ethtx_address_mappings')
        write_cursor.execute('DROP TABLE IF EXISTS evm_tx_mappings')

        # Create new tables and populate them
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evm_transactions (
            tx_hash BLOB NOT NULL,
            chain_id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT,
            value TEXT NOT NULL,
            gas TEXT NOT NULL,
            gas_price TEXT NOT NULL,
            gas_used TEXT NOT NULL,
            input_data BLOB NOT NULL,
            nonce INTEGER NOT NULL,
            PRIMARY KEY(tx_hash, chain_id)
            );""",
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evm_transactions(
                tx_hash,
                chain_id,
                timestamp,
                block_number,
                from_address,
                to_address,
                value,
                gas,
                gas_price,
                gas_used,
                input_data,
                nonce
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ? ,? ,? ,? ,?)""",
            transactions,
        )
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evm_internal_transactions (
                parent_tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                trace_id INTEGER NOT NULL,
                timestamp INTEGER NOT NULL,
                block_number INTEGER NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT,
                value TEXT NOT NULL,
                FOREIGN KEY(parent_tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
                PRIMARY KEY(parent_tx_hash, chain_id, trace_id, from_address, to_address, value)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evm_internal_transactions(
                parent_tx_hash,
                chain_id,
                trace_id,
                timestamp,
                block_number,
                from_address,
                to_address,
                value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            internal_transactions,
        )
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evmtx_receipts (
                tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                contract_address TEXT, /* can be null */
                status INTEGER NOT NULL CHECK (status IN (0, 1)),
                type INTEGER NOT NULL,
                FOREIGN KEY(tx_hash, chain_id) REFERENCES evm_transactions(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
                PRIMARY KEY(tx_hash, chain_id)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evmtx_receipts(
                tx_hash,
                chain_id,
                contract_address,
                status,
                type
            ) VALUES (?, ?, ?, ?, ?)""",
            tx_receipts,
        )
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evmtx_receipt_logs (
                tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                log_index INTEGER NOT NULL,
                data BLOB NOT NULL,
                address TEXT NOT NULL,
                removed INTEGER NOT NULL CHECK (removed IN (0, 1)),
                FOREIGN KEY(tx_hash, chain_id) REFERENCES evmtx_receipts(tx_hash, chain_id) ON DELETE CASCADE ON UPDATE CASCADE,
                PRIMARY KEY(tx_hash, chain_id, log_index)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evmtx_receipt_logs(
                tx_hash,
                chain_id,
                log_index,
                data,
                address,
                removed
            ) VALUES (?, ?, ?, ?, ?, ?)""",
            tx_receipt_logs,
        )
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evmtx_receipt_log_topics (
                tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                log_index INTEGER NOT NULL,
                topic BLOB NOT NULL,
                topic_index INTEGER NOT NULL,
                FOREIGN KEY(tx_hash, chain_id, log_index) REFERENCES evmtx_receipt_logs(tx_hash, chain_id, log_index) ON DELETE CASCADE ON UPDATE CASCADE,
                PRIMARY KEY(tx_hash, chain_id, log_index, topic_index)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evmtx_receipt_log_topics(
                tx_hash,
                chain_id,
                log_index,
                topic,
                topic_index
            ) VALUES (?, ?, ?, ?, ?)""",
            tx_receipt_log_topics,
        )
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evmtx_address_mappings (
                address TEXT NOT NULL,
                tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                blockchain TEXT NOT NULL,
                FOREIGN KEY(blockchain, address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
                FOREIGN KEY(tx_hash, chain_id) references evm_transactions(tx_hash, chain_id) ON UPDATE CASCADE ON DELETE CASCADE,
                PRIMARY KEY (address, tx_hash, chain_id)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evmtx_address_mappings(
                address,
                tx_hash,
                chain_id,
                blockchain
            ) VALUES (?, ?, ?, ?)""",
            tx_address_mappings,
        )
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evm_tx_mappings (
                tx_hash BLOB NOT NULL,
                chain_id INTEGER NOT NULL,
                value INTEGER NOT NULL,
                FOREIGN KEY(tx_hash, chain_id) references evm_transactions(tx_hash, chain_id) ON UPDATE CASCADE ON DELETE CASCADE,
                PRIMARY KEY (tx_hash, chain_id, value)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO evm_tx_mappings(
                tx_hash,
                chain_id,
                value
            ) VALUES (?, ?, ?)""",
            tx_mappings,
        )

    @progress_step(description='Upgrading events mappings.')
    def _upgrade_events_mappings(write_cursor: 'DBCursor') -> None:
        """Upgrade history_events_mappings"""
        new_data = []
        if table_exists(write_cursor, 'history_events_mappings'):
            write_cursor = write_cursor.execute('SELECT * FROM history_events_mappings')
            for entry in write_cursor:
                if entry[1] == 'decoded':
                    value = 0
                elif entry[1] == 'customized':
                    value = 1
                else:
                    log.error(
                        f'During v35->v36 DB upgrade unknown history_events_mappings '
                        f'value {entry[1]} was found. Skipping it.',
                    )
                    continue
                new_data.append((entry[0], 'state', value))

        write_cursor.execute('DROP TABLE IF EXISTS history_events_mappings')
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS history_events_mappings (
                parent_identifier INTEGER NOT NULL,
                name TEXT NOT NULL,
                value INTEGER NOT NULL,
                FOREIGN KEY(parent_identifier) references history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE,
                PRIMARY KEY (parent_identifier, name, value)
            );""",  # noqa: E501
        )
        write_cursor.executemany(
            """
            INSERT OR IGNORE INTO history_events_mappings(
                parent_identifier,
                name,
                value
            ) VALUES (?, ?, ?)""",
            new_data,
        )

    @progress_step(description='Updating nfts table schema.')
    def _upgrade_nfts_table(write_cursor: 'DBCursor') -> None:
        """Upgrade nfts table to add image url, collection name and whether its a uniswap LP NFT"""
        write_cursor.execute('DROP TABLE IF EXISTS nfts')
        write_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS nfts (
                identifier TEXT NOT NULL PRIMARY KEY,
                name TEXT,
                last_price TEXT,
                last_price_asset TEXT,
                manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
                owner_address TEXT,
                blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
                is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
                image_url TEXT,
                collection_name TEXT,
                FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
                FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
                FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
            );""",  # noqa: E501
        )

    @progress_step(description='Upgrading rpc node.')
    def _upgrade_rpc_nodes(write_cursor: 'DBCursor') -> None:
        """
        Change name of web3_nodes to rpc_nodes and fix the schema. Weight should be
        a float from 0 to 1 saved as string, not an integer.

        Really wonder why this was never seen before
        """
        # using "ETH" directly since at this point all blockchain column values should be ETH
        # and there may be a problem (noticed it in the premium DB pulling tests) where
        # web3_nodes did not run through v34->v35 upgrade properly so blockchain column is missing.
        # I suspect the tests I noticed it were due to the developer who created the DB error, but
        # since this is equivalent to reading the blockchain column, better safe than sorry
        nodes_tuples = write_cursor.execute(
            "SELECT name, endpoint, owned, active, weight, 'ETH' from web3_nodes",
        ).fetchall()
        write_cursor.execute('DROP TABLE IF EXISTS web3_nodes')
        write_cursor.execute(
            """CREATE TABLE IF NOT EXISTS rpc_nodes(
            identifier INTEGER NOT NULL PRIMARY KEY,
            name TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
            active INTEGER NOT NULL CHECK (active IN (0, 1)),
            weight TEXT NOT NULL,
            blockchain TEXT NOT NULL
            );""",
        )
        nodes_tuples.extend([
            ('optimism etherscan', '', False, True, '0.4', 'OPTIMISM'),
            ('optimism official', 'https://mainnet.optimism.io', False, True, '0.2', 'OPTIMISM'),
            ('optimism blastapi', 'https://optimism-mainnet.public.blastapi.io', False, True, '0.2', 'OPTIMISM'),  # noqa: E501
            ('optimism ankr', 'https://rpc.ankr.com/optimism', False, True, '0.1', 'OPTIMISM'),
            ('optimism 1rpc', 'https://1rpc.io/op', False, True, '0.1', 'OPTIMISM'),
        ])
        write_cursor.executemany(
            'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) VALUES (?, ?, ?, ?, ?, ?)',  # noqa: E501
            nodes_tuples,
        )

    @progress_step(description='Upgrading tags.')
    def _upgrade_tags(write_cursor: 'DBCursor') -> None:
        """All tags tied to addresses should now be tied to chain + address"""
        write_cursor.execute(
            'SELECT A.blockchain, A.account, B.tag_name from blockchain_accounts AS A '
            'LEFT OUTER JOIN tag_mappings AS B on A.account = B.object_reference',
        )
        delete_tuples = []
        insert_tuples = []
        for entry in write_cursor:
            delete_tuples.append((entry[1],))
            insert_tuples.append((entry[0] + entry[1], entry[2]))

        write_cursor.executemany('DELETE from tag_mappings WHERE object_reference=?', delete_tuples)  # noqa: E501
        write_cursor.executemany(
            'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) VALUES(?, ?)',
            insert_tuples,
        )

    @progress_step(description='Upgrading address book table.')
    def _upgrade_address_book_table(write_cursor: 'DBCursor') -> None:
        """Upgrades the address book table by making the blockchain column optional"""
        update_table_schema(
            write_cursor=write_cursor,
            table_name='address_book',
            schema="""address TEXT NOT NULL,
            blockchain TEXT,
            name TEXT NOT NULL,
            PRIMARY KEY(address, blockchain)""",
            insert_columns='address, blockchain, name',
        )

    @progress_step(description='Adding OKX.')
    def _add_okx(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('e', 37);")

    @progress_step(description='Removing old tables.')
    def _remove_old_tables(write_cursor: 'DBCursor') -> None:
        """In 1.27.0 we added a check for old tables in the DB.

        This found that many old DBs still have an eth_tokens table which was left there
        and was not removed in some old upgrade. Time to clean up."""
        write_cursor.execute('DROP TABLE IF EXISTS eth_tokens')

    @progress_step(description='Fixing eth2 pnl genesis.')
    def _fix_eth2_pnl_genesis(write_cursor: 'DBCursor') -> None:
        """
        To avoid querying beaconchain for all the stats since genesis manually update
        the entries that have a wrong pnl in the database for eth2 daily staking details in the
        genesis date.
        """
        fixed_values = []
        write_cursor.execute(
            'SELECT validator_index, pnl FROM eth2_daily_staking_details WHERE timestamp=?',
            (1606780800,),  # day after eth2 genesis, as seen during the old scraping
        )

        for (validator_index, pnl_str) in write_cursor:
            pnl = FVal(pnl_str)
            if pnl > ONE:
                pnl -= MIN_EFFECTIVE_BALANCE
                fixed_values.append((str(pnl), validator_index, 1606780800))

        if len(fixed_values) != 0:
            write_cursor.executemany(
                'UPDATE eth2_daily_staking_details SET pnl=? WHERE validator_index=? AND timestamp=?',  # noqa: E501
                fixed_values,
            )

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """
        The code is taken from `delete_events_by_tx_hash` right before 1.27 release.
        Has to happen after `_upgrade_events_mappings` so that the schema is the needed one.
        """
        write_cursor.execute('SELECT tx_hash from evm_transactions')
        tx_hashes = [x[0] for x in write_cursor]
        write_cursor.execute(
            'SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )
        customized_event_ids = [x[0] for x in write_cursor]
        length = len(customized_event_ids)
        querystr = 'DELETE FROM history_events WHERE event_identifier=?'
        if length != 0:
            querystr += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
            bindings = [(x, *customized_event_ids) for x in tx_hashes]
        else:
            bindings = [(x,) for x in tx_hashes]
        write_cursor.executemany(querystr, bindings)
        write_cursor.executemany(
            'DELETE from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',
            [(tx_hash, ChainID.ETHEREUM.serialize_for_db(), 0) for tx_hash in tx_hashes],  # 0 -> decoded tx state # noqa: E501
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
