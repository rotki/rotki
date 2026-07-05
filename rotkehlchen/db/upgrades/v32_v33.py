from typing import TYPE_CHECKING

from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.types import deserialize_evm_tx_hash
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.misc import is_valid_ethereum_tx_hash
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


def _deserialize_event_identifier(val: str) -> bytes:
    """Takes the event identifier string as it was in the DB in v32 and encodes in bytes
    depending on the string value
    """
    if is_valid_ethereum_tx_hash(val):
        return hexstring_to_bytes(val)
    return val.encode()


def upgrade_v32_to_v33(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v32 to v33
    - Change the schema of `blockchain` column in `xpub_mappings` table to be required.
    - Add blockchain column to `xpubs` table.
    - Change tx_hash for tables to BLOB type & history events event_identifier column to BLOB type.
    """
    @progress_step(description='Refactoring xpubs and xpub mappings.')
    def _refactor_xpubs_and_xpub_mappings(cursor: 'DBCursor') -> None:
        # Keep a copy of the xpub_mappings because it will get deleted once
        # xpubs table is dropped.
        xpub_mappings = cursor.execute('SELECT * FROM xpub_mappings').fetchall()
        update_table_schema(
            write_cursor=cursor,
            table_name='xpubs',
            schema="""xpub TEXT NOT NULL,
            derivation_path TEXT NOT NULL,
            label TEXT,
            blockchain TEXT NOT NULL,
            PRIMARY KEY (xpub, derivation_path, blockchain)""",
            insert_columns="xpub, derivation_path, label, 'BTC'",
            insert_order='(xpub, derivation_path, label, blockchain)',
        )

        # Now populate the xpub_mappings table with its previous data
        # and set `blockchain` column to NOT NULL
        cursor.execute("""
        CREATE TABLE xpub_mappings_copy (
            address TEXT NOT NULL,
            xpub TEXT NOT NULL,
            derivation_path TEXT NOT NULL,
            account_index INTEGER,
            derived_index INTEGER,
            blockchain TEXT NOT NULL,
            FOREIGN KEY(blockchain, address)
            REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
            FOREIGN KEY(xpub, derivation_path, blockchain) REFERENCES xpubs(
                xpub,
                derivation_path,
                blockchain
            ) ON DELETE CASCADE
            PRIMARY KEY (address, xpub, derivation_path)
        );
        """)
        cursor.executemany("""
        INSERT INTO xpub_mappings_copy(
            address,
            xpub,
            derivation_path,
            account_index,
            derived_index,
            blockchain
        )
        VALUES(?, ?, ?, ?, ?, ?);
        """, xpub_mappings)
        cursor.execute('DROP TABLE xpub_mappings;')
        cursor.execute('ALTER TABLE xpub_mappings_copy RENAME TO xpub_mappings;')

    @progress_step(description='Creating new tables.')
    def _create_new_tables(cursor: 'DBCursor') -> None:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS address_book (
            address TEXT NOT NULL,
            blockchain TEXT NOT NULL DEFAULT 'ETH',
            name TEXT NOT NULL,
            PRIMARY KEY(address, blockchain)
        );
    """)

    @progress_step(description='Creating web3_nodes table.')
    def _create_nodes(cursor: 'DBCursor') -> None:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS web3_nodes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        name TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        owned INTEGER NOT NULL CHECK (owned IN (0, 1)),
        active INTEGER NOT NULL CHECK (active IN (0, 1)),
        weight INTEGER NOT NULL
        );
    """)

    @progress_step(description='Updating schemas to store tx hashes and event ids as bytes.')
    def _force_bytes_for_tx_hashes(cursor: 'DBCursor') -> None:
        """This DB upgrade function:
        - Updates the tx_hash column schema in aave_events, adex_events, balancer_events,
        amm_swaps, amm_events & yearn_vaults_events from TEXT to BLOB.
        - Updates the `event_identifier` column schema of history_events from TEXT to BLOB to force
        bytes event identifiers.
        """
        # aave_events
        cursor.execute("""
        CREATE TABLE aave_events_copy (
            address VARCHAR[42] NOT NULL,
            event_type VARCHAR[10] NOT NULL,
            block_number INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            tx_hash BLOB NOT NULL,
            log_index INTEGER NOT NULL,
            asset1 TEXT NOT NULL,
            asset1_amount TEXT NOT NULL,
            asset1_usd_value TEXT NOT NULL,
            asset2 TEXT,
            asset2amount_borrowrate_feeamount TEXT,
            asset2usd_value_accruedinterest_feeusdvalue TEXT,
            borrow_rate_mode VARCHAR[10],
            FOREIGN KEY(asset1) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(asset2) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (event_type, tx_hash, log_index)
        );
        """)
        aave_events = cursor.execute('SELECT * FROM aave_events')
        new_aave_events = []
        for aave_event in aave_events:
            aave_event = list(aave_event)  # noqa: PLW2901
            try:
                aave_event[4] = deserialize_evm_tx_hash(aave_event[4])
            except DeserializationError:
                continue
            new_aave_events.append(tuple(aave_event))
        cursor.executemany(
            'INSERT INTO aave_events_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_aave_events,
        )
        cursor.execute('DROP TABLE aave_events;')
        cursor.execute('ALTER TABLE aave_events_copy RENAME TO aave_events;')

        # adex_events
        cursor.execute("""
        CREATE TABLE adex_events_copy (
            tx_hash BLOB NOT NULL,
            address VARCHAR[42] NOT NULL,
            identity_address VARCHAR[42] NOT NULL,
            timestamp INTEGER NOT NULL,
            type TEXT NOT NULL,
            pool_id TEXT NOT NULL,
            amount TEXT NOT NULL,
            usd_value TEXT NOT NULL,
            bond_id TEXT,
            nonce INT,
            slashed_at INTEGER,
            unlock_at INTEGER,
            channel_id TEXT,
            token TEXT,
            log_index INTEGER,
            FOREIGN KEY(token) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, address, type, log_index)
        );
        """)
        adex_events = cursor.execute('SELECT * FROM adex_events')
        new_adex_events = []
        for adex_event in adex_events:
            adex_event = list(adex_event)  # noqa: PLW2901
            try:
                adex_event[0] = deserialize_evm_tx_hash(adex_event[0])
            except DeserializationError:
                continue
            new_adex_events.append(tuple(adex_event))
        cursor.executemany(
            'INSERT INTO adex_events_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_adex_events,
        )
        cursor.execute('DROP TABLE adex_events;')
        cursor.execute('ALTER TABLE adex_events_copy RENAME TO adex_events;')

        # balancer_events
        cursor.execute("""
        CREATE TABLE balancer_events_copy (
            tx_hash BLOB NOT NULL,
            log_index INTEGER NOT NULL,
            address VARCHAR[42] NOT NULL,
            timestamp INTEGER NOT NULL,
            type TEXT NOT NULL,
            pool_address_token TEXT NOT NULL,
            lp_amount TEXT NOT NULL,
            usd_value TEXT NOT NULL,
            amount0 TEXT NOT NULL,
            amount1 TEXT NOT NULL,
            amount2 TEXT,
            amount3 TEXT,
            amount4 TEXT,
            amount5 TEXT,
            amount6 TEXT,
            amount7 TEXT,
            FOREIGN KEY (pool_address_token) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, log_index)
        );
        """)
        balancer_events = cursor.execute('SELECT * FROM balancer_events')
        new_balance_events = []
        for balancer_event in balancer_events:
            balancer_event = list(balancer_event)  # noqa: PLW2901
            try:
                balancer_event[0] = deserialize_evm_tx_hash(balancer_event[0])
            except DeserializationError:
                continue
            new_balance_events.append(tuple(balancer_event))
        cursor.executemany(
            'INSERT INTO balancer_events_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_balance_events,
        )
        cursor.execute('DROP TABLE balancer_events;')
        cursor.execute('ALTER TABLE balancer_events_copy RENAME TO balancer_events;')

        # yearn_vault_events
        cursor.execute("""
        CREATE TABLE yearn_vaults_events_copy (
            address VARCHAR[42] NOT NULL,
            event_type VARCHAR[10] NOT NULL,
            from_asset TEXT NOT NULL,
            from_amount TEXT NOT NULL,
            from_usd_value TEXT NOT NULL,
            to_asset TEXT NOT NULL,
            to_amount TEXT NOT NULL,
            to_usd_value TEXT NOT NULL,
            pnl_amount TEXT,
            pnl_usd_value TEXT,
            block_number INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            tx_hash BLOB NOT NULL,
            log_index INTEGER NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(from_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(to_asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (event_type, tx_hash, log_index)
        );
        """)
        yearn_vaults_events = cursor.execute('SELECT * FROM yearn_vaults_events')
        new_yearn_vaults_events = []
        for yearn_vault_event in yearn_vaults_events:
            yearn_vault_event = list(yearn_vault_event)  # noqa: PLW2901
            try:
                yearn_vault_event[12] = deserialize_evm_tx_hash(yearn_vault_event[12])
            except DeserializationError:
                continue
            new_yearn_vaults_events.append(tuple(yearn_vault_event))
        cursor.executemany(
            'INSERT INTO yearn_vaults_events_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_yearn_vaults_events,
        )
        cursor.execute('DROP TABLE yearn_vaults_events;')
        cursor.execute('ALTER TABLE yearn_vaults_events_copy RENAME TO yearn_vaults_events;')

        # amm_events
        cursor.execute("""
        CREATE TABLE amm_events_copy (
            tx_hash BLOB NOT NULL,
            log_index INTEGER NOT NULL,
            address VARCHAR[42] NOT NULL,
            timestamp INTEGER NOT NULL,
            type TEXT NOT NULL,
            pool_address VARCHAR[42] NOT NULL,
            token0_identifier TEXT NOT NULL,
            token1_identifier TEXT NOT NULL,
            amount0 TEXT,
            amount1 TEXT,
            usd_price TEXT,
            lp_amount TEXT,
            FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, log_index)
        );
        """)
        amm_events = cursor.execute('SELECT * FROM amm_events')
        new_amm_events = []
        for amm_event in amm_events:
            amm_event = list(amm_event)  # noqa: PLW2901
            try:
                amm_event[0] = deserialize_evm_tx_hash(amm_event[0])
            except DeserializationError:
                continue
            new_amm_events.append(tuple(amm_event))
        cursor.executemany(
            'INSERT INTO amm_events_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_amm_events,
        )
        cursor.execute('DROP TABLE amm_events;')
        cursor.execute('ALTER TABLE amm_events_copy RENAME TO amm_events;')

        # amm_swaps
        # drop the read only table and re create after modification
        cursor.execute('DROP VIEW combined_trades_view;')
        cursor.execute("""
        CREATE TABLE amm_swaps_copy (
            tx_hash BLOB NOT NULL,
            log_index INTEGER NOT NULL,
            address VARCHAR[42] NOT NULL,
            from_address VARCHAR[42] NOT NULL,
            to_address VARCHAR[42] NOT NULL,
            timestamp INTEGER NOT NULL,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            token0_identifier TEXT NOT NULL,
            token1_identifier TEXT NOT NULL,
            amount0_in TEXT,
            amount1_in TEXT,
            amount0_out TEXT,
            amount1_out TEXT,
            FOREIGN KEY(token0_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            FOREIGN KEY(token1_identifier) REFERENCES assets(identifier) ON UPDATE CASCADE,
            PRIMARY KEY (tx_hash, log_index)
        );
        """)
        amm_swaps = cursor.execute('SELECT * FROM amm_swaps')
        new_amm_swaps = []
        for amm_swap in amm_swaps:
            amm_swap = list(amm_swap)  # noqa: PLW2901
            try:
                amm_swap[0] = deserialize_evm_tx_hash(amm_swap[0])
            except DeserializationError:
                continue
            new_amm_swaps.append(tuple(amm_swap))
        cursor.executemany(
            'INSERT INTO amm_swaps_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_amm_swaps,
        )
        cursor.execute('DROP TABLE amm_swaps;')
        cursor.execute('ALTER TABLE amm_swaps_copy RENAME TO amm_swaps;')
        cursor.execute("""
        CREATE VIEW combined_trades_view AS
            WITH amounts_query AS (
                SELECT
                A.tx_hash AS txhash,
                A.log_index AS logindex,
                A.timestamp AS time,
                A.location AS location,
                FE.amount1_in AS first1in,
                FE.amount0_in AS first0in,
                FE.token0_identifier AS firsttoken0,
                FE.token1_identifier AS firsttoken1,
                LE.amount0_out AS last0out,
                LE.amount1_out AS last1out,
                LE.token0_identifier AS lasttoken0,
                LE.token1_identifier AS lasttoken1
                FROM amm_swaps A
                LEFT JOIN amm_swaps FE ON
                FE.tx_hash = A.tx_hash AND FE.log_index=(SELECT MIN(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
                LEFT JOIN amm_swaps LE ON
                LE.tx_hash = A.tx_hash AND LE.log_index=(SELECT MAX(log_index) FROM amm_swaps WHERE tx_hash=A.tx_hash)
                WHERE A.tx_hash IN (SELECT DISTINCT tx_hash FROM amm_swaps) GROUP BY A.tx_hash
            ), C1 AS (
                SELECT lasttoken0 AS base1, firsttoken0 AS quote1, last0out AS amount1, cast(first0in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
                FROM amounts_query
                WHERE first0in > 0 AND last0out > 0 AND first1in == 0 AND last1out == 0
            ), C2 AS (
                SELECT lasttoken1 AS base1, firsttoken0 AS quote1, last1out AS amount1, cast(first0in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
                FROM amounts_query
                WHERE first0in > 0 AND last1out > 0 AND first1in == 0 AND last0out == 0
            ), C3 AS (
                SELECT lasttoken0 AS base1, firsttoken1 AS quote1, last0out AS amount1, CAST(first1in AS REAL) / CAST(last0out AS REAL) AS rate1, txhash, logindex, time, location
                FROM amounts_query
                WHERE first1in > 0 AND last0out > 0 AND first0in == 0 AND last1out == 0
            ), C4 AS (
                SELECT lasttoken1 AS base1, firsttoken1 AS quote1, last1out AS amount1, CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1, txhash, logindex, time, location
                FROM amounts_query
                WHERE first1in > 0 AND last1out > 0 AND first0in == 0 AND last0out == 0
            ), C5 AS (
                SELECT
                    lasttoken1 AS base1,
                    firsttoken1 AS quote1,
                    (CAST(last1out AS REAL) / 2) AS amount1,
                    CAST(first1in AS REAL) / (CAST(last1out AS REAL) / 2) as rate1,
                    lasttoken1 AS base2,
                    firsttoken0 AS quote2,
                    (CAST(last1out AS REAL) / 2) AS amount2,
                    CAST(first0in AS REAL) / (CAST(last1out AS REAL) / 2) AS rate2,
                    txhash, logindex, time, location
                FROM amounts_query
                WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out == 0
            ), C6 AS (
                SELECT
                    lasttoken1 AS base1,
                    firsttoken1 AS quote1,
                    last1out AS amount1,
                    CAST(first1in AS REAL) / CAST(last1out AS REAL) AS rate1,
                    lasttoken0 AS base2,
                    firsttoken0 AS quote2,
                    last0out AS amount2,
                    CAST(first0in AS REAL) / CAST(last0out AS REAL) AS rate2,
                    txhash, logindex, time, location
                FROM amounts_query
                WHERE first1in > 0 AND first0in > 0 AND last1out > 0 AND last0out > 0
            ), SWAPS AS (
            SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C1
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C2
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C3
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C4
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C5
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C5
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base1 AS base_asset, quote1 AS quote_asset, amount1 AS amount, rate1 AS rate, txhash, logindex, time, location FROM C6
            UNION ALL /* using union all as there can be no duplicates so no need to handle them */
            SELECT base2 AS base_asset, quote2 AS quote_asset, amount2 AS amount, rate2 AS rate, txhash, logindex, time, location FROM C6
        )
        SELECT
            txhash + logindex AS id,
            time,
            location,
            base_asset,
            quote_asset,
            'A' AS type, /* always a BUY */
            amount,
            rate,
            NULL AS fee, /* no fee */
            NULL AS fee_currency, /* no fee */
            txhash AS link,
            NULL AS notes /* no notes */
        FROM SWAPS
        UNION ALL /* using union all as there can be no duplicates so no need to handle them */
        SELECT * from trades;
        """)  # noqa: E501

        # this is cascaded when `history_events` is dropped, so keep a copy
        history_events_mappings = cursor.execute('SELECT * FROM history_events_mappings').fetchall()  # noqa: E501
        cursor.execute("""
        CREATE TABLE history_events_copy (
            identifier INTEGER NOT NULL PRIMARY KEY,
            event_identifier BLOB NOT NULL,
            sequence_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            location TEXT NOT NULL,
            location_label TEXT,
            asset TEXT NOT NULL,
            amount TEXT NOT NULL,
            usd_value TEXT NOT NULL,
            notes TEXT,
            type TEXT NOT NULL,
            subtype TEXT,
            counterparty TEXT,
            extra_data TEXT,
            UNIQUE(event_identifier, sequence_index)
        );
        """)

        history_events = cursor.execute('SELECT * FROM history_events')
        new_history_events = []
        for history_event in history_events:
            history_event = list(history_event)  # noqa: PLW2901
            try:
                history_event[1] = _deserialize_event_identifier(history_event[1])
            except DeserializationError:
                continue
            new_history_events.append(tuple(history_event))
        cursor.executemany(
            'INSERT INTO history_events_copy VALUES'
            '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
            new_history_events,
        )
        cursor.execute('DROP TABLE history_events;')
        cursor.execute('ALTER TABLE history_events_copy RENAME TO history_events;')

        cursor.executemany(
            'INSERT INTO history_events_mappings(parent_identifier, value) VALUES(?, ?);',
            history_events_mappings,
        )

    @progress_step(description='Refactoring blockchain account labels.')
    def _refactor_blockchain_account_labels(cursor: 'DBCursor') -> None:
        cursor.execute("UPDATE blockchain_accounts SET label = NULL WHERE label =''")

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
