import asyncio
from typing import Any

from rotkehlchen.mcp.analytics import DEFAULT_MAX_RESULT_ROWS, get_analytics_session
from rotkehlchen.mcp.registry import register_tool


@register_tool(name='refresh_analytics_data')
async def refresh_analytics_data(
        tables: list[str] | None = None,
        from_timestamp: int = 0,
        to_timestamp: int = 0,
        include_ignored_assets: bool = False,
        include_values: bool = False,
        aggregate_by_group_ids: bool = False,
) -> dict[str, Any]:
    """Load the user's rotki data into the local, privacy-filtered analytics session.

    This pulls data from the running rotki backend, flattens it into tables and applies
    privacy filtering, so that ``query_sql`` can then run SQL over it. Call this first (or
    again, to change the loaded time range / tables).

    - ``tables``: which tables to load. Defaults to ``["history_events"]``. ``"balances"``
      is available but opt-in because refreshing it can be slow. See ``list_tables`` for
      the full set.
    - ``from_timestamp`` / ``to_timestamp``: time range bounding ``history_events`` (0 means
      unbounded). Either unix seconds or milliseconds are accepted, so you can pass the same
      millisecond unit used by the ``timestamp`` column. Large histories are capped; the
      returned source metadata reports ``cache_truncated`` when that happens — narrow the
      range to load everything.
    - ``include_ignored_assets``: include events for assets the user has marked ignored.
    - ``include_values``: also value every event in the user's main currency, adding the
      ``value``, ``price`` and ``price_missing`` columns needed for any "how much was this
      worth" question. **Off by default because it is slow**: it costs roughly 8 seconds per
      1000 distinct (asset, hour) pairs, so a single year of history takes ~20-90s while a
      full multi-year history takes several minutes. Scope it with ``from_timestamp`` /
      ``to_timestamp`` whenever you can. Prices are read only from rotki's local cache, never
      fetched from an oracle, so some events may be unpriced: those get ``value = NULL`` and
      ``price_missing = 1`` rather than 0, and the returned source metadata reports
      ``value_currency``, ``priced_rows``, ``unpriced_rows`` and ``lookup_count``. Check
      ``unpriced_rows`` before reporting any total, or you will understate it.
    - ``aggregate_by_group_ids``: load one row per group instead of one row per event, each
      carrying a ``grouped_events_num`` count. Use it to count distinct transactions or
      trades. **The rows are representatives, not merged legs**: each is the *first* event of
      its group, so a trade loaded this way shows only what was spent, with no trace of what
      was received. It is not a substitute for self-joining on ``group_identifier`` when you
      need both sides of a swap, and you should not sum amounts over it.

    Returns the per-table row counts and source metadata, plus the active ``privacy_mode``.

    On coverage, check ``source.completeness`` before trusting any aggregate: ``complete``
    means everything in range was loaded, ``truncated_by_max_events`` that the server's
    ``--max-events`` cap cut the load short, and ``stopped_early`` that paging gave up with
    data still outstanding. ``source.rows_loaded`` is the authoritative count of what is
    actually queryable. The counters under ``source.backend_metadata`` are the backend's own
    and will not match it — ``entries_found`` in particular is a pre-serialization estimate,
    so do not compute coverage from it.
    """
    return await asyncio.to_thread(
        get_analytics_session().refresh,
        tables=tables,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        include_ignored_assets=include_ignored_assets,
        include_values=include_values,
        aggregate_by_group_ids=aggregate_by_group_ids,
    )


@register_tool(name='list_tables')
async def list_tables() -> dict[str, Any]:
    """List the analytics tables: which are loaded now, the defaults, and all available."""
    return await asyncio.to_thread(get_analytics_session().list_tables)


@register_tool(name='describe_table')
async def describe_table(table: str) -> dict[str, Any]:
    """Describe a loaded analytics table: its columns, row count and source metadata.

    Use this to discover the schema before writing SQL. Each column reports:

    - ``sqlite_type``, which is what your query actually sees, alongside the pandas
      ``dtype`` it was built from. They differ: booleans arrive as 0/1 integers.
    - ``null_fraction``, and ``all_null`` for columns that are present but carry nothing —
      many ``extra_data_*`` columns exist only for one protocol and are empty otherwise.
    - ``distinct_count`` and ``top_values`` for enum-like columns (``event_type``,
      ``location``, ``entry_type``, ``event_group``, ``counterparty``), so you do not need a
      SELECT DISTINCT round trip to learn the valid values. ``top_values`` holds only the
      most common few, so on a wide column like ``counterparty`` check ``distinct_count`` to
      see how much of the vocabulary you are being shown. A column whose values never repeat
      reports ``distinct_count`` alone: it is per-row data, not an enum.
    - ``hashed`` with a ``hashed_reason`` of ``pii`` (an address or hash, hidden by policy)
      or ``unrecognized`` (a column the allowlist does not know, hashed rather than leaked).

    Identifier columns are privacy-filtered: they appear as ``<col>_hash``, consistent within
    a session so you can still GROUP BY / JOIN on them but not reversible and not stable
    across sessions. Their values are never listed. Free-text ``notes``/``user_notes`` are
    redacted to a ``has_<col>`` flag, unless the server was started in ``raw`` privacy mode.
    """
    return await asyncio.to_thread(get_analytics_session().describe_table, table=table)


@register_tool(name='query_sql')
async def query_sql(sql: str, max_rows: int = DEFAULT_MAX_RESULT_ROWS) -> dict[str, Any]:
    """Run a read-only SQL query over the loaded, privacy-filtered analytics tables.

    The query runs against **SQLite**, so write SQLite-flavoured SQL. Aggregations, joins,
    grouping, ordering and window functions are all available and computed exactly — use it
    for the math (sums, cost basis candidates, rolling balances, per-asset/per-counterparty
    rollups, fee totals) rather than doing arithmetic yourself. Only a single
    ``SELECT``/``WITH`` statement is allowed; writes and DDL are rejected.

    Call ``refresh_analytics_data`` first to load data, and ``describe_table`` to learn the
    columns. The default table is ``history_events``. ``max_rows`` caps returned rows; the
    result reports ``result_truncated`` and the true ``row_count`` when more matched.

    Rules that decide whether an aggregate is right or quietly wrong:

    - Call ``get_event_taxonomy`` before any aggregate over ``event_type`` — it explains all
      30+ type/subtype combinations and gives each a ``direction``.
    - Aggregate on ``direction`` rather than ``event_type``. Every ``informational`` row is
      neutral: those are annotations whose value arrives as a separate real event, so
      including them double counts MEV and block-production rewards.
    - For "what did I earn" questions filter on ``event_group = 'income'``, not on
      ``event_type``. ``event_type = 'staking'`` spans both rewards (group ``income``) and
      principal coming back out of a stake (group ``staking``), and both are direction
      ``in`` — so summing the event type counts unstaked principal as earnings, which on an
      account with validator exits is far larger than the income itself.
    - ``amount`` is a decimal string — do arithmetic on ``amount_float``. But it is in each
      row's own asset, so only sum it per-asset; for money questions use ``value``, which
      exists only after refreshing with ``include_values=true``.
    - ``timestamp`` is in **milliseconds**; the ``datetime`` and ``year`` columns are derived
      from it, so filter on those instead of doing unix math.
    - One trade is several rows sharing a group (spend, receive, fee — each in a different
      asset), ordered by ``sequence_index``. Self-join on ``group_identifier_hash`` to see
      both sides; never sum across the legs.
    - Identifier columns arrive as ``<col>_hash`` holding ``anon_…`` values. They are stable
      within this session, so joining and grouping on them works, but they are not reversible
      and not stable across sessions — never quote one to the user as if it were an address.
    - ``value`` is denominated in ``source.value_currency`` from the refresh result, not
      necessarily USD.

    ``get_event_taxonomy`` carries worked queries for the common questions under ``recipes``.
    """
    return await asyncio.to_thread(
        get_analytics_session().query_sql,
        sql=sql,
        max_rows=max_rows,
    )
