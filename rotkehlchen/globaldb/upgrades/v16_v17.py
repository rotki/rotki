import logging
from typing import TYPE_CHECKING

from eth_utils import to_checksum_address

from rotkehlchen.assets.types import AssetFlag
from rotkehlchen.chain.evm.decoding.compound.v3.constants import CPT_COMPOUND_V3
from rotkehlchen.constants.assets import A_STETH
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_globaldb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='globaldb v16->v17 upgrade')
def migrate_to_v17(
        connection: DBConnection,
        progress_handler: DBUpgradeProgressHandler,
) -> None:
    """This upgrade takes place in v1.44.0."""

    @progress_step('Drop the unused location_unsupported_assets table.')
    def _drop_location_unsupported_assets_table(write_cursor: DBCursor) -> None:
        """The exchange unsupported-asset blocklist was removed, so the table that backed
        it is no longer used. Drop it."""
        write_cursor.execute('DROP TABLE IF EXISTS location_unsupported_assets')

    @progress_step('Adding moralis to price_history_source_types')
    def _add_moralis_price_source(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'INSERT OR IGNORE INTO price_history_source_types(type, seq) VALUES (?, ?)',
            ('J', 10),
        )

    @progress_step('Optimize historical price lookup by asset pair and timestamp.')
    def _optimize_historical_price_lookup(write_cursor: DBCursor) -> None:
        write_cursor.execute('DROP INDEX IF EXISTS idx_price_history_identifier')
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_price_history_pair_timestamp '
            'ON price_history(from_asset, to_asset, timestamp, source_type)',
        )

    @progress_step('Create and populate the asset flags table.')
    def _create_and_populate_asset_flags(write_cursor: DBCursor) -> None:
        write_cursor.execute("""CREATE TABLE IF NOT EXISTS asset_flags (
            identifier TEXT NOT NULL COLLATE NOCASE,
            flag TEXT NOT NULL,
            PRIMARY KEY(identifier, flag),
            FOREIGN KEY(identifier) REFERENCES assets(identifier)
                ON UPDATE CASCADE ON DELETE CASCADE
        );""")
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) VALUES (?, ?)',
            (A_STETH.identifier, AssetFlag.REBASING),
        )
        write_cursor.execute(
            'INSERT OR IGNORE INTO asset_flags(identifier, flag) '
            'SELECT identifier, ? FROM evm_tokens WHERE protocol = ?',
            (AssetFlag.REBASING, CPT_COMPOUND_V3),
        )

    @progress_step('Canonicalize evm token addresses that were not checksummed.')
    def _checksum_evm_token_addresses(write_cursor: DBCursor) -> None:
        """Rewrite the evm tokens whose address was stored without being checksummed.

        A contract call served by an indexer used to hand back the raw abi decoded address,
        which is lowercased, so a token first seen through one of those was created under a
        non canonical address and identifier. Identifiers are compared exactly, so such an
        identifier never matches the one built from the same address once checksummed.

        An address that was never checksummed is uniformly cased, which sqlite can filter on
        directly, so the keccak behind to_checksum_address is only paid for a handful of rows
        instead of every token in the db.
        """
        renames = []
        for identifier, address in write_cursor.execute(
                'SELECT identifier, address FROM evm_tokens WHERE '
                'substr(address, 3) = lower(substr(address, 3)) OR '
                'substr(address, 3) = upper(substr(address, 3))',
        ).fetchall():
            try:
                checksummed = to_checksum_address(address)
            except ValueError:
                log.error('Skipping evm token %s with invalid address %s', identifier, address)
                continue

            if checksummed != address:
                renames.append((identifier, identifier.replace(address, checksummed), checksummed))

        if len(renames) == 0:
            return

        log.debug('Canonicalizing the address of %s evm tokens', len(renames))
        # assets.identifier is COLLATE NOCASE and sqlite decides whether ON UPDATE CASCADE
        # fires by comparing the old and the new parent key under that collation, so a change
        # of casing alone never reaches the children. Every column holding an identifier has
        # to be written explicitly. Which ones those are is asked of the db rather than
        # listed here, so a column cannot be missed.
        identifier_columns = [('assets', 'identifier')]
        tables = [row[0] for row in write_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'",
        )]
        for table in tables:
            identifier_columns.extend(
                (table, fk_entry[3])
                for fk_entry in write_cursor.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()  # noqa: E501
                if fk_entry[2] in ('assets', 'evm_tokens') and fk_entry[4] == 'identifier'
            )

        # these two hold an identifier without declaring a foreign key for it
        identifier_columns.extend(
            (table, 'local_id')
            for table in ('location_asset_mappings', 'counterparty_asset_mappings')
            if table in tables
        )
        for table, column in identifier_columns:
            write_cursor.executemany(
                f'UPDATE OR IGNORE {table} SET {column}=? WHERE {column}=?',
                [(new_identifier, identifier) for identifier, new_identifier, _ in renames],
            )

        write_cursor.executemany(  # keyed by the identifier they now have
            'UPDATE evm_tokens SET address=? WHERE identifier=?',
            [(address, new_identifier) for _, new_identifier, address in renames],
        )

    perform_globaldb_upgrade_steps(connection, progress_handler)
