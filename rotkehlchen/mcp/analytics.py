from __future__ import annotations

import hmac
import json
import re
import secrets
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Final

import polars as pl

from rotkehlchen.mcp.backend import (
    BackendQueryError,
    get_backend_config,
    query_all_balances,
    query_history_events_page,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.mcp.constants import PrivacyMode

PAGE_SIZE: Final = 1000
DEFAULT_MAX_RESULT_ROWS: Final = 500
MAX_RESULT_ROWS: Final = 5_000
REDACTED_TEXT: Final = '[redacted]'
DEFAULT_TABLES: Final = ('history_events',)
AVAILABLE_TABLES: Final = ('history_events', 'balances')
# Any real unix-seconds timestamp is well below this (1e11 s ~= year 5138), while a
# millisecond timestamp is ~1.7e12. Used to accept either unit for the time-range filter:
# the event ``timestamp`` column is in ms, so an LLM naturally passes ms here too.
MS_THRESHOLD: Final = 10**11

# --- privacy classification -------------------------------------------------------------
# Free-text columns: never emitted verbatim outside ``raw`` mode (only a ``has_<col>``
# flag). ``auto_notes`` is rotki's decoded description and routinely embeds addresses, so
# it is treated as free text rather than a safe value.
TEXT_COLUMN_NAMES: Final = frozenset({'notes', 'user_notes', 'auto_notes'})
# Identifier columns that are always personally identifying: hashed (never raw) outside
# ``raw`` mode. ``location_label`` is special-cased in ``balanced`` (see _sanitize_identifier).
PII_COLUMN_NAMES: Final = frozenset({
    'account',
    'address',
    'group_identifier',
    'event_identifier',
    'location_label',
    'tx_hash',
})
# In ``strict`` mode, user-authored labels and names are treated as identifiers too.
STRICT_IDENTIFIER_COLUMN_NAMES: Final = PII_COLUMN_NAMES | frozenset({'label', 'name', 'tag'})
# The ONLY columns allowed through verbatim outside ``raw`` mode. This is the core of the
# fail-closed design: anything whose base name is not here, and that is not handled by the
# text/identifier paths above, is hashed (if a string) rather than leaked. Adding a new
# nested field upstream therefore defaults to "hidden", not "exposed".
SAFE_PASSTHROUGH_COLUMN_NAMES: Final = frozenset({
    'amount',
    'asset',
    'balance',
    'category',
    'counterparty',
    'entry_type',
    'event_subtype',
    'event_type',
    'ignored_asset',
    'location',
    'percentage_of_net_value',
    'price',
    'product',
    'sequence_index',
    'timestamp',
    'usd_value',
    'value',
})

ALLOWED_SQL_PREFIXES: Final = ('select ', 'with ')
DENIED_SQL_TOKENS: Final = frozenset({
    'alter', 'attach', 'copy', 'create', 'delete', 'drop',
    'insert', 'replace', 'truncate', 'update',
})
SQL_ERROR_HINT: Final = (
    'Use list_tables() and describe_table(table) to inspect the schema, then query, e.g. '
    '`select * from history_events limit 1`.'
)
# Detects bare crypto identifiers embedded in otherwise-safe strings (defence in depth on
# top of the column allowlist; catches e.g. an address inside a counterparty product url).
SENSITIVE_IDENTIFIER_RE: Final = re.compile(
    r'(?:'
    r'0x[a-fA-F0-9]{40}|'           # EVM address
    r'0x[a-fA-F0-9]{64}|'           # EVM tx/hash
    r'(?:bc1|tb1)[ac-hj-np-z02-9]{20,90}|'  # bech32 BTC
    r'[13][a-km-zA-HJ-NP-Z1-9]{25,34}|'     # base58 BTC
    r'[1-9A-HJ-NP-Za-km-z]{32,44}'  # base58 (Solana etc.)
    r')',
)

# Per-process random seed so the same identifier hashes consistently within a session
# (GROUP BY / joins over the hash still work) but is not linkable across sessions or back
# to the real value.
_session_seed: Final = secrets.token_bytes(32)


@dataclass(frozen=True)
class TableData:
    frame: pl.DataFrame
    source: dict[str, Any]


@dataclass(frozen=True)
class AnalyticsScope:
    from_timestamp: int | None
    to_timestamp: int | None
    include_ignored_assets: bool
    privacy_mode: PrivacyMode


def _hash_identifier(value: Any) -> str | None:
    if value is None:
        return None
    return f'anon_{hmac.new(_session_seed, str(value).encode(), sha256).hexdigest()[:16]}'


_KNOWN_COLUMN_NAMES: Final = tuple(sorted(
    TEXT_COLUMN_NAMES | STRICT_IDENTIFIER_COLUMN_NAMES | SAFE_PASSTHROUGH_COLUMN_NAMES,
    key=len,
    reverse=True,
))


def _base_column_name(column: str) -> str:
    """The flattener prefixes nested keys (``extra_data_address``). Resolve a flattened
    column to the known base name it carries (longest match wins, so ``location_label``
    stays ``location_label`` rather than collapsing to ``label``); unknown columns return
    themselves and thus fall through to the fail-closed branch.
    """
    for known in _KNOWN_COLUMN_NAMES:
        if column == known or column.endswith(f'_{known}'):
            return known
    return column


def _to_float(value: Any) -> float | None:
    if value in (None, ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_scalar(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return json.dumps(value, default=str, sort_keys=True)


def _flatten(value: dict[str, Any], prefix: str = '') -> dict[str, Any]:
    """Recursively flatten a nested mapping into ``parent_child`` keyed scalars. Numeric
    strings additionally get a ``<col>_float`` companion so SQL can do arithmetic directly.
    """
    row: dict[str, Any] = {}
    for key, nested in value.items():
        column = f'{prefix}_{key}' if prefix else str(key)
        if isinstance(nested, dict):
            row.update(_flatten(nested, prefix=column))
            continue
        scalar = _json_scalar(nested)
        row[column] = scalar
        if isinstance(scalar, str) and (as_float := _to_float(scalar)) is not None:
            row[f'{column}_float'] = as_float
    return row


def _sanitize_row(row: dict[str, Any], privacy_mode: PrivacyMode) -> dict[str, Any]:
    """Strip identifiers from one flattened row according to ``privacy_mode``.

    Fail-closed: a column is emitted verbatim only if it is explicitly allowlisted (or we
    are in ``raw`` mode). Every other string is hashed rather than passed through, so a
    field we have never seen before defaults to hidden. Numbers/bools are the analytic
    payload and are kept (they carry no identifier on their own).
    """
    if privacy_mode == 'raw':
        return row

    identifier_columns = (
        STRICT_IDENTIFIER_COLUMN_NAMES if privacy_mode == 'strict' else PII_COLUMN_NAMES
    )
    sanitized: dict[str, Any] = {}
    for column, value in row.items():
        base = _base_column_name(column)
        if base in TEXT_COLUMN_NAMES:
            has_value = value not in (None, '')
            sanitized[f'has_{column}'] = has_value
            sanitized[column] = REDACTED_TEXT if has_value else None
        elif base in identifier_columns:
            sanitized[f'{column}_hash'] = _hash_identifier(value)
            # In balanced mode a human-friendly account label (e.g. "Kraken main") that is
            # not itself an address stays readable; anything address-shaped is hashed only.
            if (
                privacy_mode == 'balanced' and
                base == 'location_label' and
                isinstance(value, str) and
                SENSITIVE_IDENTIFIER_RE.search(value) is None
            ):
                sanitized[column] = value
        elif base in SAFE_PASSTHROUGH_COLUMN_NAMES:
            sanitized[column] = value
        elif isinstance(value, str):
            # Unrecognized string: never leak it. Keep a numeric companion if it is really
            # a number, otherwise hash it so it can still be grouped/joined on.
            if (as_float := _to_float(value)) is not None:
                sanitized[f'{column}_float'] = as_float
            else:
                sanitized[f'{column}_hash'] = _hash_identifier(value)
        else:
            sanitized[column] = value  # int / float / bool / None: safe analytic payload
    return sanitized


def _promote_entry(raw: dict[str, Any]) -> dict[str, Any]:
    """The history/events API wraps each event's fields in an ``entry`` sub-object next to
    sibling metadata. Promote those fields to the top level so SQL columns read as
    ``timestamp``/``location``/``asset`` rather than ``entry_timestamp`` etc.
    """
    if not isinstance(inner := raw.get('entry'), dict):
        return raw
    return {**{key: value for key, value in raw.items() if key != 'entry'}, **inner}


def _load_history_events(scope: AnalyticsScope) -> TableData:
    # No cap by default: load the complete (time-scoped) set so the user gets complete data
    # unless they explicitly bound it with --max-events to limit load time on a huge history.
    max_events = get_backend_config().max_events
    rows: list[dict[str, Any]] = []
    offset = 0
    entries_found: int | None = None
    entries_total: int | None = None
    entries_limit: int | None = None
    while max_events is None or len(rows) < max_events:
        result = query_history_events_page(
            limit=PAGE_SIZE,
            offset=offset,
            from_timestamp=scope.from_timestamp,
            to_timestamp=scope.to_timestamp,
            exclude_ignored_assets=scope.include_ignored_assets is False,
        )
        entries_found = result.get('entries_found')
        entries_total = result.get('entries_total')
        entries_limit = result.get('entries_limit')
        if not isinstance(entries := result.get('entries'), list) or len(entries) == 0:
            break

        rows.extend(
            _sanitize_row(_flatten(_promote_entry(entry)), scope.privacy_mode)
            for entry in entries if isinstance(entry, dict)
        )
        offset += PAGE_SIZE
        if isinstance(entries_found, int) and offset >= entries_found:
            break

    if max_events is not None and len(rows) > max_events:
        rows = rows[:max_events]
    cache_truncated = (
        max_events is not None and
        isinstance(entries_found, int) and
        entries_found > len(rows)
    )
    frame = pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()
    if 'timestamp' in frame.columns and frame.schema['timestamp'].is_integer():
        # Add readable date columns derived from the ms timestamp so an LLM can filter on
        # `year` / `datetime` instead of computing error-prone unix-millisecond bounds.
        frame = frame.with_columns(
            _dt=pl.from_epoch(pl.col('timestamp'), time_unit='ms'),
        ).with_columns(
            datetime=pl.col('_dt').dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            year=pl.col('_dt').dt.year(),
        ).drop('_dt')

    return TableData(
        frame=frame,
        source={
            'endpoint': 'history/events',
            'range_scoped': True,
            'cached_rows': len(rows),
            'cache_truncated': cache_truncated,
            'entries_found': entries_found,
            'entries_total': entries_total,
            'entries_limit': entries_limit,
            'privacy_mode': scope.privacy_mode,
        },
    )


def _load_balances(scope: AnalyticsScope) -> TableData:
    # Never force a refresh here: recalculating balances is slow and should stay an explicit
    # user action in the app. The analytics layer reads the latest cached snapshot.
    result = query_all_balances(refresh=False, timeout=get_backend_config().timeout)
    rows: list[dict[str, Any]] = []
    for category in ('assets', 'liabilities'):
        holdings = result.get(category)
        if not isinstance(holdings, dict):
            continue
        for asset, data in holdings.items():
            if not isinstance(data, dict):
                continue
            rows.append(_sanitize_row(
                _flatten({'category': category[:-1], 'asset': asset, **data}),
                scope.privacy_mode,
            ))

    return TableData(
        frame=pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame(),
        source={
            'endpoint': 'balances',
            'range_scoped': False,
            'cached_rows': len(rows),
            'net_value': result.get('net_value'),
            'privacy_mode': scope.privacy_mode,
        },
    )


TABLE_LOADERS: Final[dict[str, Callable[[AnalyticsScope], TableData]]] = {
    'history_events': _load_history_events,
    'balances': _load_balances,
}


def _normalize_tables(tables: list[str] | None) -> list[str]:
    return sorted(set(tables)) if tables else list(DEFAULT_TABLES)


def _filter_seconds(timestamp: int) -> int | None:
    """Normalize a time-range bound to unix seconds for the backend filter. 0 means no
    bound; a millisecond value (the unit of the ``timestamp`` column) is accepted and
    converted, so callers can pass milliseconds consistently.
    """
    if not timestamp:
        return None
    return timestamp // 1000 if timestamp >= MS_THRESHOLD else timestamp


def _validate_sql(sql: str) -> str | None:
    normalized = ' '.join(sql.strip().lower().split())
    if not normalized.startswith(ALLOWED_SQL_PREFIXES):
        return 'Only read-only SELECT/WITH queries over analytics tables are allowed'
    if ';' in normalized.rstrip(';'):
        return 'Only a single SQL statement is allowed'
    tokens = set(normalized.replace(',', ' ').replace('(', ' ').replace(')', ' ').split())
    if disallowed := tokens & DENIED_SQL_TOKENS:
        return f'Disallowed SQL token(s): {", ".join(sorted(disallowed))}'
    return None


def _error(error_type: str, message: str, **details: Any) -> dict[str, Any]:
    return {'error': {'type': error_type, 'message': message, 'hint': SQL_ERROR_HINT, **details}}


def _summary(table: str, table_data: TableData) -> dict[str, Any]:
    return {'table': table, 'rows': table_data.frame.height, 'source': table_data.source}


class AnalyticsSession:
    """In-memory, privacy-filtered table store queried with Polars SQL. One instance lives
    for the lifetime of the MCP server process and is shared across tool calls.
    """

    def __init__(self) -> None:
        self._tables: dict[str, TableData] = {}
        self._last_scope: AnalyticsScope | None = None

    def _current_scope(
            self,
            from_timestamp: int,
            to_timestamp: int,
            include_ignored_assets: bool,
    ) -> AnalyticsScope:
        return AnalyticsScope(
            from_timestamp=_filter_seconds(from_timestamp),
            to_timestamp=_filter_seconds(to_timestamp),
            include_ignored_assets=include_ignored_assets,
            privacy_mode=get_backend_config().privacy_mode,
        )

    def refresh(
            self,
            tables: list[str] | None,
            from_timestamp: int,
            to_timestamp: int,
            include_ignored_assets: bool,
    ) -> dict[str, Any]:
        scope = self._current_scope(from_timestamp, to_timestamp, include_ignored_assets)
        loaded: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for table in _normalize_tables(tables):
            if (loader := TABLE_LOADERS.get(table)) is None:
                errors[table] = f'Unknown table {table!r}. Available: {list(AVAILABLE_TABLES)}'
                continue
            try:
                self._tables[table] = (table_data := loader(scope))
            except BackendQueryError as e:
                errors[table] = str(e)
            except (KeyError, TypeError, pl.exceptions.PolarsError) as e:
                errors[table] = str(e)
            else:
                loaded[table] = _summary(table, table_data)

        self._last_scope = scope
        return {'tables': loaded, 'errors': errors, 'privacy_mode': scope.privacy_mode}

    def list_tables(self) -> dict[str, Any]:
        return {
            'loaded': {t: _summary(t, d) for t, d in sorted(self._tables.items())},
            'default_tables': list(DEFAULT_TABLES),
            'available_tables': list(AVAILABLE_TABLES),
            'privacy_mode': get_backend_config().privacy_mode,
        }

    def describe_table(self, table: str) -> dict[str, Any]:
        if (table_data := self._tables.get(table)) is None:
            return _error(
                'unknown_table',
                f'Table {table!r} is not loaded. Call refresh_analytics_data first.',
                available_tables=list(AVAILABLE_TABLES),
            )
        return {
            'table': table,
            'columns': [
                {'name': name, 'dtype': str(dtype)}
                for name, dtype in table_data.frame.schema.items()
            ],
            'rows': table_data.frame.height,
            'source': table_data.source,
        }

    def query_sql(self, sql: str, max_rows: int) -> dict[str, Any]:
        if (error := _validate_sql(sql)) is not None:
            return _error('validation_error', error)
        if len(self._tables) == 0:
            return _error(
                'no_tables_loaded',
                'No analytics tables are loaded yet. Call refresh_analytics_data first.',
            )

        context = pl.SQLContext()
        for table, table_data in self._tables.items():
            context.register(table, table_data.frame)
        try:
            result_frame = context.execute(sql, eager=True)
        except pl.exceptions.PolarsError as e:
            return _error(
                'sql_execution_error',
                str(e),
                available_columns={t: d.frame.columns for t, d in self._tables.items()},
            )

        bounded = min(max(max_rows, 1), MAX_RESULT_ROWS)
        result_rows = result_frame.head(bounded).to_dicts()
        return {
            'columns': result_frame.columns,
            'rows': result_rows,
            'row_count': result_frame.height,
            'returned_rows': len(result_rows),
            'result_truncated': result_frame.height > bounded,
            'privacy_mode': get_backend_config().privacy_mode,
        }

    def clear(self) -> None:
        self._tables.clear()
        self._last_scope = None


_analytics_session = AnalyticsSession()


def get_analytics_session() -> AnalyticsSession:
    return _analytics_session
