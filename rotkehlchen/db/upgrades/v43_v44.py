import json
import logging
import re
from typing import TYPE_CHECKING, Final

from eth_utils import to_checksum_address

from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.upgrades.utils import fix_address_book_duplications
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

NFT_DIRECTIVE: Final = '_nft_'


@enter_exit_debug_log(name='UserDB v43->v44 upgrade')
def upgrade_v43_to_v44(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v43 to v44. This was in v1.35 release.

    - last_price and last_price asset are no longer optional in the nfts table
    - update tags of accounts
    - drop column removed from the transaction logs
    - make the blockchain column not nullable since we use `NONE` as string
    - add uniswap v2 and v3 as historical oracles
    - add exited_timestamp to the eth2_validators table
    - add new tables: cowswap orders and gnosis pay data
    - reset decoded evm events except for zksync lite and custom ones
    - Add 4 new locations to the DB (moved from migration 17 which was in 1.34.3)
    """
    @progress_step(description='Adding new locations to the DB.')
    def _add_new_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Bitcoin */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('q', 49);
        /* Bitcoin Cash */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('r', 50);
        /* Polkadot */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('s', 51);
        /* Kusama */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('t', 52);
        """)

    @progress_step(description='Updating NFT table schema.')
    def _update_nft_table(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS nfts_new (
            identifier TEXT NOT NULL PRIMARY KEY,
            name TEXT,
            last_price TEXT NOT NULL,
            last_price_asset TEXT NOT NULL,
            manual_price INTEGER NOT NULL CHECK (manual_price IN (0, 1)),
            owner_address TEXT,
            blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
            is_lp INTEGER NOT NULL CHECK (is_lp IN (0, 1)),
            image_url TEXT,
            collection_name TEXT,
            usd_price REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(blockchain, owner_address) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE,
            FOREIGN KEY (identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY (last_price_asset) REFERENCES assets(identifier) ON UPDATE CASCADE
        );""")  # noqa: E501
        write_cursor.execute(
            'SELECT identifier, name, last_price, last_price_asset, manual_price, owner_address, '
            'is_lp, image_url, collection_name, usd_price FROM nfts',
        )
        final_rows = []
        assets_updates = []
        for row in write_cursor:
            final_row = list(row)
            try:  # update the identifier to ensure that the addresses are checksummed
                nft_address = final_row[0][len(NFT_DIRECTIVE):].split('_')[0]
                new_id = final_row[0].replace(nft_address, to_checksum_address(nft_address))
            except (ValueError, KeyError, TypeError):
                log.error(f'Failed to process nft address while upgrading row {row}')
                continue

            assets_updates.append((new_id, final_row[0]))
            final_row[0] = new_id

            if row[2] is None:
                final_row[2] = 0  # set last_price to a default of 0
            if row[3] is None:
                final_row[3] = 'ETH'  # set default asset to ethereum if missing for last_price_asset  # noqa: E501

            final_rows.append(final_row)

        write_cursor.executemany(
            'UPDATE assets SET identifier=? WHERE identifier=?',
            assets_updates,
        )
        write_cursor.executemany(
            'INSERT OR IGNORE INTO nfts_new(identifier, name, last_price, last_price_asset, '
            'manual_price, owner_address, is_lp, image_url, collection_name, usd_price) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            final_rows,
        )
        write_cursor.execute('DROP TABLE nfts')
        write_cursor.execute('ALTER TABLE nfts_new RENAME TO nfts')

    @progress_step(description='Removing log column "removed".')
    def _remove_log_removed_column(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'ALTER TABLE evmtx_receipt_logs DROP COLUMN removed;',
        )

    @progress_step(description='Upgrading account tags.')
    def _upgrade_account_tags(write_cursor: 'DBCursor') -> None:
        """Upgrade the object_reference references in tag_mappings to not
        depend on the supported blockchain since the format has changed in 1.35
        """
        object_references: list[tuple[str, str]] = write_cursor.execute(
            'SELECT object_reference, tag_name FROM tag_mappings',
        ).fetchall()
        if len(object_references) == 0:
            return

        remove_keys, insert_entries = [], set()
        supported_blockchains = re.compile(r'^(ETH|ETH2|BTC|BCH|KSM|AVAX|DOT|OPTIMISM|POLYGON_POS|ARBITRUM_ONE|BASE|GNOSIS|SCROLL|ZKSYNC_LITE)')  # noqa: E501  # supported blockchains at v1.35
        for (object_reference, tag_name) in object_references:
            new_object_reference, count = supported_blockchains.subn('', object_reference)
            if count != 0:
                remove_keys.append((object_reference,))
                insert_entries.add((new_object_reference, tag_name))

        write_cursor.executemany('DELETE FROM tag_mappings WHERE object_reference=?', remove_keys)
        write_cursor.executemany(
            'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) VALUES (?, ?)',
            list(insert_entries),
        )

    @progress_step(description='Updating addressbook schema.')
    def _addressbook_schema_update(write_cursor: 'DBCursor') -> None:
        """Make the blockchain column to a non nullable column for address_book"""
        fix_address_book_duplications(write_cursor=write_cursor)

    @progress_step(description='Adding Uniswap to historical oracles.')
    def _add_uniswap_to_historical_oracles(cursor: 'DBCursor') -> None:
        """Add uniswapv2 and uniswapv3 to the list of historical price oracles."""
        cursor.execute('SELECT value FROM settings WHERE name=?', ('historical_price_oracles',))
        if (price_oracles := cursor.fetchone()) is None:
            return

        try:
            oracles = json.loads(price_oracles[0])
        except json.JSONDecodeError as e:
            log.error(f'Failed to parse {price_oracles[0]} as JSON due to {e}')
            return

        oracles.extend([
            HistoricalPriceOracle.UNISWAPV3.serialize(),
            HistoricalPriceOracle.UNISWAPV2.serialize(),
        ])

        cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            ('historical_price_oracles', json.dumps(oracles)),
        )

    @progress_step(description='Adding exited_timestamp column to the eth2_validators table.')
    def _add_exited_timestamp(cursor: 'DBCursor') -> None:
        """Add exited_timestamp column to the eth2_validators table"""
        cursor.execute('ALTER TABLE eth2_validators ADD COLUMN exited_timestamp INTEGER')

    @progress_step(description='Adding new cowswap_orders and gnosispay_data tables.')
    def _add_new_tables(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS cowswap_orders (
            identifier TEXT NOT NULL PRIMARY KEY,
            order_type TEXT NOT NULL,
            raw_fee_amount TEXT NOT NULL
        );""")
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS gnosispay_data (
            identifier INTEGER PRIMARY KEY NOT NULL,
            tx_hash BLOB NOT NULL UNIQUE,
            timestamp INTEGER NOT NULL,
            merchant_name TEXT NOT NULL,
            merchant_city TEXT,
            country TEXT NOT NULL,
            mcc INTEGER NOT NULL,
            transaction_symbol TEXT NOT NULL,
            transaction_amount TEXT NOT NULL,
            billing_symbol TEXT,
            billing_amount TEXT,
            reversal_symbol TEXT,
            reversal_amount TEXT,
            reversal_tx_hash BLOB UNIQUE
        );""")

    @progress_step(description='Removing zksynclite used query ranges.')
    def _remove_zksynclite_used_query_ranges(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("DELETE FROM used_query_ranges WHERE name LIKE 'zksynclitetxs_%'")

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm events except for the customized ones and those in zksync lite."""
        if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0:
            customized_events = write_cursor.execute(
                'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
                (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
            ).fetchone()[0]
            querystr = (
                "DELETE FROM history_events WHERE identifier IN ("
                "SELECT H.identifier from history_events H INNER JOIN evm_events_info E "
                "ON H.identifier=E.identifier AND E.tx_hash IN "
                "(SELECT tx_hash FROM evm_transactions) AND H.location != 'o')"  # location 'o' is zksync lite  # noqa: E501
            )
            bindings: tuple = ()
            if customized_events != 0:
                querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
                bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

            write_cursor.execute(querystr, bindings)
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
                (0,),  # decoded tx state
            )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
