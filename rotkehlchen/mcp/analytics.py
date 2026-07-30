from __future__ import annotations

import hmac
import json
import re
import secrets
import sqlite3
import threading
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Final

import pandas as pd

from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.mcp.backend import (
    BackendQueryError,
    balances_timeout,
    get_backend_config,
    query_all_balances,
    query_historical_prices,
    query_history_events_page,
    query_settings,
)
from rotkehlchen.mcp.taxonomy import resolve_direction, resolve_group
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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
# Valuation batches this many (asset, timestamp) pairs per backend request. The endpoint is
# linear in pair count (~8.4s per 1000 against a real history), so the chunk size only bounds
# request size, not total cost -- which is why valuation is opt-in.
PRICE_LOOKUP_CHUNK_SIZE: Final = 500
# How many consecutive empty pages to tolerate before giving up on a load. Empty windows are
# normal mid-range; an endless run of them is a backend fault and must not spin forever.
MAX_CONSECUTIVE_EMPTY_PAGES: Final = 5
# describe_table lists a string column's actual values when there are few enough for the set
# to be a useful hint (an enum) rather than a data dump.
MAX_DISTINCT_VALUES_SCANNED: Final = 50
MAX_DISTINCT_VALUES_REPORTED: Final = 10
# ``counterparty`` is the column whose vocabulary an agent most needs -- protocol names are
# not guessable the way event types are -- yet any real account carries well over the general
# scan cap (105 distinct on the account this was measured against), so it was the one
# documented column that never got a listing. Scan far more of it; MAX_DISTINCT_VALUES_REPORTED
# still bounds what is returned, so the payload does not grow.
WIDE_SCAN_COLUMN_LIMITS: Final = {'counterparty': 500}
# Prices are matched within an hour of the event, the same tolerance rotki's own CSV export
# uses, so bucketing event timestamps to the hour costs no accuracy while roughly halving the
# number of distinct lookups (measured: 64,936 exact-second pairs vs 31,878 hourly ones).
PRICE_TOLERANCE_SECONDS: Final = HOUR_IN_SECONDS
# The lookup radius has to be *twice* the bucket width, not equal to it. The backend matches
# a price with `timestamp BETWEEN queried - distance AND queried + distance`, and what we
# query is the bucket, not the event: an event sitting 59 minutes into its bucket asks from
# an hour behind itself, so with an equal radius its window ran from 2 hours before the event
# to 1 second after it -- a cached price minutes *later* than the event was missed even
# though it was well inside the intended tolerance. Doubling restores a full +/- hour around
# every event in the bucket while keeping the ~2x lookup saving bucketing buys.
PRICE_LOOKUP_RADIUS_SECONDS: Final = 2 * PRICE_TOLERANCE_SECONDS
DEFAULT_VALUE_CURRENCY: Final = 'USD'
# Beacon-chain withdrawals: the entry type rotki files them under, and the taxonomy group a
# partial one belongs to. See _add_partial_withdrawal_income.
ETH_WITHDRAWAL_ENTRY_TYPE: Final = 'eth withdrawal event'
INCOME_GROUP: Final = 'income'

# --- privacy classification -------------------------------------------------------------
# User-authored / decoder-written free text: never emitted verbatim outside ``raw`` mode
# (only a ``has_<col>`` flag). Despite its name ``user_notes`` is the one that carries
# decoder output with addresses in it ("Burn 0.0001 XDAI for gas") *and* is user-editable,
# so its provenance is mixed and it stays redacted.
USER_TEXT_COLUMN_NAMES: Final = frozenset({'notes', 'user_notes'})
# Text rotki generates at serialization time from a fixed set of templates over amount,
# asset symbol and location name -- no identifier is ever interpolated into one. Redacting
# these threw away readable descriptions for no privacy gain, so in ``balanced`` they pass
# through scrubbed (an asset *name* is attacker-controlled on a scam token, so the scrub is
# what keeps the no-identifier property true rather than merely likely). ``strict`` still
# redacts them outright.
GENERATED_TEXT_COLUMN_NAMES: Final = frozenset({'auto_notes'})
TEXT_COLUMN_NAMES: Final = USER_TEXT_COLUMN_NAMES | GENERATED_TEXT_COLUMN_NAMES
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
# ``location_label`` on an exchange row is the *account name*, which defaults to the venue
# name but is user-editable ("Coinbase 1", "mom's savings"). In ``balanced`` only a value that
# is exactly a rotki location name passes through readable; anything else is the user's own
# text and gets hashed like every other identifier. This costs no venue information -- the
# ``location`` column already carries it -- only the ability to tell two accounts on the same
# venue apart *by name*, and their hashes still distinguish them for grouping.
READABLE_LOCATION_LABELS: Final = frozenset(str(location) for location in Location)
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
    'price_missing',
    'product',
    'sequence_index',
    'timestamp',
    'usd_value',
    'value',
})

ALLOWED_SQL_PREFIXES: Final = ('select ', 'with ')
# ``replace`` is deliberately absent: it is a perfectly ordinary read-only scalar function
# (``select replace(counterparty, '-', ' ')``) and SQLite's ``REPLACE INTO`` is already
# blocked by the select/with prefix requirement. The denylist is defence in depth on top of
# that prefix check and the read-only in-memory connection, not the primary guard.
DENIED_SQL_TOKENS: Final = frozenset({
    'alter', 'attach', 'copy', 'create', 'delete', 'drop',
    'insert', 'truncate', 'update',
})
# Quoted strings and identifiers are stripped before tokenising, so a denied word appearing
# inside a literal (or a semicolon inside one) does not get mistaken for a statement.
SQL_QUOTED_RE: Final = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"")
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
    frame: pd.DataFrame
    source: dict[str, Any]


@dataclass(frozen=True)
class AnalyticsScope:
    from_timestamp: int | None
    to_timestamp: int | None
    include_ignored_assets: bool
    privacy_mode: PrivacyMode
    include_values: bool = False
    aggregate_by_group_ids: bool = False


def _hash_identifier(value: Any) -> str | None:
    if value is None:
        return None
    return f'anon_{hmac.new(_session_seed, str(value).encode(), sha256).hexdigest()[:16]}'


def _scrub_identifiers(value: str) -> str:
    """Replace any identifier embedded in otherwise-safe text with the same hash the column
    level hashing would produce, so the text stays cross-referenceable with hashed columns.
    """
    return SENSITIVE_IDENTIFIER_RE.sub(lambda match: str(_hash_identifier(match.group())), value)


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
            if not has_value:
                sanitized[column] = None
            elif base in GENERATED_TEXT_COLUMN_NAMES and privacy_mode == 'balanced':
                sanitized[column] = _scrub_identifiers(str(value))
            else:
                sanitized[column] = REDACTED_TEXT
        elif base in identifier_columns:
            sanitized[f'{column}_hash'] = _hash_identifier(value)
            # In balanced mode a location label that is exactly a venue name (e.g. "kraken")
            # stays readable; a user-assigned account name ("Coinbase 1") is the user's own
            # text and is hashed like any other identifier. See READABLE_LOCATION_LABELS.
            if (
                privacy_mode == 'balanced' and
                base == 'location_label' and
                isinstance(value, str) and
                value.lower() in READABLE_LOCATION_LABELS
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


def _add_partial_withdrawal_income(frame: pd.DataFrame) -> None:
    """Reclassify partial beacon-chain withdrawals as ``income``, in place.

    rotki records every beacon-chain withdrawal as ``staking``/``remove asset``, which the
    taxonomy groups as ``staking`` -- returned principal. That is right for a full validator
    exit and wrong for a partial withdrawal: the consensus layer only ever skims the balance
    *above* the validator's effective balance, so a partial withdrawal is reward in its
    entirety. rotki's own PnL engine agrees --
    ``DBEth2.process_non_accumulating_validators_balances_and_pnl`` counts every partial
    withdrawal as profit and subtracts principal only on an exit. Without this an account
    with validator exits has its whole ETH staking income written off as principal.

    Known imprecision: on an accumulating (0x02) validator a *requested* partial withdrawal
    does return principal, unlike an automatic skim. Telling the two apart needs the running
    per-validator deposit ledger (``process_accumulating_validators_balances_and_pnl``), not
    anything on the row, so those are counted as income here. The recipe says so.
    """
    if not {'entry_type', 'is_exit', 'event_group'} <= set(frame.columns):
        return

    # NaN on every non-withdrawal row, and ``eq`` resolves those to False rather than raising.
    frame.loc[
        frame['entry_type'].eq(ETH_WITHDRAWAL_ENTRY_TYPE) & frame['is_exit'].eq(False),
        'event_group',
    ] = INCOME_GROUP


def _add_taxonomy_columns(frame: pd.DataFrame) -> None:
    """Add rotki's own ``direction`` and ``event_group`` for each event, in place.

    The serialized event carries neither, so without them an agent has to infer income from
    ``event_type`` -- the guess that double counts MEV rewards -- and hand-maintain subtype
    lists to separate reward from returned principal. Deriving both here from the same
    mappings the rest of rotki uses makes the correct aggregation a plain ``group by``.
    Resolution is cached per type/subtype/location because a large history has ~100 distinct
    combinations across six figures of rows.

    The column is ``event_group`` rather than ``group`` because ``group`` is a SQL keyword
    and every query touching it would need quoting.
    """
    if not {'event_type', 'event_subtype', 'location'} <= set(frame.columns):
        return

    cache: dict[tuple[Any, Any, Any], tuple[str | None, str | None]] = {}
    resolved: list[tuple[str | None, str | None]] = []
    for key in zip(frame['event_type'], frame['event_subtype'], frame['location'], strict=True):
        if key not in cache:
            cache[key] = (resolve_direction(*key), resolve_group(*key))
        resolved.append(cache[key])

    frame['direction'] = [direction for direction, _ in resolved]
    frame['event_group'] = [group for _, group in resolved]
    _add_partial_withdrawal_income(frame)


def _iter_entries(entries: list[Any]) -> Iterator[dict[str, Any]]:
    """Yield every event in a page, including the ones the API nests.

    Without ``aggregate_by_group_ids`` the endpoint returns a *sub-list* per group for EVM
    and Solana swaps and for matched asset movements, so a page mixes plain event dicts with
    lists of them. Keeping only the dicts silently dropped every on-chain swap and matched
    deposit/withdrawal from the loaded table -- and, because a grouped sub-list still counts
    as one entry against the page limit, made pages look short for no visible reason.
    """
    for entry in entries:
        if isinstance(entry, dict):
            yield entry
        elif isinstance(entry, list):
            yield from (grouped for grouped in entry if isinstance(grouped, dict))


def _promote_entry(raw: dict[str, Any]) -> dict[str, Any]:
    """The history/events API wraps each event's fields in an ``entry`` sub-object next to
    sibling metadata. Promote those fields to the top level so SQL columns read as
    ``timestamp``/``location``/``asset`` rather than ``entry_timestamp`` etc.
    """
    if not isinstance(inner := raw.get('entry'), dict):
        return raw
    return {**{key: value for key, value in raw.items() if key != 'entry'}, **inner}


def _resolve_prices(
        pairs: list[tuple[str, int]],
        target_asset: str,
) -> dict[tuple[str, int], float]:
    """Look up unit prices for ``(asset, unix_second)`` pairs, cache-only and chunked.

    ``max_seconds_distance`` maps to the endpoint's ``only_cache_period``, which is what
    keeps the query inside rotki's stored price history: the MCP must never trigger a remote
    oracle fetch on an agent's behalf. It is a search *radius*, not an exactness requirement
    -- the backend takes the closest stored row inside the window -- so it has to account for
    the hour of bucketing already applied to the timestamp. See PRICE_LOOKUP_RADIUS_SECONDS.

    The response is keyed by the timestamp we *asked* for (the backend rewrites the matched
    row's timestamp to the queried one), so pairs join straight back without a nearest-match
    search -- but that also means a hit says nothing about how stale the matched price is.
    """
    # The main currency is worth exactly one of itself, and the price endpoint has no
    # such pair cached, so asking for it leaves every fiat leg of an exchange trade
    # unpriced. Resolve those locally and keep them out of the request entirely.
    resolved: dict[tuple[str, int], float] = {
        pair: 1.0 for pair in pairs if pair[0] == target_asset
    }
    remaining = [pair for pair in pairs if pair[0] != target_asset]
    for start in range(0, len(remaining), PRICE_LOOKUP_CHUNK_SIZE):
        result = query_historical_prices(
            asset_timestamps=remaining[start:start + PRICE_LOOKUP_CHUNK_SIZE],
            target_asset=target_asset,
            max_seconds_distance=PRICE_LOOKUP_RADIUS_SECONDS,
        )
        for asset, by_timestamp in result['assets'].items():
            if not isinstance(by_timestamp, dict):
                continue
            for timestamp, price in by_timestamp.items():
                # Both levels arrive as strings over JSON (object keys always are, and prices
                # are serialized decimals), so neither can be trusted to convert.
                if (
                    (second := _to_float(timestamp)) is not None and
                    (unit_price := _to_float(price)) is not None
                ):
                    resolved[asset, int(second)] = unit_price

    return resolved


def _add_fiat_values(frame: pd.DataFrame) -> dict[str, Any]:
    """Add ``price``/``value``/``price_missing`` to a loaded history frame, in place.

    Mirrors how rotki itself values events for the CSV export (dedupe the lookups, read them
    from the price cache, multiply by the amount) minus the oracle fallback. Rows whose price
    is not cached get a null ``value``, never 0 -- a zero would silently understate every
    total an agent computes over the column.
    """
    target_asset = str(query_settings().get('main_currency') or DEFAULT_VALUE_CURRENCY)
    summary: dict[str, Any] = {
        'value_currency': target_asset,
        'priced_rows': 0,
        'unpriced_rows': len(frame),
        'lookup_count': 0,
    }
    if not {'asset', 'timestamp', 'amount_float'} <= set(frame.columns):
        return summary  # nothing to join on (empty history, or a fully ragged one)

    # Bucket to the hour the tolerance already spans; ``to_numeric`` keeps a ragged timestamp
    # column (missing on some entry types -> object dtype) from blowing up the arithmetic.
    seconds: pd.Series = pd.to_numeric(frame['timestamp'], errors='coerce')
    buckets = seconds // 1000 // PRICE_TOLERANCE_SECONDS * PRICE_TOLERANCE_SECONDS
    keys = [
        (asset, int(bucket)) if isinstance(asset, str) and pd.notna(bucket) else None
        for asset, bucket in zip(frame['asset'], buckets, strict=True)
    ]
    if len(pairs := sorted({key for key in keys if key is not None})) == 0:
        return summary

    resolved = _resolve_prices(pairs=pairs, target_asset=target_asset)
    frame['price'] = [resolved.get(key) if key is not None else None for key in keys]
    # NaN propagates through the multiplication, so an unpriced row lands as NULL in sqlite.
    amounts: pd.Series = pd.to_numeric(frame['amount_float'], errors='coerce')
    frame['value'] = amounts * frame['price']
    frame['price_missing'] = frame['price'].isna()
    return summary | {
        'priced_rows': int((~frame['price_missing']).sum()),
        'unpriced_rows': int(frame['price_missing'].sum()),
        'lookup_count': len(pairs),
    }


def _load_history_events(scope: AnalyticsScope) -> TableData:
    # No cap by default: load the complete (time-scoped) set so the user gets complete data
    # unless they explicitly bound it with --max-events to limit load time on a huge history.
    max_events = get_backend_config().max_events
    rows: list[dict[str, Any]] = []
    offset = 0
    entries_found: int | None = None
    entries_total: int | None = None
    entries_limit: int | None = None
    consecutive_empty = 0
    completeness = 'complete'
    while max_events is None or len(rows) < max_events:
        result = query_history_events_page(
            limit=PAGE_SIZE,
            offset=offset,
            from_timestamp=scope.from_timestamp,
            to_timestamp=scope.to_timestamp,
            exclude_ignored_assets=scope.include_ignored_assets is False,
            aggregate_by_group_ids=scope.aggregate_by_group_ids,
        )
        entries_found = result.get('entries_found')
        entries_total = result.get('entries_total')
        entries_limit = result.get('entries_limit')
        if not isinstance(entries := result.get('entries'), list):
            completeness = 'stopped_early'
            break

        if len(entries) == 0:
            # A window can legitimately come back empty (every event in it filtered out), so
            # an empty page means "skip this window", not "end of data" -- stopping here was
            # cutting loads short while still reporting them as complete. Bounded so a
            # backend that only ever returns nothing cannot spin forever, and if we give up
            # with ground still to cover the load is reported as incomplete.
            consecutive_empty += 1
            if (
                consecutive_empty >= MAX_CONSECUTIVE_EMPTY_PAGES or
                not isinstance(entries_found, int)
            ):
                if isinstance(entries_found, int) and offset < entries_found:
                    completeness = 'stopped_early'
                break
        else:
            consecutive_empty = 0
            rows.extend(
                _sanitize_row(_flatten(_promote_entry(entry)), scope.privacy_mode)
                for entry in _iter_entries(entries)
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
    if cache_truncated:
        completeness = 'truncated_by_max_events'
    frame = pd.DataFrame(rows) if rows else pd.DataFrame()
    for column in frame.columns:
        if str(column).startswith('has_'):
            # These flags are only emitted for rows that carry the underlying field, so
            # ragged event types leave gaps and the column ends up object dtype -- which then
            # reaches SQL as a confusing 0/1/NULL mix. A missing flag means the field was
            # absent on that event type, which is exactly false, so fill it and keep a real
            # bool.
            frame[column] = frame[column].fillna(value=False).astype(bool)

    if 'timestamp' in frame.columns and pd.api.types.is_integer_dtype(frame['timestamp']):
        # Add readable date columns derived from the ms timestamp so an LLM can filter on
        # `year` / `datetime` instead of computing error-prone unix-millisecond bounds.
        dt = pd.to_datetime(frame['timestamp'], unit='ms', utc=True)
        frame['datetime'] = dt.dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        frame['year'] = dt.dt.year

    _add_taxonomy_columns(frame)

    # Valuation runs here, in the loader, so its minutes of price lookups stay outside the
    # connection lock and queries keep serving the previous snapshot meanwhile.
    values = _add_fiat_values(frame) if scope.include_values else {}
    return TableData(
        frame=frame,
        source={
            'endpoint': 'history/events',
            'range_scoped': True,
            'rows_loaded': len(rows),
            'completeness': completeness,
            'cache_truncated': cache_truncated,
            # The backend's own counters, which do not agree with rows_loaded and are not
            # meant to: entries_found is its pre-serialization estimate of matching events.
            'backend_metadata': {
                'entries_found': entries_found,
                'entries_total': entries_total,
                'entries_limit': entries_limit,
            },
            'privacy_mode': scope.privacy_mode,
            **values,
        },
    )


def _load_balances(scope: AnalyticsScope) -> TableData:
    # Never force a refresh here: recalculating balances is slow and should stay an explicit
    # user action in the app. The analytics layer reads the latest cached snapshot.
    result = query_all_balances(refresh=False, timeout=balances_timeout())
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
        frame=pd.DataFrame(rows) if rows else pd.DataFrame(),
        source={
            'endpoint': 'balances',
            'range_scoped': False,
            'rows_loaded': len(rows),
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
    unquoted = SQL_QUOTED_RE.sub(' ', normalized)
    if ';' in unquoted.rstrip(';'):
        return 'Only a single SQL statement is allowed'
    tokens = set(unquoted.replace(',', ' ').replace('(', ' ').replace(')', ' ').split())
    if disallowed := tokens & DENIED_SQL_TOKENS:
        return f'Disallowed SQL token(s): {", ".join(sorted(disallowed))}'
    return None


def _hashed_reason(column: str, privacy_mode: PrivacyMode) -> str | None:
    """Why a column holds opaque hashes instead of values, or None if it is readable.

    ``pii`` means the column was always going to be hashed (an address, a tx hash);
    ``unrecognized`` means it hit the fail-closed branch -- a column the allowlist does not
    know, hashed rather than leaked. The distinction tells an agent whether a column is
    hidden by policy or merely unclassified. Which set applies depends on the mode the data
    was loaded under, since ``strict`` also treats user-authored labels as identifiers.
    """
    if not column.endswith('_hash'):
        return None
    identifier_columns = (
        STRICT_IDENTIFIER_COLUMN_NAMES if privacy_mode == 'strict' else PII_COLUMN_NAMES
    )
    base = _base_column_name(column.removesuffix('_hash'))
    return 'pii' if base in identifier_columns else 'unrecognized'


def _describe_column(
        name: str,
        series: pd.Series,
        sqlite_type: str | None,
        privacy_mode: PrivacyMode,
) -> dict[str, Any]:
    """Describe one column: how SQL sees it, how empty it is, and -- for small enums -- what
    is actually in it, so an agent does not have to spend a round trip on SELECT DISTINCT.
    """
    column: dict[str, Any] = {
        'name': name,
        # The pandas dtype is not what the query sees: everything goes through to_sql, so a
        # bool lands as an integer and an all-null object column as a float.
        'dtype': str(series.dtype),
        'sqlite_type': sqlite_type,
        'null_fraction': round(float(series.isna().mean()), 4) if len(series) > 0 else None,
    }
    if column['null_fraction'] == 1.0:
        column['all_null'] = True  # present but carries nothing; do not build a query on it
    if (reason := _hashed_reason(name, privacy_mode)) is not None:
        # Never list hashed values: pages of anon_ strings are pure noise to an agent.
        return column | {'hashed': True, 'hashed_reason': reason}

    # pandas gives string columns a dedicated ``str`` dtype and only falls back to ``object``
    # for ragged/mixed ones, so both are candidates for a value listing.
    is_texty = pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)
    scan_limit = WIDE_SCAN_COLUMN_LIMITS.get(name, MAX_DISTINCT_VALUES_SCANNED)
    if is_texty and len(counts := series.value_counts()) <= scan_limit:
        column['distinct_count'] = len(counts)
        # A long tail of values that each occur once is not an enum -- it is per-row data
        # that happens to be sparse, like extra_data_amount holding one distinct amount per
        # row. Listing those puts row-level financial detail in what should be a schema
        # summary and tells an agent nothing about the vocabulary. A short list is still
        # worth showing even if nothing repeats: it is cheap and it is the whole domain.
        if len(counts) <= MAX_DISTINCT_VALUES_REPORTED or int(counts.iloc[0]) > 1:
            column['top_values'] = [
                {'value': value, 'rows': int(rows)}
                for value, rows in counts.head(MAX_DISTINCT_VALUES_REPORTED).items()
                # defence in depth: a hash must never reach the agent through this path
                if not (isinstance(value, str) and value.startswith('anon_'))
            ]
    return column


def _error(error_type: str, message: str, **details: Any) -> dict[str, Any]:
    return {'error': {'type': error_type, 'message': message, 'hint': SQL_ERROR_HINT, **details}}


def _summary(table: str, table_data: TableData) -> dict[str, Any]:
    return {'table': table, 'rows': len(table_data.frame), 'source': table_data.source}


class AnalyticsSession:
    """In-memory, privacy-filtered table store queried with SQL (sqlite over pandas
    DataFrames). One instance lives for the lifetime of the MCP server process and is
    shared across tool calls running in worker threads.
    """

    def __init__(self) -> None:
        self._tables: dict[str, TableData] = {}
        # Refreshes must not overtake each other, but should not block queries while loading.
        self._refresh_lock = threading.Lock()
        # asyncio.to_thread() may use a different worker for every tool call. The lock
        # serializes all connection and matching metadata access when thread affinity is off.
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(':memory:', check_same_thread=False)

    def _current_scope(
            self,
            from_timestamp: int,
            to_timestamp: int,
            include_ignored_assets: bool,
            include_values: bool,
            aggregate_by_group_ids: bool,
    ) -> AnalyticsScope:
        return AnalyticsScope(
            from_timestamp=_filter_seconds(from_timestamp),
            to_timestamp=_filter_seconds(to_timestamp),
            include_ignored_assets=include_ignored_assets,
            privacy_mode=get_backend_config().privacy_mode,
            include_values=include_values,
            aggregate_by_group_ids=aggregate_by_group_ids,
        )

    def refresh(
            self,
            tables: list[str] | None,
            from_timestamp: int,
            to_timestamp: int,
            include_ignored_assets: bool,
            include_values: bool = False,
            aggregate_by_group_ids: bool = False,
    ) -> dict[str, Any]:
        with self._refresh_lock:
            scope = self._current_scope(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                include_ignored_assets=include_ignored_assets,
                include_values=include_values,
                aggregate_by_group_ids=aggregate_by_group_ids,
            )
            loaded: dict[str, Any] = {}
            errors: dict[str, str] = {}
            pending: dict[str, TableData] = {}
            # Backend loading can be slow. Keep it outside the connection lock so queries
            # continue using the previous complete snapshot until the frames are ready.
            for table in _normalize_tables(tables):
                if (loader := TABLE_LOADERS.get(table)) is None:
                    errors[table] = f'Unknown table {table!r}. Available: {list(AVAILABLE_TABLES)}'
                    continue
                try:
                    table_data = loader(scope)
                except BackendQueryError as e:
                    errors[table] = str(e)
                except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
                    errors[table] = str(e)
                else:
                    pending[table] = table_data

            with self._lock:
                for table, table_data in pending.items():
                    try:
                        table_data.frame.to_sql(
                            table,
                            self._connection,
                            if_exists='replace',
                            index=False,
                        )
                    except (KeyError, TypeError, ValueError, sqlite3.Error) as e:
                        errors[table] = str(e)
                    else:
                        self._tables[table] = table_data
                        loaded[table] = _summary(table, table_data)

            return {'tables': loaded, 'errors': errors, 'privacy_mode': scope.privacy_mode}

    def list_tables(self) -> dict[str, Any]:
        with self._lock:
            return {
                'loaded': {t: _summary(t, d) for t, d in sorted(self._tables.items())},
                'default_tables': list(DEFAULT_TABLES),
                'available_tables': list(AVAILABLE_TABLES),
                'privacy_mode': get_backend_config().privacy_mode,
            }

    def describe_table(self, table: str) -> dict[str, Any]:
        with self._lock:
            if (table_data := self._tables.get(table)) is None:
                return _error(
                    'unknown_table',
                    f'Table {table!r} is not loaded. Call refresh_analytics_data first.',
                    available_tables=list(AVAILABLE_TABLES),
                )
            with closing(self._connection.cursor()) as cursor:
                # The declared sqlite types are the ones the query actually sees, so report
                # them next to the pandas dtypes rather than instead of them.
                sqlite_types = {
                    row[1]: row[2]
                    for row in cursor.execute(f'PRAGMA table_info("{table}")')
                }
            return {
                'table': table,
                'columns': [
                    _describe_column(
                        name=str(name),
                        series=table_data.frame[name],
                        sqlite_type=sqlite_types.get(str(name)),
                        # the mode the frame was built under, not the current config
                        privacy_mode=table_data.source.get('privacy_mode', 'balanced'),
                    )
                    for name in table_data.frame.columns
                ],
                'rows': len(table_data.frame),
                'source': table_data.source,
            }

    def query_sql(self, sql: str, max_rows: int) -> dict[str, Any]:
        if (error := _validate_sql(sql)) is not None:
            return _error('validation_error', error)

        with self._lock:
            if len(self._tables) == 0:
                return _error(
                    'no_tables_loaded',
                    'No analytics tables are loaded yet. Call refresh_analytics_data first.',
                )

            try:
                with closing(self._connection.cursor()) as cursor:
                    cursor.execute(sql)
                    # Read the rows straight from sqlite rather than through a DataFrame: a
                    # NULL in a numeric result column would come back out of pandas as NaN,
                    # which is not valid JSON and would corrupt the tool response. sqlite
                    # already hands back None/int/float/str natives.
                    columns = [description[0] for description in cursor.description]
                    fetched = cursor.fetchall()
            except sqlite3.Error as e:
                return _error(
                    'sql_execution_error',
                    str(e),
                    available_columns={
                        table: list(data.frame.columns)
                        for table, data in self._tables.items()
                    },
                )

        bounded = min(max(max_rows, 1), MAX_RESULT_ROWS)
        result_rows = [dict(zip(columns, row, strict=True)) for row in fetched[:bounded]]
        return {
            'columns': columns,
            'rows': result_rows,
            'row_count': len(fetched),
            'returned_rows': len(result_rows),
            'result_truncated': len(fetched) > bounded,
            'privacy_mode': get_backend_config().privacy_mode,
        }

    def clear(self) -> None:
        with self._refresh_lock, self._lock:
            self._tables.clear()
            self._connection.close()
            self._connection = sqlite3.connect(':memory:', check_same_thread=False)


_analytics_session = AnalyticsSession()


def get_analytics_session() -> AnalyticsSession:
    return _analytics_session
