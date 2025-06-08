import json
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import Asset
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.swap import (
    SwapEvent,
    create_swap_events,
    get_swap_spend_receive,
)
from rotkehlchen.history.events.structures.types import HistoryEventType
from rotkehlchen.history.events.utils import create_event_identifier_from_unique_id
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import AssetAmount, Location, Price
from rotkehlchen.utils.misc import ts_sec_to_ms
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def upgrade_trade_to_swap_events(
        row: tuple[Any, ...],
        kraken_ids_to_labels: dict[str, str],
        kraken_adjustments_data: dict[str, tuple[str, str, str]],
        kraken_ids_to_delete: set[str],
) -> list[SwapEvent]:
    """Convert a raw Trade db row into a list of SwapEvents.

    Kraken trades get special treatment using data from history events:
    - location_label is set from `kraken_ids_to_labels` and `kraken_adjustments_data`
    - adjustment trade amounts are set from `kraken_adjustments_data` since adjustment trade rates
      were calculated incorrectly previously.
    - adjustment events associated with a trade are added to `kraken_ids_to_delete`

    May raise:
    - DeserializationError
    - ValueError
    """
    spend, receive = get_swap_spend_receive(
        is_buy=row[4] in {'A', 'C'},  # A,C = buy, settlement buy; B,D = sell, settlement sell
        base_asset=Asset(row[2]),
        quote_asset=Asset(row[3]),
        amount=FVal(row[5]),
        rate=Price(FVal(row[6])),
    )

    # Special Kraken logic
    link, location_label = row[9], None
    if (
        (location := Location.deserialize_from_db(row[1])) == Location.KRAKEN and
        link is not None and
        len(link) > 10  # Coincidentally both normal and adjustment trade links must be at least 10 chars to be processed here.  # noqa: E501
    ):
        if link[:10] == 'adjustment':  # Adjustment trade links are 'adjustment' + a1.event_identifier + a2.event_identifier  # noqa: E501
            # Find which adjustment history event ids are present in this trade link.
            adjustments_for_this_trade = set()
            for adjustment_trade_id, adjustment_data in kraken_adjustments_data.items():
                if adjustment_trade_id not in link:
                    continue

                adjustments_for_this_trade.add(adjustment_trade_id)
                # Set location_label and amounts from the adjustment event data
                location_label, amount, subtype = adjustment_data
                if subtype == 'spend':
                    spend = AssetAmount(asset=spend.asset, amount=FVal(amount))
                elif subtype == 'receive':
                    receive = AssetAmount(asset=receive.asset, amount=FVal(amount))

                if len(adjustments_for_this_trade) == 2:
                    break  # Found both adjustments associated with this trade

            kraken_ids_to_delete.update(adjustments_for_this_trade)

        else:  # Normal kraken trade. Link is trade ID + timestamp.
            # Remove timestamp from link to get trade ID for label lookup.
            location_label = kraken_ids_to_labels.get(link[:-10])

    return create_swap_events(
        timestamp=ts_sec_to_ms(row[0]),
        location=location,
        spend=spend,
        receive=receive,
        fee=AssetAmount(
            asset=Asset(row[8]),
            amount=FVal(row[7]),
        ) if row[8] is not None and row[7] is not None else None,
        location_label=location_label,
        event_identifier=create_event_identifier_from_unique_id(
            location=location,
            unique_id=link,
        ),
        spend_notes=row[10],
    )


@enter_exit_debug_log(name='UserDB v47->v48 upgrade')
def upgrade_v47_to_v48(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v47 to v48. This was in v1.39 release."""

    @progress_step(description='Removing action_type table and simplifying ignored_actions')
    def _remove_action_types(write_cursor: 'DBCursor') -> None:
        """This upgrade drops the action_type table and modifies the ignored_actions table
        to remove the type column, making identifier the primary key.

        The type column is no longer needed as we're standardizing on a single action type.
        """
        update_table_schema(
            write_cursor=write_cursor,
            table_name='ignored_actions',
            schema='identifier TEXT PRIMARY KEY',
            insert_columns='identifier',
        )
        write_cursor.execute('DROP TABLE action_type')

    @progress_step(description='Adding evm transactions authorization list table')
    def _add_evm_transaction_authorization_list_table(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_transactions_authorizations (
            tx_id INTEGER NOT NULL PRIMARY KEY,
            nonce INTEGER NOT NULL,
            delegated_address TEXT NOT NULL,
            FOREIGN KEY(tx_id) REFERENCES evm_transactions(identifier) ON DELETE CASCADE
        );
        """)

    @progress_step(description='Adding eth2 validator cache table')
    def _add_eth2_staking_cache_table(write_cursor: 'DBCursor') -> None:
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS eth_validators_data_cache (
            id INTEGER NOT NULL PRIMARY KEY,
            validator_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,  -- timestamp is in milliseconds
            balance TEXT NOT NULL,
            withdrawals_pnl TEXT NOT NULL,
            exit_pnl TEXT NOT NULL,
            UNIQUE(validator_index, timestamp),
            FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501

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

    @progress_step(description='Adding validator_type column to eth2 validators table')
    def _add_validator_type_column(write_cursor: 'DBCursor') -> None:
        update_table_schema(
            write_cursor=write_cursor,
            table_name='eth2_validators',
            schema="""
                identifier INTEGER NOT NULL PRIMARY KEY,
                validator_index INTEGER UNIQUE,
                public_key TEXT NOT NULL UNIQUE,
                ownership_proportion TEXT NOT NULL,
                withdrawal_address TEXT,
                validator_type INTEGER NOT NULL CHECK (validator_type IN (0, 1, 2)),
                activation_timestamp INTEGER,
                withdrawable_timestamp INTEGER,
                exited_timestamp INTEGER
            """,
            insert_columns="""identifier, validator_index, public_key, ownership_proportion, withdrawal_address,
            CASE WHEN withdrawal_address IS NOT NULL THEN 1 ELSE 0 END as validator_type,
            activation_timestamp, withdrawable_timestamp, exited_timestamp
            """,  # noqa: E501
            insert_order='(identifier, validator_index, public_key, ownership_proportion, withdrawal_address, validator_type, activation_timestamp, withdrawable_timestamp, exited_timestamp)',  # noqa: E501
        )

    @progress_step(description='Updating calendar reminders schema')
    def _update_calendar_reminders_schema(write_cursor: 'DBCursor') -> None:
        """Upgrades the calendar_reminders table to include acknowledged column."""
        update_table_schema(
            write_cursor=write_cursor,
            table_name='calendar_reminders',
            schema="""
            identifier INTEGER PRIMARY KEY NOT NULL,
            event_id INTEGER NOT NULL,
            secs_before INTEGER NOT NULL,
            acknowledged INTEGER NOT NULL CHECK (acknowledged IN (0, 1)) DEFAULT 0,
            FOREIGN KEY(event_id) REFERENCES calendar(identifier) ON DELETE CASCADE
            """,
            insert_columns='identifier, event_id, secs_before, 0',
            insert_order='(identifier, event_id, secs_before, acknowledged)',
        )

    @progress_step(description='Converting trades to history events')
    def _convert_trades_to_swap_events(write_cursor: 'DBCursor') -> None:
        new_events: list[SwapEvent] = []
        # Kraken events appear both as history events and trades. We'll convert to SwapEvents
        # from the trades, but preserve the location_labels from the history events.
        write_cursor.execute(
            'SELECT DISTINCT event_identifier, location_label '
            'FROM history_events WHERE location=? AND type=?',
            (Location.KRAKEN.serialize_for_db(), HistoryEventType.TRADE.serialize()),
        )
        kraken_ids_to_labels = dict(write_cursor)  # Map event_identifiers (trade IDs) to location_labels.  # noqa: E501
        kraken_ids_to_delete = set(kraken_ids_to_labels)
        # Adjustments need special treatment, so save them in a different mapping with more info.
        write_cursor.execute(
            'SELECT DISTINCT event_identifier, location_label, amount, subtype '
            'FROM history_events WHERE location=? AND type=?',
            (Location.KRAKEN.serialize_for_db(), HistoryEventType.ADJUSTMENT.serialize()),
        )
        kraken_adjustments_data = {row[0]: (row[1], row[2], row[3]) for row in write_cursor}

        write_cursor.execute(
            'SELECT timestamp, location, base_asset, quote_asset, type, '
            'amount, rate, fee, fee_currency, link, notes FROM trades',
        )
        for row in write_cursor:
            try:
                new_events.extend(upgrade_trade_to_swap_events(
                    row=row,
                    kraken_ids_to_labels=kraken_ids_to_labels,
                    kraken_adjustments_data=kraken_adjustments_data,
                    kraken_ids_to_delete=kraken_ids_to_delete,
                ))
            except (DeserializationError, ValueError) as e:
                log.error(f'Failed to deserialize row {row} due to {e}. Skipping.')

        # Remove old Kraken history events that are no longer needed.
        placeholders = ','.join(['?'] * len(kraken_ids_to_delete))
        write_cursor.execute(
            f'DELETE FROM history_events WHERE location=? AND event_identifier IN ({placeholders})',  # noqa: E501
            (Location.KRAKEN.serialize_for_db(),) + tuple(kraken_ids_to_delete),
        )

        # Write the new swap events to the db and drop the old trade tables.
        # We hardcode the insert tuple instead of calling the serialization method to avoid
        # issues in the case of new fields being added or a change in the order.
        # Avoiding the call to the serialization function improved performance on databases
        # with many trades reducing the execution time by a considerable amount.
        write_cursor.executemany(
            'INSERT OR IGNORE INTO history_events(entry_type, event_identifier, '
            'sequence_index, timestamp, location, location_label, asset, amount, '
            'notes, type, subtype, extra_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            ((
                event.entry_type.value,
                event.event_identifier,
                event.sequence_index,
                event.timestamp,
                event.location.serialize_for_db(),
                event.location_label,
                event.asset.identifier,
                str(event.amount),
                event.notes,
                event.event_type.serialize(),
                event.event_subtype.serialize(),
                json.dumps(event.extra_data) if event.extra_data else None,
            ) for event in new_events),
        )
        write_cursor.execute('DROP TABLE trades')
        write_cursor.execute('DROP TABLE trade_type')
        write_cursor.execute('DELETE FROM used_query_ranges WHERE name LIKE "%_trades_%"')

    @progress_step(description='Replacing specific history note locations with HISTORY')
    def _replace_history_note_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            """
            UPDATE user_notes
            SET location = 'HISTORY'
            WHERE location IN (
                'HISTORY_TRADES',
                'HISTORY_TRANSACTIONS',
                'HISTORY_DEPOSITS_WITHDRAWALS'
            )
            """,
        )

    @progress_step(description='Migrating etherscan configuration')
    def _migrate_etherscan_keys(write_cursor: 'DBCursor') -> None:
        write_cursor.execute(
            'DELETE FROM external_service_credentials WHERE name IN (?, ?, ?, ?, ?, ?, ?)',
            (
                'optimism_etherscan',
                'polygon_pos_etherscan',
                'arbitrum_one_etherscan',
                'base_etherscan',
                'gnosis_etherscan',
                'scroll_etherscan',
                'binance_sc_etherscan',
            ),
        )
        write_cursor.execute(
            'DELETE FROM rpc_nodes WHERE name IN (?, ?, ?, ?, ?, ?, ?, ?)',
            (
                'etherscan',
                'optimism etherscan',
                'polygon pos etherscan',
                'arbitrum one etherscan',
                'base etherscan',
                'gnosis etherscan',
                'scroll etherscan',
                'bsc etherscan',
            ),
        )
        write_cursor.execute('DELETE FROM settings WHERE name=?', ('use_unified_etherscan_api',))

    @progress_step(description='Resetting asset movement notes')
    def _reset_asset_movement_notes(write_cursor: 'DBCursor') -> None:
        """Clears auto-generated asset movement notes.

        Auto-generated notes were previously stored for asset movements (entry_type=6).
        Now these are generated on the fly, so we remove them unless the event is customized.
        """
        write_cursor.execute(
            'UPDATE history_events SET notes = NULL WHERE entry_type = 6 AND notes IS NOT NULL '
            'AND NOT EXISTS (SELECT 1 FROM history_events_mappings WHERE parent_identifier = history_events.identifier AND name=? AND value=?)',  # noqa: E501
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        )

    @progress_step(description='Upgrade internal transactions table')
    def _upgrade_internal_transactions(write_cursor: 'DBCursor') -> None:
        """Update the internal transactions table

        Again we need to add more info in the internal transactions data due to examples like this:
        https://etherscan.io/tx/0xbded678de7cb58d7f0e4e8d1f0f5adeb1dd5097601a8ab5790558f8228a04c58#internal

        To differentiate between same from/to/value internals we just add gas and gas used there.
        This "should" reduce the chance of missing something to almost zero. There is no other data
        available for differentiation.
        """
        update_table_schema(
            write_cursor=write_cursor,
            table_name='evm_internal_transactions',
            schema="""
            parent_tx INTEGER NOT NULL,
            trace_id INTEGER NOT NULL,
            from_address TEXT NOT NULL,
            to_address TEXT,
            value TEXT NOT NULL,
            gas TEXT NOT NULL,
            gas_used TEXT NOT NULL,
            FOREIGN KEY(parent_tx) REFERENCES evm_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE,
            PRIMARY KEY(parent_tx, trace_id, from_address, to_address, value, gas, gas_used)
            """,  # noqa: E501
            insert_columns="parent_tx, trace_id, from_address, to_address, value, '0', '0'",
            insert_order='(parent_tx, trace_id, from_address, to_address, value, gas, gas_used)',
        )

    @progress_step(description='Upgrade history events table')
    def _upgrade_history_events(write_cursor: 'DBCursor') -> None:
        """Update the history events table, adding a new ignored column and populating it from
        the ignored asset values in multisettings.
        Also adds indexes to improve query speed when filtering events.
        """
        write_cursor.execute('ALTER TABLE history_events ADD COLUMN ignored INTEGER NOT NULL DEFAULT 0;')  # noqa: E501
        write_cursor.execute("""
            UPDATE history_events SET ignored = 1 FROM multisettings ms
            WHERE history_events.asset = ms.value AND ms.name = 'ignored_asset'
        """)
        write_cursor.execute('CREATE INDEX idx_history_events_entry_type ON history_events(entry_type);')  # noqa: E501
        write_cursor.execute('CREATE INDEX idx_history_events_timestamp ON history_events(timestamp);')  # noqa: E501
        write_cursor.execute('CREATE INDEX idx_history_events_location ON history_events(location);')  # noqa: E501
        write_cursor.execute('CREATE INDEX idx_history_events_location_label ON history_events(location_label);')  # noqa: E501
        write_cursor.execute('CREATE INDEX idx_history_events_asset ON history_events(asset);')
        write_cursor.execute('CREATE INDEX idx_history_events_type ON history_events(type);')
        write_cursor.execute('CREATE INDEX idx_history_events_subtype ON history_events(subtype);')
        write_cursor.execute('CREATE INDEX idx_history_events_ignored ON history_events(ignored);')

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
