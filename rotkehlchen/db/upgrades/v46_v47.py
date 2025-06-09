import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.data_import.importers.constants import ROTKI_EVENT_PREFIX
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.settings import DEFAULT_ACTIVE_MODULES
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v46->v47 upgrade')
def upgrade_v46_to_v47(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v46 to v47. This was in v1.38 release.

    - Add Binance Smart Chain location
    """
    @progress_step(description='Adding new locations to the DB.')
    def _add_new_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
            /* Binance Smart Chain */
            INSERT OR IGNORE INTO location(location, seq) VALUES ('v', 54);
            """)

    @progress_step(description='Remove extrainternaltx cache.')
    def _clean_cache(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("DELETE FROM key_value_cache WHERE name LIKE 'extrainternaltx_%'")

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm events except for the customized ones and those in zksync lite.
        Code taken from previous upgrade
        """
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

    @progress_step(description='Adjust block production events.')
    def _adjust_block_production_events(write_cursor: 'DBCursor') -> None:
        """Due to the block production changes we need to make sure that all MEV
        events are recalculated and that we properly use INFORMATIONAL when the recipient
        is not tracked.
        """
        # Delete MEV events that were already moved to the block events. They will rerun
        write_cursor.execute(
            "DELETE FROM history_events WHERE sequence_index > 1 AND event_identifier LIKE 'BP1_%'",  # noqa: E501
        )
        # Modify all MEV relayer events to be informational and properly display new notes
        write_cursor.execute("""
        UPDATE history_events
        SET
            type = 'informational',
            subtype = 'mev reward',
            notes = 'Validator ' ||
            (SELECT SE.validator_index FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier) ||
            ' produced block ' ||
            (SELECT SE.is_exit_or_blocknumber FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier) ||
            '. Relayer reported ' ||
            history_events.amount ||
            ' ETH as the MEV reward going to ' ||
            COALESCE(history_events.location_label, 'Unknown')
        WHERE
            entry_type = 4 AND
            sequence_index = 1 AND
        EXISTS (SELECT 1 FROM eth_staking_events_info SE WHERE SE.identifier = history_events.identifier);
        """)  # noqa: E501
        # Modify block proposals to be informational if the fee recipient is not tracked
        write_cursor.execute("""
        UPDATE history_events
        SET type = 'informational'
        WHERE entry_type = 4 AND sequence_index = 0 AND location_label NOT IN (
            SELECT account FROM blockchain_accounts WHERE blockchain = 'ETH'
        );
        """)

    @progress_step(description='Remove unneeded nft collection assets (may take some time).')
    def _remove_nft_collection_assets(write_cursor: 'DBCursor') -> None:
        """Remove erc721 assets that have no collectible id, and also any erc20 assets
        with the same address that were incorrectly added.
        """
        with (globaldb_conn := GlobalDBHandler().conn).read_ctx() as global_db_cursor:
            globaldb_identifiers_to_remove = tuple(entry[0] for entry in global_db_cursor.execute(
                'SELECT identifier FROM assets WHERE identifier IN ('
                "SELECT identifier FROM evm_tokens WHERE token_kind = 'B' "
                "UNION SELECT REPLACE(identifier, 'erc721', 'erc20') "
                "FROM evm_tokens WHERE token_kind = 'B') AND "
                "identifier NOT LIKE 'eip155:%/erc721:0x%/%'",  # Skip identifiers with collectible ids # noqa: E501
            ))

        if (num_to_remove := len(globaldb_identifiers_to_remove)) != 0:
            log.debug(f'Deleting {num_to_remove} globaldb assets...')
            placeholders = ','.join(['?'] * len(globaldb_identifiers_to_remove))
            tables_with_assets = (
                ('assets', 'identifier'),
                ('evm_tokens', 'identifier'),
                ('common_asset_details', 'identifier'),
                ('multiasset_mappings', 'asset'),
                ('price_history', 'from_asset'),
                ('price_history', 'to_asset'),
                ('underlying_tokens_list', 'identifier'),
                ('underlying_tokens_list', 'parent_token_entry'),
                ('user_owned_assets', 'asset_id'),
            )
            total = len(tables_with_assets)
            with globaldb_conn.write_ctx() as global_db_write_cursor:
                log.debug('Deleting from globaldb...')
                # We disable foreign keys because that ended up being the fastest way to delete
                # the assets. Without that a CASCADE deletion happens but it turned to be really
                # slow, around ~8 mins in my case with ~300 assets to delete and ~30K assets in my
                # globaldb. First I tried adding indexes in the globaldb to the tables that
                # reference the assets table but it lowered the time only to ~6-7 minutes.
                # With direct deletion without FKs it's almost instant.
                global_db_write_cursor.executescript('PRAGMA foreign_keys = OFF;')
                for step, (table_name, column_name) in enumerate(tables_with_assets, start=1):
                    log.debug(f'{step}/{total}: Deleting references in the {table_name} table for {column_name}')  # noqa: E501
                    global_db_write_cursor.execute(f'DELETE FROM {table_name} WHERE {column_name} IN ({placeholders})', globaldb_identifiers_to_remove)  # noqa: E501

                global_db_write_cursor.executescript('PRAGMA foreign_keys = ON;')

        userdb_identifiers_to_remove = tuple(set({
            x[0] for x in write_cursor.execute(
                "SELECT identifier FROM assets WHERE identifier LIKE 'eip155:%/erc721:0x%' "
                "AND identifier NOT LIKE 'eip155:%/erc721:0x%/%'",
            )}).union(set(globaldb_identifiers_to_remove)))
        if len(userdb_identifiers_to_remove) == 0:
            log.debug('No identifiers to remove from userDB')
            return

        log.debug('Deleting from user db...')
        # Load any data associated with these identifiers that might actually be valuable and
        # save it in a temporary table that will need to be dealt with manually.
        # For 99% of users no data should be found here.
        selected_data = {}
        tables_to_delete_from = []
        values_placeholders = ','.join(['(?)'] * len(userdb_identifiers_to_remove))
        for table, columns in (
            ('history_events', ('asset',)),
            ('manually_tracked_balances', ('asset',)),
            ('trades', ('base_asset', 'quote_asset', 'fee_currency')),
            ('margin_positions', ('pl_currency', 'fee_currency')),
            ('zksynclite_transactions', ('asset',)),
            ('zksynclite_swaps', ('from_asset', 'to_asset')),
            ('nfts', ('identifier', 'last_price_asset')),
        ):
            column_str = ','.join([f'{table}.{column}' for column in columns])
            result = write_cursor.execute(
                f'WITH asset_list(value) AS (VALUES {values_placeholders}) '
                f'SELECT * FROM {table} '
                f'WHERE EXISTS (SELECT 1 FROM asset_list WHERE value IN ({column_str}))',
                userdb_identifiers_to_remove,
            ).fetchall()
            if len(result) > 0:
                selected_data[table] = result
                tables_to_delete_from.append((table, columns))

        if len(selected_data) > 0:
            log.error('Found data associated with old erc721 tokens. Saving it in the temp_erc721_data table.')  # noqa: E501
            write_cursor.execute('CREATE TABLE temp_erc721_data (table_name TEXT, data TEXT)')
            for table, data in selected_data.items():
                try:
                    write_cursor.execute(
                        'INSERT INTO temp_erc721_data(table_name, data) VALUES(?, ?)',
                        (table, json.dumps(data)),
                    )
                except (TypeError, OverflowError, UnicodeEncodeError) as e:
                    log.error(f'Failed to serialize {data!s} as json due to {e!s}')

        # Delete the old erc721 assets and any associated data.
        # The data in timed_balances and evm_accounts_details will likely be present and
        # has no value so it is not included in the select queries above.
        for table, columns in tuple(tables_to_delete_from) + (
            ('timed_balances', ('currency',)),
            ('evm_accounts_details', ('value',)),
            ('assets', ('identifier',)),
        ):
            column_str = ','.join([f'{table}.{column}' for column in columns])
            write_cursor.execute(
                f'WITH asset_list(value) AS (VALUES {values_placeholders}) '
                f'DELETE FROM {table} '
                f'WHERE EXISTS (SELECT 1 FROM asset_list WHERE value IN ({column_str}))',
                userdb_identifiers_to_remove,
            )

    @progress_step(description='Reset exchanges events and cache')
    def _reset_exchanges_events_and_cache(write_cursor: 'DBCursor') -> None:
        for location in (Location.GEMINI, Location.BYBIT, Location.COINBASE):
            write_cursor.execute(
                'DELETE FROM history_events WHERE location=? AND event_identifier NOT LIKE ?',
                ((db_loc := location.serialize_for_db()), f'{ROTKI_EVENT_PREFIX}_%'),
            )
            write_cursor.execute(
                "DELETE FROM trades WHERE location=? AND link != ''",
                (db_loc,),
            )
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name LIKE ? OR name LIKE ? OR name LIKE ? OR name LIKE ?',  # noqa: E501
                (
                    f'{(loc := location.serialize())}_history_events_%',
                    f'{loc}_trades_%',
                    f'{loc}_margins_%',
                    f'{loc}_asset_movements_%',
                ),
            )

        write_cursor.execute(
            'DELETE FROM key_value_cache WHERE name LIKE ? OR name LIKE ?',
            (f'{(coinbase_loc := Location.COINBASE.serialize())}_%_last_query_ts', f'{coinbase_loc}_%_last_query_id'),  # noqa: E501
        )

    @progress_step(description='Remove old accounting rules')
    def _remove_old_accounting_rules(write_cursor: 'DBCursor') -> None:
        """Remove unused `deposit asset` and `remove asset` accounting rules.
        This must be done here as the accounting rule updates don't currently support deletion.
        See https://github.com/orgs/rotki/projects/11?pane=issue&itemId=96831912
        """
        counterparties = ('aave-v1', 'aave-v2', 'aave-v3', 'compound', 'compound-v3', 'Locked GNO', 'yearn-v1', 'yearn-v2')  # noqa: E501
        write_cursor.executemany(
            'DELETE FROM accounting_rules WHERE type=? AND subtype=? AND counterparty=?',
            [
                (event_type, event_subtype, counterparty)
                for counterparty in counterparties
                for event_type, event_subtype in (
                    ('deposit', 'deposit asset'),
                    ('withdrawal', 'remove asset'),
                )
            ],
        )

    @progress_step(description='Remove manual historical oracle')
    def _remove_manual_historical_price_oracle(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'SELECT value FROM settings WHERE name=?',
            ('historical_price_oracles',),
        )
        if (result := write_cursor.fetchone()) is None:
            return

        try:
            oracles = [x for x in json.loads(result[0]) if x != 'manual']
        except json.JSONDecodeError:
            log.error(f'During v46->v47 DB upgrade, a non-json historical_price_oracles entry was found: {result[0]}.')  # noqa: E501
            oracles = [x.serialize() for x in DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER]

        write_cursor.execute(
            'UPDATE settings SET value=? WHERE name=?',
            (json.dumps(oracles), 'historical_price_oracles'),
        )

    @progress_step(description='Remove deleted ethereum modules')
    def _remove_deleted_ethereum_modules(write_cursor: 'DBCursor') -> None:
        deleted_modules = ('compound', 'yearn_vaults', 'yearn_vaults_v2', 'aave')
        write_cursor.execute(
            'SELECT value FROM settings WHERE name=?',
            ('active_modules',),
        )
        if (result := write_cursor.fetchone()) is None:
            return

        try:
            modules: Sequence[str] = [
                x for x in json.loads(result[0])
                if x not in deleted_modules
            ]
        except json.JSONDecodeError:
            log.error(f'During v46->v47 DB upgrade, a non-json ethereum module entry was found: {result[0]}.')  # noqa: E501
            modules = DEFAULT_ACTIVE_MODULES

        write_cursor.execute(
            'UPDATE settings SET value=? WHERE name=?',
            (json.dumps(modules), 'active_modules'),
        )
        write_cursor.executemany(
            'DELETE FROM multisettings WHERE name=?',
            [(f'queried_address_{x}',) for x in deleted_modules],
        )

    @progress_step(description='Remove old accounting rules')
    def _drop_usd_value_column(write_cursor: 'DBCursor') -> None:
        """Drops the usd value column from history events"""
        write_cursor.execute('ALTER TABLE history_events DROP COLUMN usd_value;')

    @progress_step(description='Remove old setting')
    def _remove_old_setting(write_cursor: 'DBCursor') -> None:
        """Removes a key that wasn't correctly deleted for one user and might affect others"""
        write_cursor.execute("DELETE FROM settings WHERE name='last_data_upload_ts'")

    @progress_step(description='Upgrading old style binance and avalanche tokens')
    def _upgrade_binance_avalanche_tokens(write_cursor: 'DBCursor') -> None:
        """If a user has any old style binance and avalanche tokens that were upgraded in the
        global DB we have to upgrade them here"""
        changed_ids_mappings = {
            'BIDR': 'eip155:56/erc20:0x9A2f5556e9A637e8fBcE886d8e3cf8b316a1D8a2',
            'COS': 'eip155:56/erc20:0x96Dd399F9c3AFda1F194182F71600F1B65946501',
            'PHB': 'eip155:56/erc20:0x0409633A72D846fc5BBe2f98D88564D35987904D',
            'BUX': 'eip155:56/erc20:0x211FfbE424b90e25a15531ca322adF1559779E45',  # already exists in packaged DB  # noqa: E501
            'LNCHX': 'eip155:56/erc20:0xC43570263e924C8cF721F4b9c72eEd1AEC4Eb7DF',
            'POLX': 'eip155:56/erc20:0xbe510da084E084e3C27b20D79C135Dc841135c7F',
            'ICA': 'eip155:56/erc20:0x0ca2f09eCa544b61b91d149dEA2580c455c564b2',
            'TEDDY': 'eip155:43114/erc20:0x094bd7B2D99711A1486FB94d4395801C6d0fdDcC',
        }
        # Get all tables that reference assets via foreign keys
        fk_table_data = write_cursor.execute(
        "SELECT m.name as table_name, p.'from' as column_name "
        "FROM sqlite_master m JOIN pragma_foreign_key_list(m.name) p "
        "ON m.name != 'assets' WHERE p.'table' = 'assets' AND m.type = 'table'",
        ).fetchall()

        for old_id, new_id in changed_ids_mappings.items():
            # Check if the new ID already exists
            write_cursor.execute('SELECT COUNT(*) FROM assets WHERE identifier=?', (new_id,))
            if write_cursor.fetchone()[0] != 0:  # exists so for each foreign key relation update it  # noqa: E501
                for table_name, column_name in fk_table_data:
                    write_cursor.execute(
                        f'UPDATE {table_name} SET {column_name}=? WHERE {column_name}=?',
                        (new_id, old_id),
                    )

                # and finally delete the old asset
                write_cursor.execute('DELETE FROM assets WHERE identifier = ?', (old_id,))

            else:  # does not exist, so just modify
                write_cursor.execute(
                    'UPDATE assets SET identifier=? WHERE identifier=?', (new_id, old_id),
                )

        # finally check if the ignored_assets contain any of these tokens and replace them
        entries = write_cursor.execute(
            "SELECT value FROM multisettings WHERE name='ignored_asset' AND value "
            f"IN({','.join(['?'] * len(changed_ids_mappings))})",
            list(changed_ids_mappings),
        ).fetchall()
        for entry in entries:
            write_cursor.execute(
                "SELECT COUNT(*) FROM multisettings WHERE name='ignored_asset' AND value=?",
                (changed_ids_mappings[entry[0]],),
            )
            if write_cursor.fetchone()[0] != 0:  # exists so can't update, just delete the old one
                write_cursor.execute(
                    "DELETE FROM multisettings WHERE name='ignored_asset' AND value=?",
                    (entry[0],),
                )
            else:
                write_cursor.execute(
                    "UPDATE multisettings SET value=? WHERE name='ignored_asset' AND value=?",
                    (changed_ids_mappings[entry[0]], entry[0]),
                )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
