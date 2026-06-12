"""ProfileBuilder: creates a bootable rotki data directory for one profile.

All raw-SQL writes of the generator funnel through this module (design §3.2)
so that schema changes have a single maintenance touchpoint. Event rows are
serialized by the real event structures' ``serialize_for_db()`` — the bulk
writer only batches them with explicitly assigned identifiers for speed.
"""
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.constants.misc import DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.balances.manual import ManuallyTrackedBalance
    from rotkehlchen.chain.accounts import BlockchainAccountData
    from rotkehlchen.db.settings import ModifiableDBSettings
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

# Matches testEnv.PASSWORD in frontend/app/tests/e2e/fixtures/index.ts
USER_PASSWORD: Final = '1234'
EVENTS_CHUNK_SIZE: Final = 50_000


class ProfileBuilder:
    """Builds one profile user inside a fresh data directory.

    The output directory becomes a complete rotki data dir: the global DB is
    initialized from the packaged one (no network: no asset updates are
    performed) and the user DB is created at the current schema version
    through the regular DBHandler.
    """

    def __init__(self, name: str, output_dir: Path) -> None:
        self.name = name
        self.output_dir = output_dir
        self.user_dir = output_dir / 'users' / name
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.msg_aggregator = MessagesAggregator()
        GlobalDBHandler(  # globaldb must be initialized before DBHandler
            data_dir=output_dir,
            perform_assets_updates=False,  # never hit the network during builds
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
            msg_aggregator=self.msg_aggregator,
        )
        self.db = DBHandler(
            user_data_dir=self.user_dir,
            password=USER_PASSWORD,
            msg_aggregator=self.msg_aggregator,
            initial_settings=None,
            sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
            resume_from_backup=False,
        )
        self._next_event_identifier = 1
        self.stats: dict[str, Any] = {
            'total_events': 0,
            'event_groups': 0,
            'events_per_location': {},
            'events_per_entry_type': {},
        }
        self._seen_groups: set[str] = set()

    def add_accounts(self, accounts: list['BlockchainAccountData']) -> None:
        with self.db.user_write() as write_cursor:
            self.db.add_blockchain_accounts(write_cursor, accounts)

    def set_settings(self, settings: 'ModifiableDBSettings') -> None:
        with self.db.user_write() as write_cursor:
            self.db.set_settings(write_cursor, settings)

    def add_manual_balances(self, balances: list['ManuallyTrackedBalance']) -> None:
        with self.db.user_write() as write_cursor:
            self.db.add_manually_tracked_balances(write_cursor, balances)
        self.stats.setdefault('manual_balances', []).extend(
            {
                'amount': str(balance.amount),
                'asset': balance.asset.identifier,
                'label': balance.label,
                'location': balance.location.serialize(),
            }
            for balance in balances
        )

    def add_chain_state(self, state: dict[str, Any], expected: dict[str, Any]) -> None:
        """Write the mock rpc layer's on-chain state (raw base-unit balances)
        at the profile root and record the human-readable amounts in
        expected.json (see common.make_chain_state)."""
        (self.output_dir / 'chain_state.json').write_text(
            json.dumps(state, indent=2, sort_keys=True),
            encoding='utf8',
        )
        self.stats['blockchain_balances'] = expected

    def add_manual_latest_prices(self, prices: Sequence[tuple['Asset', str]]) -> None:
        """Seed manual latest prices (vs USD) into the global DB so balance
        valuations resolve locally instead of querying remote oracles."""
        from rotkehlchen.constants.assets import A_USD  # heavy import kept local
        from rotkehlchen.fval import FVal
        from rotkehlchen.types import Price

        for asset, usd_price in prices:
            GlobalDBHandler.add_manual_latest_price(
                from_asset=asset,
                to_asset=A_USD,
                price=Price(FVal(usd_price)),
            )

    def add_balance_snapshots(
            self,
            balance_rows: Sequence[tuple],
            location_rows: Sequence[tuple],
            snapshot_count: int,
    ) -> None:
        """Bulk-insert historical balance snapshots (timed_balances and
        timed_location_data rows, as produced by profiles.common.make_snapshots)"""
        with self.db.user_write() as write_cursor:
            write_cursor.executemany(
                'INSERT INTO timed_balances(category, timestamp, currency, amount, usd_value) '
                'VALUES (?, ?, ?, ?, ?)',
                balance_rows,
            )
            write_cursor.executemany(
                'INSERT INTO timed_location_data(timestamp, location, usd_value) '
                'VALUES (?, ?, ?)',
                location_rows,
            )
        self.stats['snapshots'] = snapshot_count

    def ignore_assets(self, identifiers: Sequence[str]) -> None:
        with self.db.user_write() as write_cursor:
            write_cursor.executemany(
                "INSERT OR IGNORE INTO multisettings(name, value) VALUES('ignored_asset', ?)",
                [(identifier,) for identifier in identifiers],
            )

    def filter_existing_assets(self, identifiers: Sequence[str]) -> list[str]:
        """Keep only asset identifiers present in the packaged global DB,
        preserving input order (deterministic given the global DB, which is
        part of the cache key). Warns about dropped ones so a shrinking pool
        is visible instead of silent."""
        with GlobalDBHandler().conn.read_ctx() as cursor:
            existing = {row[0] for row in cursor.execute(
                f'SELECT identifier FROM assets WHERE identifier IN '
                f'({",".join("?" * len(identifiers))})',
                tuple(identifiers),
            )}
        if len(missing := [x for x in identifiers if x not in existing]) != 0:
            print(f'WARNING: dropping assets missing from global DB: {missing}', file=sys.stderr)
        return [x for x in identifiers if x in existing]

    def add_history_events(self, events: Iterable['HistoryBaseEntry']) -> None:
        """Bulk-insert history events with explicitly assigned identifiers.

        Identifiers are assigned from a running counter (the tables are fresh,
        so rowids are ours to choose), which lets secondary-table rows
        (e.g. chain_events_info) reference them without per-row lastrowid
        round-trips. The insert statements come from the events' own
        serialize_for_db() so column knowledge stays in the structures.
        """
        base_query: str | None = None
        base_rows: list[tuple] = []
        secondary_rows: dict[str, list[tuple]] = {}

        def flush() -> None:
            if base_query is None or len(base_rows) == 0:
                return
            with self.db.user_write() as write_cursor:
                write_cursor.executemany(f'INSERT INTO {base_query}', base_rows)
                for table_query, rows in secondary_rows.items():
                    write_cursor.executemany(f'INSERT INTO {table_query}', rows)
            base_rows.clear()
            secondary_rows.clear()

        for event in events:
            serialized = event.serialize_for_db()
            insert_query, _, bindings = serialized[0]
            bulk_query = insert_query.replace(
                'history_events(', 'history_events(identifier, ', 1,
            ).replace('VALUES (?,', 'VALUES (?, ?,', 1)
            if base_query is None:
                base_query = bulk_query
            elif bulk_query != base_query:  # all entry types share the base-table statement
                raise AssertionError(f'unexpected history_events insert: {insert_query}')

            base_rows.append((self._next_event_identifier, *bindings))
            for table_query, _, table_bindings in serialized[1:]:
                secondary_rows.setdefault(table_query, []).append(
                    (self._next_event_identifier, *table_bindings),
                )
            self._next_event_identifier += 1

            self.stats['total_events'] += 1
            for key, value in (
                    ('events_per_location', str(event.location)),
                    ('events_per_entry_type', str(event.entry_type)),
            ):
                self.stats[key][value] = self.stats[key].get(value, 0) + 1
            if event.group_identifier not in self._seen_groups:
                self._seen_groups.add(event.group_identifier)
                self.stats['event_groups'] += 1

            if len(base_rows) >= EVENTS_CHUNK_SIZE:
                flush()

        flush()

    def finalize(self, expected_extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Apply post-insert bookkeeping, write expected.json and close the
        user DB. Returns the expected-values dict."""
        with self.db.user_write() as write_cursor:
            # the bulk writer skips the per-event ignored computation; do it once
            write_cursor.execute(
                'UPDATE history_events SET ignored=1 WHERE asset IN '
                "(SELECT value FROM multisettings WHERE name='ignored_asset')",
            )
        expected = self.stats | (expected_extra or {})
        (self.user_dir / 'expected.json').write_text(
            json.dumps(expected, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        self.db.conn_transient.close()  # checkpoint both DBs' WALs before caching
        self.db.conn.close()
        return expected
