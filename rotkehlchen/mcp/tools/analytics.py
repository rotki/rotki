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

    Returns the per-table row counts and source metadata, plus the active ``privacy_mode``.
    """
    return await asyncio.to_thread(
        get_analytics_session().refresh,
        tables=tables,
        from_timestamp=from_timestamp,
        to_timestamp=to_timestamp,
        include_ignored_assets=include_ignored_assets,
    )


@register_tool(name='list_tables')
async def list_tables() -> dict[str, Any]:
    """List the analytics tables: which are loaded now, the defaults, and all available."""
    return await asyncio.to_thread(get_analytics_session().list_tables)


@register_tool(name='describe_table')
async def describe_table(table: str) -> dict[str, Any]:
    """Describe a loaded analytics table: its columns (name + dtype), row count and source.

    Use this to discover the schema before writing SQL. Note that identifier columns are
    privacy-filtered: addresses/hashes appear as ``<col>_hash`` (consistent within a
    session so you can still GROUP BY / JOIN on them) and free-text ``notes`` are redacted
    to a ``has_notes`` flag, unless the server was started in ``raw`` privacy mode.
    """
    return await asyncio.to_thread(get_analytics_session().describe_table, table=table)


@register_tool(name='query_sql')
async def query_sql(sql: str, max_rows: int = DEFAULT_MAX_RESULT_ROWS) -> dict[str, Any]:
    """Run a read-only SQL query over the loaded, privacy-filtered analytics tables.

    Polars SQL runs the query, so aggregations, joins, grouping, ordering and window
    functions are all available and computed exactly — use it for the math (sums, cost
    basis candidates, rolling balances, per-asset/per-counterparty rollups, fee totals)
    rather than doing arithmetic yourself. Only a single ``SELECT``/``WITH`` statement is
    allowed; writes and DDL are rejected.

    Call ``refresh_analytics_data`` first to load data, and ``describe_table`` to learn the
    columns. The default table is ``history_events``. ``max_rows`` caps returned rows; the
    result reports ``result_truncated`` and the true ``row_count`` when more matched.
    """
    return await asyncio.to_thread(
        get_analytics_session().query_sql,
        sql=sql,
        max_rows=max_rows,
    )
