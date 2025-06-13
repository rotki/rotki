import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.constants import ZERO
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    NO_ACCOUNTING_COUNTERPARTY,
)
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PREFIX = 'RE_%'  # hard-coded since this is a migration and prefix may change in the future
MIGRATION_PREFIX = 'MLA_'  # prefix to add to ledger actions migrated to history events id
# TO TYPE, TO SUBTYPE, FROM TYPE, FROM SUBTYPE
CHANGES: list[tuple[HistoryEventType, HistoryEventSubType, HistoryEventType, HistoryEventSubType]] = [  # noqa: E501
    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE, HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.DEPOSIT, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.RECEIVE, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.STAKING, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.RECEIVE, HistoryEventSubType.REWARD, HistoryEventType.RECEIVE, HistoryEventSubType.INTEREST_PAYMENT),  # noqa: E501
]
# TO TYPE, TO SUBTYPE, FROM TYPE, FROM SUBTYPE  # types remapped after consolidation
# for all the locations
TYPES_REMAPPED: list[tuple[HistoryEventType, HistoryEventSubType, HistoryEventType, HistoryEventSubType]] = [  # noqa: E501
    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, HistoryEventType.DEPOSIT, HistoryEventSubType.SPEND),  # noqa: E501
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, HistoryEventType.WITHDRAWAL, HistoryEventSubType.RECEIVE),  # noqa: E501
    (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, HistoryEventType.DEPOSIT, HistoryEventSubType.NONE),  # noqa: E501
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, HistoryEventType.WITHDRAWAL, HistoryEventSubType.NONE),  # noqa: E501
]

LEDGER_ACTION_TYPE_TO_NAME = {
    'A': 'income',
    'B': 'expense',
    'C': 'loss',
    'D': 'dividends income',
    'E': 'donation received',
    'F': 'airdrop',
    'G': 'gift',
    'H': 'grant',
}


@enter_exit_debug_log(name='UserDB v39->v40 upgrade')
def upgrade_v39_to_v40(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v39 to v40. This was in v1.31.0 release.

        - Migrate rotki events that were broken due to https://github.com/rotki/rotki/issues/6550
        - Purge kraken events
        - Create new tables
        - Replace VELO asset in favor of the binance chain version
    """
    @progress_step(description='Adding new tables.')
    def _add_new_tables(write_cursor: 'DBCursor') -> None:
        """
        Add new tables for this upgrade
        """
        write_cursor.execute("""CREATE TABLE IF NOT EXISTS skipped_external_events (
        identifier INTEGER NOT NULL PRIMARY KEY,
        data TEXT NOT NULL,
        location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        extra_data TEXT,
        UNIQUE(data, location)
        );""")
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounting_rules(
            identifier INTEGER NOT NULL PRIMARY KEY,
            type TEXT NOT NULL,
            subtype TEXT NOT NULL,
            counterparty TEXT NOT NULL,
            taxable INTEGER NOT NULL CHECK (taxable IN (0, 1)),
            count_entire_amount_spend INTEGER NOT NULL CHECK (count_entire_amount_spend IN (0, 1)),
            count_cost_basis_pnl INTEGER NOT NULL CHECK (count_cost_basis_pnl IN (0, 1)),
            accounting_treatment TEXT,
            UNIQUE(type, subtype, counterparty)
        );
        """)
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS linked_rules_properties(
            identifier INTEGER PRIMARY KEY NOT NULL,
            accounting_rule INTEGER REFERENCES accounting_rules(identifier),
            property_name TEXT NOT NULL,
            setting_name TEXT NOT NULL references settings(name)
        );
        """)
        write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS unresolved_remote_conflicts(
            identifier INTEGER PRIMARY KEY NOT NULL,
            local_id INTEGER NOT NULL,
            remote_data TEXT NOT NULL,
            type INTEGER NOT NULL
        );
        """)

    @progress_step(description='Migrating rotki events.')
    def _migrate_rotki_events(write_cursor: 'DBCursor') -> None:
        """
        Migrate rotki events that were broken due to https://github.com/rotki/rotki/issues/6550.
        and events that need to update their types after the consolidation made in 1.31
        """
        write_cursor.executemany(  # update types by event identifier
            'UPDATE history_events SET type=?, subtype=? WHERE '
            'event_identifier LIKE ? AND type=? AND subtype=?',
            [(
                to_type.serialize(), to_subtype.serialize(), PREFIX,
                from_type.serialize(), from_subtype.serialize(),
            ) for to_type, to_subtype, from_type, from_subtype in CHANGES],
        )
        write_cursor.executemany(  # update types for all the locations
            'UPDATE history_events SET type=?, subtype=? WHERE type=? AND subtype=?',
            [(
                to_type.serialize(), to_subtype.serialize(),
                from_type.serialize(), from_subtype.serialize(),
            ) for to_type, to_subtype, from_type, from_subtype in TYPES_REMAPPED],
        )
        write_cursor.execute('DELETE from used_query_ranges WHERE name=?', ('last_withdrawals_query_ts',))  # noqa: E501

    @progress_step(description='Purging Kraken events.')
    def _purge_kraken_events(write_cursor: 'DBCursor') -> None:
        """
        Purge kraken events, after the changes that allows for processing of new assets.
        We may have had missed events so now let's repull. And since we will also
        get https://github.com/rotki/rotki/issues/6582 this resetting should not need to
        happen in the future.

        This just mimics DBHandler::purge_exchange_data
        """
        write_cursor.execute(
            'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
            (f'{Location.KRAKEN!s}\\_%', '\\'),
        )
        location = Location.KRAKEN.serialize_for_db()
        for table in ('trades', 'asset_movements', 'history_events'):
            write_cursor.execute(f'DELETE FROM {table} WHERE location = ?;', (location,))

    @progress_step(description='Adding new supported chains locations.')
    def _add_new_supported_chains_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO location(location, seq) '
            'VALUES (?, ?)',
            (('j', 42), ('k', 43), ('l', 44)),
        )

    @progress_step(description='Upgrading rotki events.')
    def _upgrade_rotki_events(write_cursor: 'DBCursor') -> None:
        """Upgrade the rotki events schema table to specify location as a type"""
        write_cursor.executescript('PRAGMA foreign_keys = OFF;')
        update_table_schema(
            write_cursor=write_cursor,
            table_name='history_events',
            schema="""identifier INTEGER NOT NULL PRIMARY KEY,
            entry_type INTEGER NOT NULL,
            event_identifier TEXT NOT NULL,
            sequence_index INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
            location_label TEXT,
            asset TEXT NOT NULL,
            amount TEXT NOT NULL,
            usd_value TEXT NOT NULL,
            notes TEXT,
            type TEXT NOT NULL,
            subtype TEXT NOT NULL,
            FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
            UNIQUE(event_identifier, sequence_index)""",
        )
        write_cursor.executescript('PRAGMA foreign_keys = ON;')

    @progress_step(description='Migrating ledger airdop accounting setting.')
    def _migrate_ledger_airdrop_accounting_setting(write_cursor: 'DBCursor') -> None:
        """
        Migrates the accounting setting for airdrops to the new table for accounting
        rules. It requires the existence of the accounting_rules table and the existence of
        `taxable_ledger_actions` on the settings table.
        """
        # copy the taxable ledger actions rules
        new_accounting_rule = None
        write_cursor.execute('SELECT value FROM settings WHERE name=?', ('taxable_ledger_actions',))  # noqa: E501
        if (taxable_ledgers_row := write_cursor.fetchone()) is not None:
            try:
                taxable_ledger_events = json.loads(taxable_ledgers_row[0])
            except json.JSONDecodeError as e:
                log.error(f'Failed to decode ledger action taxable rules {e}')
            else:
                if 'airdrop' in taxable_ledger_events:
                    new_accounting_rule = (
                        HistoryEventType.RECEIVE.serialize(),
                        HistoryEventSubType.AIRDROP.serialize(),
                        NO_ACCOUNTING_COUNTERPARTY,
                        True,  # taxable
                        False,
                        False,
                        None,
                    )
        if new_accounting_rule is None:
            return

        write_cursor.execute(
            'INSERT INTO accounting_rules(type, subtype, counterparty, taxable, '
            'count_entire_amount_spend, count_cost_basis_pnl, '
            'accounting_treatment) VALUES (?, ?, ?, ?, ?, ?, ?)',
            new_accounting_rule,
        )

    @progress_step(description='Migrating ledger actions.')
    def _migrate_ledger_actions(write_cursor: 'DBCursor') -> None:
        """
        Migrate all ledger actions to history events, so that we can get rid of the
        deprecated ledger action structure.

        Then remove all no longer needed DB data

        Part of https://github.com/rotki/rotki/issues/6096. Requires the new tables to be
        already created.
        """
        history_events = []
        with db.conn.read_ctx() as cursor:
            cursor.execute('SELECT timestamp, type, location, amount, asset, rate, rate_asset, link, notes FROM ledger_actions')  # noqa: E501
            for entry in cursor:
                location = entry[2]
                try:
                    val = ord(location)  # can raise TypeError
                    if val < 65 or val > 106:  # not between A and j
                        raise TypeError
                except TypeError:
                    log.error(f'Skipped a ledger action from migration to history event due to invalid location {location}')  # noqa: E501
                    continue

                usd_value = ZERO  # try to use a rate asset if given only if it's against USD. Unfortunately this means we can lose data here but there is no way to translate this to a single history event  # noqa: E501
                if entry[5] is not None and entry[6] is not None and entry[6] == 'USD':
                    try:
                        amount = deserialize_fval(entry[3], 'amount', 'ledger actions migration')
                        rate = deserialize_fval(entry[5], 'rate', 'ledger actions migration')
                    except DeserializationError as e:
                        log.error(f'Skipped a ledger action from migration to history event due {e}')  # noqa: E501
                        continue

                    usd_value = amount * rate

                ledger_action_type = entry[1]
                notes = f'Migrated from a ledger action of {LEDGER_ACTION_TYPE_TO_NAME[ledger_action_type]} type'  # due to DB consistency there should be no key errors # noqa: E501
                if entry[8] is not None:
                    notes = f'{entry[8]}. {notes}'
                if entry[7] is not None:
                    notes = f'{notes}. {entry[7]}'

                # map the types. Making sure to have the as default/valid combinations
                if ledger_action_type in {'A', 'D', 'G', 'H'}:  # income, dividends income, gift, grant action type  # noqa: E501
                    event_type = 'receive'
                    event_subtype = 'none'
                elif ledger_action_type in {'B', 'C'}:  # expense, loss action type
                    event_type = 'spend'
                    event_subtype = 'none'
                elif ledger_action_type == 'E':
                    event_type = 'receive'
                    event_subtype = 'donate'
                elif ledger_action_type == 'F':
                    event_type = 'receive'
                    event_subtype = 'airdrop'
                else:
                    log.error(f'Corrupt ledger action type. Skipping entry during upgrade: {entry}')  # noqa: E501
                    continue

                history_events.append((
                    1,  # entry_type -> HISTORY_EVENT
                    f'{MIGRATION_PREFIX}{uuid4().hex}',  # event_identifier
                    0,  # sequence_index
                    entry[0] * 1000,  # timestamp
                    location,
                    None,  # location_label
                    entry[4],  # asset
                    entry[3],  # amount
                    str(usd_value),  # usd_value
                    notes,
                    event_type,
                    event_subtype,
                ))

        write_cursor.executemany("""INSERT OR IGNORE INTO history_events(
        entry_type,
        event_identifier,
        sequence_index,
        timestamp,
        location,
        location_label,
        asset,
        amount,
        usd_value,
        notes,
        type,
        subtype) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", history_events)
        write_cursor.execute('DROP TABLE IF EXISTS ledger_actions;')
        write_cursor.execute('DROP TABLE IF EXISTS ledger_action_type;')
        write_cursor.execute('DELETE from settings WHERE name=?', ('taxable_ledger_actions',))

        with db.conn.read_ctx() as cursor:  # migrate coinbase ledger action query ranges
            cursor.execute('SELECT name FROM used_query_ranges WHERE name LIKE ? ESCAPE ?', ('%\\_ledger\\_actions\\_%', '\\'))  # noqa: E501
            for entry in cursor:
                try:
                    write_cursor.execute(
                        'UPDATE used_query_ranges SET name = ? WHERE name = ?',
                        (entry[0].replace('_ledger_actions_', '_history_events_'), entry[0]),
                    )
                except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                    log.error(f'Failed to update used query range {entry[0]} due to {e}')
                    continue

        # Clean up any ignored ledger actions # THINK: Migrate the ignoring if action exists and is migrated to history event or let user do it again? Probably let's keep it simple  # noqa: E501
        write_cursor.execute('DELETE FROM ignored_actions WHERE type=?', ('D',))
        write_cursor.execute('DELETE FROM action_type WHERE type=?', ('D',))

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """
        Reset all decoded evm events except the customized ones for ethereum mainnet,
        arbitrum, optimism and polygon.
        """
        if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] == 0:
            return

        customized_events = write_cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        ).fetchone()[0]
        querystr = (
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT H.identifier from history_events H INNER JOIN evm_events_info E '
            'ON H.identifier=E.identifier AND E.tx_hash IN '
            '(SELECT tx_hash FROM evm_transactions))'
        )
        bindings: tuple = ()
        if customized_events != 0:
            querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

        write_cursor.execute(querystr, bindings)
        write_cursor.execute(
            'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
            (0,),  # decoded state
        )

    @progress_step(description='Replacing velo identifier.')
    def _replace_velo_identifier(write_cursor: 'DBCursor') -> None:
        """
        Replace VELO with the binance version of the token. This is done as part of a consolidation
        process where we added VELO V1 and VELO V2 from Velodrome but our database also contained a
        VELO asset and a BNB version of it both not related to velodrome. As part of upgrade to V6
        of the global DB we are replacing this VELO asset (not token) with its BNB version.

        Code taken from replace_asset_identifier
        """
        target_asset_identifier = 'eip155:56/erc20:0xf486ad071f3bEE968384D2E39e2D8aF0fCf6fd46'
        source_identifier = 'VELO'

        write_cursor.executescript('PRAGMA foreign_keys = OFF;')
        write_cursor.execute(
            'DELETE from assets WHERE identifier=?;',
            (target_asset_identifier,),
        )
        write_cursor.executescript('PRAGMA foreign_keys = ON;')
        write_cursor.execute(
            'UPDATE assets SET identifier=? WHERE identifier=?;',
            (target_asset_identifier, source_identifier),
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
