import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
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

    @progress_step(description='Remove unneeded nft collection assets (may take some time).')
    def _remove_nft_collection_assets(write_cursor: 'DBCursor') -> None:
        """Remove erc721 assets that have no collectible id, and also any erc20 assets
        with the same address that were incorrectly added.
        """
        with (globaldb_conn := GlobalDBHandler().conn).read_ctx() as global_db_cursor:
            identifiers_to_remove = tuple(entry[0] for entry in global_db_cursor.execute(
                'SELECT identifier FROM assets WHERE identifier IN ('
                "SELECT identifier FROM evm_tokens WHERE token_kind = 'B' "
                "UNION SELECT REPLACE(identifier, 'erc721', 'erc20') "
                "FROM evm_tokens WHERE token_kind = 'B');",
            ))

        if (num_to_remove := len(identifiers_to_remove)) == 0:
            return

        log.debug(f'Deleting {num_to_remove} assets...')
        placeholders = ','.join(['?'] * len(identifiers_to_remove))
        with globaldb_conn.write_ctx() as global_db_write_cursor:
            log.debug('Deleting from globaldb...')
            global_db_write_cursor.execute(f'DELETE FROM assets WHERE identifier IN ({placeholders})', identifiers_to_remove)  # noqa: E501

        log.debug('Deleting from user db...')
        # Load any data associated with these identifiers that might actually be valuable and
        # save it in a temporary table that will need to be dealt with manually.
        # For 99% of users no data should be found here.
        selected_data = {}
        tables_to_delete_from = []
        values_placeholders = ','.join(['(?)'] * len(identifiers_to_remove))
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
                identifiers_to_remove,
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
                identifiers_to_remove,
            )

    # TODO: Put the history events reset step BEFORE _remove_nft_collection_assets so that
    # most history events are gone when it checks for data associated with old erc721 assets.

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
