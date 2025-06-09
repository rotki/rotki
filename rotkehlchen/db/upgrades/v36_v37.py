import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import EVM_LOCATIONS, Location, deserialize_evm_tx_hash
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
    """
    Reset all decoded events except the customized ones.
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
        'DELETE from evm_tx_mappings WHERE tx_hash=? AND value=?',
        [(tx_hash, 0) for tx_hash in tx_hashes],  # 0 -> decoded state
    )


@enter_exit_debug_log(name='UserDB v36->v37 upgrade')
def upgrade_v36_to_v37(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v36 to v37. This was in v1.28.0 release.

        - Replace null history event subtype
    """
    @progress_step(description='Moving event locations.')
    def _move_event_locations(write_cursor: 'DBCursor') -> None:
        """
        Create location ethereum and optimism and move the blockchain events to those locations

        This used to be DB data migration 9 which was added only for when upgrading from 1.27.0 to
        1.27.1. So it only exists in 1.27.1 and has from now on (1.28.0) moved to this DB upgrade

        This should always be at the start of this DB upgrade as it relies on the old schema.
        """
        write_cursor.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('f', 38);")
        write_cursor.execute("INSERT OR IGNORE INTO location(location, seq) VALUES ('g', 39);")

        write_cursor.execute(
            'SELECT chain_id, tx_hash FROM evm_transactions WHERE '
            'tx_hash IN (SELECT event_identifier FROM history_events)',
        )
        update_tuples = []
        for chain_id, tx_hash in write_cursor:
            if chain_id == 1:
                location = 'f'  # ethereum
            elif chain_id == 10:
                location = 'g'  # optimism
            else:  # unexpected -- skip entry from editing
                log.error(f'Found unexpected chain id {chain_id} in the DB for transaction {tx_hash}')  # noqa: E501
                continue

            update_tuples.append((location, tx_hash))

        write_cursor.executemany(
            'UPDATE history_events SET location=? WHERE event_identifier=?', update_tuples,
        )
        write_cursor.execute("DELETE FROM history_events_mappings WHERE name='chain_id'")

    @progress_step(description='Creating new tables.')
    def _create_new_tables(write_cursor: 'DBCursor') -> None:
        """Create new tables

        Data is not migrated to the evm_events_info as it will be done when redecoding.
        Still left to do: delete all data except customized events and figure out what to do
        with the custom events.
        """
        write_cursor.execute("""
            CREATE TABLE IF NOT EXISTS evm_events_info(
                identifier INTEGER PRIMARY KEY,
                tx_hash BLOB NOT NULL,
                counterparty TEXT,
                product TEXT,
                address TEXT,
                extra_data TEXT,
                FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
            );
        """)  # noqa: E501
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS eth_staking_events_info(
            identifier INTEGER PRIMARY KEY,
            validator_index INTEGER NOT NULL,
            is_exit_or_blocknumber INTEGER NOT NULL,
            FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
        """)  # noqa: E501

    @progress_step(description='Updating history events schema.')
    def _update_history_events_schema(write_cursor: 'DBCursor') -> None:
        """
        1. Reset all decoded events
        2. Rewrite the DB schema of the history events to have subtype as non Optional
        3. Delete counterparty and extra_data fields
        4. Add `entry_type` column that helps determine types of events.
        5. Turn event_identifier to a string

        Also turn all null subtype entries to have subtype none
        """
        _reset_decoded_events(write_cursor)
        write_cursor.execute("""CREATE TABLE IF NOT EXISTS history_events_copy (
        identifier INTEGER NOT NULL PRIMARY KEY,
        entry_type INTEGER NOT NULL,
        event_identifier TEXT NOT NULL,
        sequence_index INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        location TEXT NOT NULL,
        location_label TEXT,
        asset TEXT NOT NULL,
        amount TEXT NOT NULL,
        usd_value TEXT NOT NULL,
        notes TEXT,
        type TEXT NOT NULL,
        subtype TEXT NOT NULL,
        FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
        UNIQUE(event_identifier, sequence_index)
        );""")
        new_entries = []
        extra_evm_info_entries = []
        with db.conn.read_ctx() as read_cursor:
            read_cursor.execute('SELECT * from history_events')
            for entry in read_cursor:
                location = Location.deserialize_from_db(entry[4])
                db_event_identifier = entry[1]
                if location in EVM_LOCATIONS:
                    event_identifier = f'{location.to_chain_id()}{deserialize_evm_tx_hash(db_event_identifier).hex()}'  # noqa: E501 # pylint: disable=no-member
                elif location == Location.KRAKEN or db_event_identifier.startswith(b'rotki_events'):  # noqa: E501
                    # kraken is the only location with basic history event entry type that doesn't
                    # start with 'rotki_events'
                    event_identifier = db_event_identifier.decode()
                else:
                    # this shouldn't happen, leaving it here to avoid failing during the upgrade
                    # _move_event_locations should have moved already all the events that
                    #  are related to evm transactions with the wrong location
                    log.critical(f'Unexpected event {entry=} found. Skipping')
                    continue

                if location == Location.KRAKEN or event_identifier.startswith('rotki_events'):  # This is the rule at 1.27.1   # noqa: E501
                    entry_type = HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db()
                else:
                    entry_type = HistoryBaseEntryType.EVM_EVENT.serialize_for_db()
                    extra_evm_info_entries.append((entry[0], entry[1]) + entry[12:])

                if entry[11] is None:
                    new_entries.append([entry[0], entry_type, event_identifier, *entry[2:11], 'none'])  # turn NULL values to text `none`  # noqa: E501
                else:
                    new_entries.append([entry[0], entry_type, event_identifier, *entry[2:12]])  # Don't change NON-NULL values  # noqa: E501

        # add all non-evm entries to the new table (no data lost)
        write_cursor.executemany('INSERT INTO history_events_copy VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', new_entries)  # noqa: E501
        for entry in extra_evm_info_entries:
            write_cursor.execute(
                'INSERT INTO evm_events_info VALUES(?, ?, ?, ?, ?, ?)',
                (entry[0], entry[1], entry[2], None, None, entry[3]),
            )

        write_cursor.switch_foreign_keys('OFF')  # need FK off or history_events_mappings get deleted  # noqa: E501
        write_cursor.execute('DROP TABLE history_events')
        write_cursor.execute('ALTER TABLE history_events_copy RENAME TO history_events')
        write_cursor.switch_foreign_keys('ON')

    @progress_step(description='Updating ens mappings schema.')
    def _update_ens_mappings_schema(write_cursor: 'DBCursor') -> None:
        update_table_schema(
            write_cursor=write_cursor,
            table_name='ens_mappings',
            schema="""address TEXT NOT NULL PRIMARY KEY,
            ens_name TEXT UNIQUE,
            last_update INTEGER NOT NULL,
            last_avatar_update INTEGER NOT NULL DEFAULT 0""",
            insert_columns='address, ens_name, last_update',
            insert_order='(address, ens_name, last_update)',
        )

    @progress_step(description='Deleting old tables.')
    def _delete_old_tables(write_cursor: 'DBCursor') -> None:
        """Deletes old tables that are now unused along with related data
        """
        write_cursor.execute('DROP TABLE IF EXISTS eth2_deposits')
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ?',
            ('eth2_deposits%',),
        )

    @progress_step(description='Fixing Kraken events.')
    def _fix_kraken_events(write_cursor: 'DBCursor') -> None:
        """
        Fix kraken events with negative amounts related to:
        - staking ETH after the merge
        - trades not having subtypes and having negative amounts
        - withdrawals use positive amounts
        - instant swaps
        Needs to be executed after _update_history_events_schema
        """
        write_cursor.execute(
            "SELECT identifier, amount, usd_value FROM history_events WHERE location='B' AND "
            "asset=? AND type='staking' AND subtype='reward' AND CAST(amount AS REAL) < 0",
            (A_ETH2.identifier,),
        )
        update_tuples: list[Any] = [(
            HistoryEventType.INFORMATIONAL.serialize(),
            HistoryEventSubType.NONE.serialize(),
            str(-FVal(event_row[1])),
            str(-FVal(event_row[2])),
            'Automatic virtual conversion of staked ETH rewards to ETH',
            event_row[0],
        ) for event_row in write_cursor]
        if len(update_tuples) != 0:
            write_cursor.executemany(
                'UPDATE history_events SET type=?, subtype=?, amount=?, usd_value=?, notes=? WHERE identifier=?',  # noqa: E501
                update_tuples,
            )

        log.debug('Fixing kraken trades')
        write_cursor.execute(
            "SELECT identifier, amount, usd_value FROM history_events WHERE location='B' AND "
            "type='trade' AND subtype='none'",
        )

        trade_db_type = HistoryEventType.TRADE.serialize()
        update_tuples = []
        for event_row in write_cursor:
            asset_amount = FVal(event_row[1])
            usd_value = FVal(event_row[2])
            if asset_amount < ZERO:
                event_subtype = HistoryEventSubType.SPEND
                asset_amount = -asset_amount
                usd_value = -usd_value
            else:
                event_subtype = HistoryEventSubType.RECEIVE

            update_tuples.append(
                (
                    trade_db_type,
                    event_subtype.serialize(),
                    str(asset_amount),
                    str(usd_value),
                    event_row[0],
                ),
            )

        if len(update_tuples) != 0:
            write_cursor.executemany(
                'UPDATE history_events SET type=?, subtype=?, amount=?, usd_value=? WHERE identifier=?',  # noqa: E501
                update_tuples,
            )

        log.debug('Fixing kraken withdrawals')  # deposits are all positive amount already
        write_cursor.execute(
            "SELECT identifier, amount, usd_value FROM history_events WHERE location='B' AND "
            "type='withdrawal'",
        )
        update_tuples = [(
            str(-FVal(event_row[1])),
            str(-FVal(event_row[2])),
            event_row[0],
        ) for event_row in write_cursor]
        if len(update_tuples) != 0:
            write_cursor.executemany(
                'UPDATE history_events SET amount=?, usd_value=? WHERE identifier=?',
                update_tuples,
            )

        log.debug('Fixing kraken instant swaps')
        update_tuples = []
        grouped_events: dict[str, list[Any]] = defaultdict(list)
        write_cursor.execute(
            "SELECT identifier, event_identifier, type, amount, usd_value FROM history_events "
            "WHERE location='B' AND type IN ('spend', 'receive') AND subtype='none'",
        )
        for row in write_cursor:
            grouped_events[row[1]].append(row)

        for events in grouped_events.values():
            if len(events) != 2:
                # we are looking for instant swaps that are always pairs of spend/receive
                # with the same event identifier
                continue

            for event in events:
                if event[2] == 'spend':
                    event_subtype = HistoryEventSubType.SPEND
                    asset_amount = FVal(event[3])
                    asset_amount_str = str(-asset_amount) if asset_amount != ZERO else str(asset_amount)  # noqa: E501
                    usd_value_str = str(-FVal(event[4]))
                else:
                    event_subtype = HistoryEventSubType.RECEIVE
                    asset_amount_str = event[3]
                    usd_value_str = event[4]

                update_tuples.append(
                    (
                        trade_db_type,
                        event_subtype.serialize(),
                        asset_amount_str,
                        usd_value_str,
                        event[0],
                    ),
                )
        if len(update_tuples) != 0:
            write_cursor.executemany(
                'UPDATE history_events SET type=?, subtype=?, amount=?, usd_value=? WHERE identifier=?',  # noqa: E501
                update_tuples,
            )

    @progress_step(description='Trimming daily stats.')
    def _trim_daily_stats(write_cursor: 'DBCursor') -> None:
        """Decreases the amount of data in the daily stats table"""
        update_table_schema(
            write_cursor=write_cursor,
            table_name='eth2_daily_staking_details',
            schema="""validator_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            pnl TEXT NOT NULL,
            FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
            PRIMARY KEY (validator_index, timestamp)""",  # noqa: E501
            insert_columns='validator_index, timestamp, pnl',
            insert_where='start_amount != 0 OR end_amount !=0 OR amount_deposited != 0',
        )

    @progress_step(description='Removing FTX data.')
    def _remove_ftx_data(write_cursor: 'DBCursor') -> None:
        """Removes FTX-related settings from the DB"""
        write_cursor.execute(
            'DELETE FROM user_credentials WHERE location IN (?, ?)',
            (Location.FTX.serialize_for_db(), Location.FTXUS.serialize_for_db()),
        )
        write_cursor.execute(
            'DELETE FROM user_credentials_mappings WHERE credential_location IN (?, ?)',
            (Location.FTX.serialize_for_db(), Location.FTXUS.serialize_for_db()),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{Location.FTX!s}\\_%', '\\'),
        )
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{Location.FTXUS!s}\\_%', '\\'),
        )
        non_syncing_exchanges_in_db = write_cursor.execute(
            "SELECT value FROM settings WHERE name='non_syncing_exchanges'",
        ).fetchone()
        if non_syncing_exchanges_in_db is not None:
            non_syncing_exchanges = json.loads(non_syncing_exchanges_in_db[0])
            new_values = [x for x in non_syncing_exchanges if x['location'] not in (Location.FTX.serialize(), Location.FTXUS.serialize())]  # noqa: E501
            write_cursor.execute(
                "UPDATE settings SET value=? WHERE name='non_syncing_exchanges'",
                (json.dumps(new_values),),
            )

    @progress_step(description='Adjusting user settings.')
    def _adjust_user_settings(write_cursor: 'DBCursor') -> None:
        """Adjust user settings, renaming a key that misbehaves in frontend transformation"""
        write_cursor.execute(
            "UPDATE settings SET name='ssf_graph_multiplier' WHERE name='ssf_0graph_multiplier'")

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
