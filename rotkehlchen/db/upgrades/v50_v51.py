import json
import logging
from json import JSONDecodeError
from typing import TYPE_CHECKING

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.constants import (
    CONTRACT_TAG_BACKGROUND_COLOR,
    CONTRACT_TAG_DESCRIPTION,
    CONTRACT_TAG_FOREGROUND_COLOR,
    CONTRACT_TAG_NAME,
)
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v50->v51 upgrade')
def upgrade_v50_to_v51(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v50 to v51. This happened in the v1.42 release."""

    @progress_step(description='Adding Avalanche location to the DB.')
    def _add_avalanche_location(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Avalanche */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('x', 56);
        """)

    @progress_step(description='Rename event_identifier column to group_identifier in history_events table.')  # noqa: E501
    def _rename_event_identifier_to_group_identifier(write_cursor: 'DBCursor') -> None:
        """Rename event_identifier column to group_identifier in history_events table."""
        write_cursor.switch_foreign_keys('OFF')
        update_table_schema(
            write_cursor=write_cursor,
            table_name='history_events',
            schema="""identifier INTEGER NOT NULL PRIMARY KEY,
            entry_type INTEGER NOT NULL,
            group_identifier TEXT NOT NULL,
            sequence_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            location_label TEXT,
            asset TEXT NOT NULL,
            amount TEXT NOT NULL,
            notes TEXT,
            type TEXT NOT NULL,
            subtype TEXT NOT NULL,
            extra_data TEXT,
            ignored INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            UNIQUE(group_identifier, sequence_index)""",
            insert_columns='identifier, entry_type, event_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype, extra_data, ignored',  # noqa: E501
            insert_order='(identifier, entry_type, group_identifier, sequence_index, timestamp, location, location_label, asset, amount, notes, type, subtype, extra_data, ignored)',  # noqa: E501
        )
        write_cursor.switch_foreign_keys('ON')

    @progress_step(description='Create new tables.')
    def _add_new_tables(write_cursor: 'DBCursor') -> None:
        """Add new tables
        - lido_csm_node_operators
        - lido_csm_node_operator_metrics
        - event_metrics
        - solana_ata_address_mappings
        """
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS lido_csm_node_operators (
            node_operator_id INTEGER NOT NULL PRIMARY KEY,
            address TEXT NOT NULL,
            blockchain TEXT GENERATED ALWAYS AS ('ETH') VIRTUAL,
            FOREIGN KEY(blockchain, address)
                REFERENCES blockchain_accounts(blockchain, account)
                ON DELETE CASCADE
        );
        """)
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS lido_csm_node_operator_metrics (
            node_operator_id INTEGER NOT NULL PRIMARY KEY,
            operator_type_id INTEGER,
            bond_current TEXT,
            bond_required TEXT,
            bond_claimable TEXT,
            total_deposited_validators INTEGER,
            rewards_pending TEXT,
            updated_ts INTEGER,
            FOREIGN KEY(node_operator_id)
                REFERENCES lido_csm_node_operators(node_operator_id)
                ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_metrics (
            id INTEGER NOT NULL PRIMARY KEY,
            event_identifier INTEGER NOT NULL REFERENCES history_events(identifier) ON DELETE CASCADE,
            location CHAR(1) NOT NULL,
            location_label TEXT,
            protocol TEXT,
            metric_key TEXT NOT NULL,
            metric_value TEXT NOT NULL,
            asset TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            sequence_index INTEGER NOT NULL,
            sort_key INTEGER NOT NULL,
            UNIQUE(event_identifier, location_label, protocol, metric_key, asset)
        );
        """)  # noqa: E501
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_event '
            'ON event_metrics(event_identifier);',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_location_label '
            'ON event_metrics(location_label);',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_protocol '
            'ON event_metrics(protocol);',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key '
            'ON event_metrics(metric_key);',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key_timestamp '
            'ON event_metrics(metric_key, timestamp);',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key_asset_sort_key '
            'ON event_metrics(metric_key, asset, sort_key);',
        )
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_event_metrics_asset '
            'ON event_metrics(asset);',
        )
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS solana_ata_address_mappings (
            blockchain TEXT GENERATED ALWAYS AS ('SOLANA') VIRTUAL,
            account TEXT NOT NULL,
            ata_address TEXT NOT NULL,
            PRIMARY KEY(account, ata_address),
            FOREIGN KEY(blockchain, account) REFERENCES blockchain_accounts(blockchain, account) ON DELETE CASCADE
        );
        """)  # noqa: E501

    @progress_step(description='Adding reserved Contract tag.')
    def _add_contract_tag(write_cursor: 'DBCursor') -> None:
        """Adds the reserved 'Contract' system tag for tagging smart contract addresses.
        Renames any existing user 'Contract' tag to 'Contract (Custom)' first.
        """
        write_cursor.switch_foreign_keys('OFF')
        write_cursor.execute(
            'UPDATE tags SET name = ? WHERE name = ? COLLATE NOCASE',
            (f'{CONTRACT_TAG_NAME} (Custom)', CONTRACT_TAG_NAME),
        )
        write_cursor.execute(
            'UPDATE tag_mappings SET tag_name = ? WHERE tag_name = ? COLLATE NOCASE',
            (f'{CONTRACT_TAG_NAME} (Custom)', CONTRACT_TAG_NAME),
        )
        write_cursor.switch_foreign_keys('ON')
        try:
            write_cursor.execute(
                'INSERT INTO tags(name, description, background_color, foreground_color) '
                'VALUES (?, ?, ?, ?)',
                (CONTRACT_TAG_NAME, CONTRACT_TAG_DESCRIPTION,
                 CONTRACT_TAG_BACKGROUND_COLOR, CONTRACT_TAG_FOREGROUND_COLOR),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            log.error(f'Failed to insert Contract tag during upgrade: {e}')

    @progress_step(description='Tagging Safe contract addresses.')
    def _tag_safe_addresses(write_cursor: 'DBCursor') -> None:
        """Tags existing tracked accounts that have Safe deployment events with the Contract tag.

        Note: This step must run before any step that deletes history_events, as it depends
        on the presence of Safe deployment events to identify contract addresses.
        """
        write_cursor.execute(
            """
            INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name)
            SELECT B.account, ?
            FROM blockchain_accounts B
            WHERE EXISTS (
                SELECT 1
                FROM chain_events_info C
                JOIN history_events H ON C.identifier = H.identifier
                WHERE C.address = B.account
                  AND C.counterparty = ?
                  AND H.type = ?
                  AND H.subtype = ?
            )
            """,
            (CONTRACT_TAG_NAME, CPT_SAFE_MULTISIG,
             HistoryEventType.INFORMATIONAL.serialize(),
             HistoryEventSubType.CREATE.serialize()),
        )

    @progress_step(description='Migrate last event processing ts cache key.')
    def _migrate_last_event_processing_ts_cache_key(write_cursor: 'DBCursor') -> None:
        """Migrates the last event processing ts cache key to a new eth2 events specific key.
        This is to differentiate it from the new last processing ts key for asset movements.
        """
        write_cursor.execute(
            'UPDATE key_value_cache SET name=? WHERE name=?',
            ('last_eth2_events_processing_ts', 'last_events_processing_task_ts'),
        )

    @progress_step(description='Remove Monerium profile data from cached credentials.')
    def _remove_monerium_profiles_from_cache(write_cursor: 'DBCursor') -> None:
        """Remove stored Monerium OAuth profile data from cached credentials."""
        if (result := write_cursor.execute(
            'SELECT value FROM key_value_cache WHERE name=?',
            (DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS.value,),
        ).fetchone()) is None:
            return

        raw_value = result[0]
        try:
            cached_data = json.loads(raw_value)
        except (JSONDecodeError, TypeError) as exc:
            log.error(
                'Failed to parse stored Monerium OAuth credentials during upgrade: '
                f'{exc!s}',
            )
            return

        if not isinstance(cached_data, dict):
            log.error('Unexpected Monerium OAuth credentials format during upgrade. Bailing')
            return

        if 'profiles' not in cached_data and 'default_profile_id' not in cached_data:
            log.debug(f'_remove_monerium_profiles_from_cache bails because profiles and default_profile_id are not in the cached data. {cached_data=}')  # noqa: E501
            return

        cached_data.pop('profiles', None)
        cached_data.pop('default_profile_id', None)
        write_cursor.execute(
            'UPDATE key_value_cache SET value=? WHERE name=?',
            (json.dumps(cached_data), DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS.value),
        )
        log.debug(f'_remove_monerium_profiles_from_cache successfully saved in the database {cached_data=}')  # noqa: E501

    @progress_step(description='Migrating deposit/withdrawal subtypes for customized events.')
    def _migrate_defi_protocol_subtypes(write_cursor: 'DBCursor') -> None:
        """Migrate customized events from deposit_asset/remove_asset to
        deposit_to_protocol/withdraw_from_protocol subtypes.

        Only affects customized events that:
        - Are not asset movements
        - Have a counterparty set (indicating DeFi protocol interaction)
        """
        write_cursor.execute(
            """
            UPDATE history_events
            SET subtype = CASE
                WHEN type = ? AND subtype = ? THEN ?
                WHEN type = ? AND subtype = ? THEN ?
            END
            FROM chain_events_info
            WHERE history_events.identifier = chain_events_info.identifier
                AND chain_events_info.counterparty IS NOT NULL
                AND entry_type != ?
                AND history_events.identifier IN (
                    SELECT parent_identifier FROM history_events_mappings
                    WHERE name = ? AND value = ?
                )
                AND ((type = ? AND subtype = ?) OR (type = ? AND subtype = ?))
            """,
            (
                # CASE: deposit/deposit_asset -> deposit_to_protocol
                HistoryEventType.DEPOSIT.serialize(),
                HistoryEventSubType.DEPOSIT_ASSET.serialize(),
                HistoryEventSubType.DEPOSIT_TO_PROTOCOL.serialize(),
                # CASE: withdrawal/remove_asset -> withdraw_from_protocol
                HistoryEventType.WITHDRAWAL.serialize(),
                HistoryEventSubType.REMOVE_ASSET.serialize(),
                HistoryEventSubType.WITHDRAW_FROM_PROTOCOL.serialize(),
                # WHERE: exclude asset movements, only customized, only with counterparty
                HistoryBaseEntryType.ASSET_MOVEMENT_EVENT.value,
                HISTORY_MAPPING_KEY_STATE,
                HISTORY_MAPPING_STATE_CUSTOMIZED,
                HistoryEventType.DEPOSIT.serialize(),
                HistoryEventSubType.DEPOSIT_ASSET.serialize(),
                HistoryEventType.WITHDRAWAL.serialize(),
                HistoryEventSubType.REMOVE_ASSET.serialize(),
            ),
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
