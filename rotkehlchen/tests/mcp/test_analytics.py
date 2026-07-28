import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any

import pandas as pd
import pytest

from rotkehlchen.mcp import analytics
from rotkehlchen.mcp.analytics import (
    AnalyticsScope,
    AnalyticsSession,
    TableData,
    _flatten,
    _sanitize_row,
    _validate_sql,
)
from rotkehlchen.mcp.backend import configure_backend

ADDRESS = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
TX_HASH = '0x' + 'ab' * 32


class BlockingTableLoader:
    def __init__(self, started: Event, proceed: Event) -> None:
        self.started = started
        self.proceed = proceed

    def __call__(self, scope: AnalyticsScope) -> TableData:
        self.started.set()
        assert self.proceed.wait(timeout=5)
        return TableData(
            frame=pd.DataFrame([{'asset': 'BTC', 'amount_float': 2.0}]),
            source={'privacy_mode': scope.privacy_mode},
        )


class OrderedTableLoader:
    def __init__(self, started: Event, proceed: Event) -> None:
        self.started = started
        self.proceed = proceed

    def __call__(self, scope: AnalyticsScope) -> TableData:
        if scope.from_timestamp == 1:
            self.started.set()
            assert self.proceed.wait(timeout=5)
            asset = 'OLD'
        else:
            asset = 'NEW'
        return TableData(
            frame=pd.DataFrame([{'asset': asset}]),
            source={'privacy_mode': scope.privacy_mode},
        )


def test_flatten_should_recurse_and_add_float_companions() -> None:
    row = _flatten({
        'identifier': 1,
        'amount': '1.5',
        'extra_data': {'address': ADDRESS, 'depth': 2},
    })
    assert row == {
        'identifier': 1,
        'amount': '1.5',
        'amount_float': 1.5,
        'extra_data_address': ADDRESS,
        'extra_data_depth': 2,
    }


def test_sanitize_should_fail_closed_on_unknown_string_columns() -> None:
    """The crux of the design: a column we have never classified must NOT leak its value.

    ``ens_name`` and ``memo`` are neither allowlisted nor address-shaped, so a naive
    regex-only filter would pass them straight through. Fail-closed hashing must hide them.
    """
    sanitized = _sanitize_row(
        {
            'amount': '1.5',          # allowlisted -> kept verbatim (+ float companion)
            'amount_float': 1.5,
            'ens_name': 'vitalik.eth',  # unknown string -> must be hidden
            'memo': 'pay rent to bob',  # unknown string -> must be hidden
            'sequence_index': 3,        # allowlisted
            'random_count': 7,          # unknown int -> safe analytic payload, kept
        },
        privacy_mode='balanced',
    )
    assert sanitized['amount'] == '1.5'
    assert sanitized['sequence_index'] == 3
    assert sanitized['random_count'] == 7
    # the unknown strings never appear verbatim, only as opaque session hashes
    assert 'ens_name' not in sanitized
    assert 'memo' not in sanitized
    assert sanitized['ens_name_hash'].startswith('anon_')
    assert sanitized['memo_hash'].startswith('anon_')
    assert 'vitalik.eth' not in str(sanitized)
    assert 'bob' not in str(sanitized)


def test_sanitize_should_hash_identifiers_and_redact_notes() -> None:
    sanitized = _sanitize_row(
        {'address': ADDRESS, 'group_identifier': TX_HASH, 'notes': 'Burned ETH for gas'},
        privacy_mode='balanced',
    )
    assert ADDRESS not in str(sanitized)
    assert TX_HASH not in str(sanitized)
    assert sanitized['address_hash'].startswith('anon_')
    assert sanitized['group_identifier_hash'].startswith('anon_')
    assert sanitized['notes'] == analytics.REDACTED_TEXT
    assert sanitized['has_notes'] is True


def test_sanitize_balanced_keeps_named_label_but_strict_hashes_it() -> None:
    row = {'location_label': 'Kraken main', 'label': 'my tag'}
    balanced = _sanitize_row(row, privacy_mode='balanced')
    # a human-friendly account name (not address-shaped) stays readable in balanced mode
    assert balanced['location_label'] == 'Kraken main'
    # but an address-shaped location_label is hashed even in balanced mode
    assert 'location_label' not in _sanitize_row({'location_label': ADDRESS}, 'balanced')

    strict = _sanitize_row(row, privacy_mode='strict')
    assert 'location_label' not in strict
    assert strict['location_label_hash'].startswith('anon_')
    assert 'label' not in strict  # user-authored label is an identifier in strict mode


def test_sanitize_raw_passes_everything_through() -> None:
    row = {'address': ADDRESS, 'notes': 'secret', 'ens_name': 'vitalik.eth'}
    assert _sanitize_row(row, privacy_mode='raw') == row


def test_hash_is_stable_within_session_for_grouping() -> None:
    first = _sanitize_row({'address': ADDRESS}, 'balanced')['address_hash']
    second = _sanitize_row({'address': ADDRESS}, 'balanced')['address_hash']
    assert first == second  # GROUP BY / JOIN on the hash works across rows
    other = _sanitize_row({'address': TX_HASH}, 'balanced')['address_hash']
    assert first != other


@pytest.mark.parametrize(('sql', 'valid'), [
    ('select * from history_events', True),
    ('WITH t as (select 1) select * from t', True),
    ('delete from history_events', False),
    ('drop table history_events', False),
    ('select 1; select 2', False),
    ('update history_events set amount = 0', False),
])
def test_validate_sql(sql: str, valid: bool) -> None:
    assert (_validate_sql(sql) is None) is valid


def _mock_history_pages(monkeypatch, entries: list[dict[str, Any]]) -> None:
    def fake_page(limit, offset, **kwargs):
        page = entries[offset:offset + limit]
        return {
            'entries': page,
            'entries_found': len(entries),
            'entries_total': len(entries),
            'entries_limit': -1,
        }
    monkeypatch.setattr(analytics, 'query_history_events_page', fake_page)


def test_session_refresh_then_query_sql_roundtrip(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '2', 'event_type': 'spend', 'notes': 'a'},
        {'identifier': 2, 'asset': 'ETH', 'amount': '3', 'event_type': 'spend', 'notes': 'b'},
        {'identifier': 3, 'asset': 'BTC', 'amount': '1', 'event_type': 'receive'},
    ])
    session = AnalyticsSession()

    refreshed = session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                                include_ignored_assets=False)
    assert refreshed['errors'] == {}
    assert refreshed['tables']['history_events']['rows'] == 3

    result = session.query_sql(
        'select asset, sum(amount_float) as total from history_events group by asset '
        'order by asset',
        max_rows=500,
    )
    assert result['columns'] == ['asset', 'total']
    assert result['rows'] == [
        {'asset': 'BTC', 'total': 1.0},
        {'asset': 'ETH', 'total': 5.0},
    ]
    assert result['result_truncated'] is False


def test_session_should_support_cross_thread_refresh_and_query(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '2', 'event_type': 'spend'},
    ])
    session = AnalyticsSession()

    with ThreadPoolExecutor(max_workers=1) as executor:
        refreshed = executor.submit(
            session.refresh,
            tables=None,
            from_timestamp=0,
            to_timestamp=0,
            include_ignored_assets=False,
        ).result()
        result = executor.submit(
            session.query_sql,
            'select count(*) as count from history_events',
            10,
        ).result()

    assert refreshed['errors'] == {}
    assert result['rows'] == [{'count': 1}]


def test_refresh_should_load_without_blocking_queries(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'event_type': 'receive'},
    ])
    session = AnalyticsSession()
    assert session.refresh(
        tables=None,
        from_timestamp=0,
        to_timestamp=0,
        include_ignored_assets=False,
    )['errors'] == {}

    started = Event()
    proceed = Event()
    monkeypatch.setitem(
        analytics.TABLE_LOADERS,
        'history_events',
        BlockingTableLoader(started=started, proceed=proceed),
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        refresh_future = executor.submit(
            session.refresh,
            tables=None,
            from_timestamp=0,
            to_timestamp=0,
            include_ignored_assets=False,
        )
        assert started.wait(timeout=5)
        query_future = executor.submit(
            session.query_sql,
            'select asset, amount_float from history_events',
            10,
        )
        try:
            assert query_future.result(timeout=5)['rows'] == [
                {'asset': 'ETH', 'amount_float': 1.0},
            ]
        finally:
            proceed.set()

        assert refresh_future.result(timeout=5)['errors'] == {}

    assert session.query_sql(
        'select asset, amount_float from history_events',
        max_rows=10,
    )['rows'] == [{'asset': 'BTC', 'amount_float': 2.0}]


def test_overlapping_refreshes_should_not_publish_out_of_order(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    started = Event()
    proceed = Event()
    monkeypatch.setitem(
        analytics.TABLE_LOADERS,
        'history_events',
        OrderedTableLoader(started=started, proceed=proceed),
    )
    session = AnalyticsSession()

    with ThreadPoolExecutor(max_workers=2) as executor:
        old_refresh = executor.submit(
            session.refresh,
            tables=None,
            from_timestamp=1,
            to_timestamp=0,
            include_ignored_assets=False,
        )
        assert started.wait(timeout=5)
        new_refresh = executor.submit(
            session.refresh,
            tables=None,
            from_timestamp=2,
            to_timestamp=0,
            include_ignored_assets=False,
        )
        proceed.set()
        assert old_refresh.result(timeout=5)['errors'] == {}
        assert new_refresh.result(timeout=5)['errors'] == {}

    assert session.query_sql(
        'select asset from history_events',
        max_rows=10,
    )['rows'] == [{'asset': 'NEW'}]


def test_history_events_promote_entry_and_redact_auto_notes(monkeypatch) -> None:
    """The API wraps fields in an ``entry`` envelope; columns must read as ``timestamp``/
    ``location`` (not ``entry_timestamp``), and ``auto_notes`` must be redacted, not raw.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {
            'entry': {
                'timestamp': 1614556800000,
                'location': 'ethereum',
                'asset': 'ETH',
                'amount': '1.5',
                'auto_notes': f'Send 1.5 ETH to {ADDRESS}',
            },
            'has_ignored_assets': False,
        },
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)

    columns = session.describe_table('history_events')['columns']
    names = {column['name'] for column in columns}
    assert {'timestamp', 'location', 'asset', 'amount'} <= names  # promoted, no entry_ prefix
    assert 'entry_timestamp' not in names
    assert 'auto_notes' in names and 'has_auto_notes' in names
    # readable date columns are derived so the LLM can filter without unix math
    assert {'year', 'datetime'} <= names
    row = session.query_sql('select * from history_events', max_rows=10)['rows'][0]
    assert row['year'] == 2021  # 1614556800000 ms -> 2021-03-01
    assert row['datetime'] == '2021-03-01T00:00:00Z'
    # the address embedded in auto_notes never leaks
    assert row['auto_notes'] == analytics.REDACTED_TEXT
    assert ADDRESS not in str(row)


def test_refresh_accepts_millisecond_timestamps(monkeypatch) -> None:
    """An LLM passing ms (the unit of the timestamp column) must not silently load 0 rows:
    ms bounds are normalized to the seconds the backend filter expects.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    captured: dict[str, Any] = {}

    def fake_page(limit, offset, from_timestamp=None, to_timestamp=None, **kwargs):
        captured['from_timestamp'] = from_timestamp
        captured['to_timestamp'] = to_timestamp
        return {'entries': [], 'entries_found': 0, 'entries_total': 0, 'entries_limit': -1}
    monkeypatch.setattr(analytics, 'query_history_events_page', fake_page)

    AnalyticsSession().refresh(
        tables=None,
        from_timestamp=1709423608000,  # ms -> must become seconds
        to_timestamp=1735689600,       # already seconds -> unchanged
        include_ignored_assets=False,
    )
    assert captured['from_timestamp'] == 1709423608
    assert captured['to_timestamp'] == 1735689600


def test_load_is_uncapped_by_default_and_respects_max_events(monkeypatch) -> None:
    """Complete data by default; --max-events only caps when explicitly set."""
    entries = [
        {'identifier': i, 'asset': 'ETH', 'amount': str(i), 'event_type': 'spend'}
        for i in range(5)
    ]
    _mock_history_pages(monkeypatch, entries)

    configure_backend(base_url='http://backend/api/1', timeout=5)  # max_events defaults to None
    full = AnalyticsSession().refresh(tables=None, from_timestamp=0, to_timestamp=0,
                                      include_ignored_assets=False)
    assert full['tables']['history_events']['rows'] == 5
    assert full['tables']['history_events']['source']['cache_truncated'] is False

    configure_backend(base_url='http://backend/api/1', timeout=5, max_events=3)
    capped = AnalyticsSession().refresh(tables=None, from_timestamp=0, to_timestamp=0,
                                        include_ignored_assets=False)
    assert capped['tables']['history_events']['rows'] == 3
    assert capped['tables']['history_events']['source']['cache_truncated'] is True


def _mock_prices(monkeypatch, prices: dict[str, dict[int, str]], currency: str = 'EUR') -> list:
    """Mock the settings + historical-price backends, recording every price call made."""
    calls: list[dict[str, Any]] = []

    def fake_prices(asset_timestamps, target_asset, max_seconds_distance):
        calls.append({
            'pairs': list(asset_timestamps),
            'target_asset': target_asset,
            'max_seconds_distance': max_seconds_distance,
        })
        assets: dict[str, dict[str, str]] = {}
        for asset, timestamp in asset_timestamps:
            if (price := prices.get(asset, {}).get(timestamp)) is not None:
                # both levels come back as strings over JSON, as the real endpoint does
                assets.setdefault(asset, {})[str(timestamp)] = price
        return {'assets': assets, 'target_asset': target_asset}

    monkeypatch.setattr(analytics, 'query_settings', lambda: {'main_currency': currency})
    monkeypatch.setattr(analytics, 'query_historical_prices', fake_prices)
    return calls


def _valued_event(identifier: int, asset: str, amount: str, timestamp: int) -> dict[str, Any]:
    return {
        'identifier': identifier,
        'asset': asset,
        'amount': amount,
        'timestamp': timestamp,
        'event_type': 'spend',
    }


def test_include_values_off_should_not_query_prices(monkeypatch) -> None:
    """Valuation costs minutes on a real history, so it must never happen implicitly."""
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [_valued_event(1, 'ETH', '2', 1614556800000)])
    calls = _mock_prices(monkeypatch, {'ETH': {1614556800: '1500'}})

    session = AnalyticsSession()
    loaded = session.refresh(
        tables=None,
        from_timestamp=0,
        to_timestamp=0,
        include_ignored_assets=False,
    )['tables']['history_events']

    assert calls == []
    assert 'value_currency' not in loaded['source']
    names = {column['name'] for column in session.describe_table('history_events')['columns']}
    assert names.isdisjoint({'value', 'price', 'price_missing'})


def test_include_values_should_multiply_amount_by_cached_price(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        _valued_event(1, 'ETH', '2', 1614556800000),    # priced: 2 * 1500
        _valued_event(2, 'BTC', '0.5', 1614556800000),  # priced: 0.5 * 40000
        _valued_event(3, 'DOGE', '100', 1614556800000),  # no cached price
    ])
    calls = _mock_prices(monkeypatch, {
        'ETH': {1614556800: '1500'},
        'BTC': {1614556800: '40000'},
    })
    session = AnalyticsSession()
    loaded = session.refresh(
        tables=None,
        from_timestamp=0,
        to_timestamp=0,
        include_ignored_assets=False,
        include_values=True,
    )['tables']['history_events']

    assert loaded['source']['value_currency'] == 'EUR'
    assert loaded['source']['priced_rows'] == 2
    assert loaded['source']['unpriced_rows'] == 1
    assert loaded['source']['lookup_count'] == 3
    # only_cache_period must always be sent, so no remote oracle fetch can be triggered
    assert all(call['max_seconds_distance'] == 3600 for call in calls)
    assert all(call['target_asset'] == 'EUR' for call in calls)

    rows = session.query_sql(
        'select asset, value, price, price_missing from history_events order by asset',
        max_rows=10,
    )['rows']
    assert rows == [
        {'asset': 'BTC', 'value': 20000.0, 'price': 40000.0, 'price_missing': 0},
        {'asset': 'DOGE', 'value': None, 'price': None, 'price_missing': 1},
        {'asset': 'ETH', 'value': 3000.0, 'price': 1500.0, 'price_missing': 0},
    ]


def test_unpriced_events_should_be_null_never_zero(monkeypatch) -> None:
    """A 0 would silently understate every total an agent sums over ``value``."""
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [_valued_event(1, 'DOGE', '100', 1614556800000)])
    _mock_prices(monkeypatch, {})
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                    include_ignored_assets=False, include_values=True)

    assert session.query_sql(
        'select sum(value) as total, count(value) as priced from history_events',
        max_rows=10,
    )['rows'] == [{'total': None, 'priced': 0}]


def test_null_results_should_stay_json_serializable(monkeypatch) -> None:
    """A NULL in a numeric result column must reach the agent as ``null``. Reading results
    back through a DataFrame turned it into NaN, which ``json.dumps`` emits as a bare ``NaN``
    token -- invalid JSON, so the whole tool response fails to parse on the client.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        _valued_event(1, 'ETH', '2', 1614556800000),
        _valued_event(2, 'DOGE', '100', 1614556800000),
    ])
    _mock_prices(monkeypatch, {'ETH': {1614556800: '1500'}})
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                    include_ignored_assets=False, include_values=True)

    result = session.query_sql('select asset, value from history_events order by asset', 10)
    assert result['rows'] == [{'asset': 'DOGE', 'value': None}, {'asset': 'ETH', 'value': 3000.0}]
    assert 'NaN' not in json.dumps(result)  # strict JSON has no NaN literal


def test_price_lookups_should_dedupe_into_hour_buckets(monkeypatch) -> None:
    """100 events in one asset-hour cost exactly one lookup, not 100."""
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        # spread across one hour: 1614556800000 is exactly 2021-03-01T00:00:00Z
        _valued_event(i, 'ETH', '1', 1614556800000 + i * 30_000) for i in range(100)
    ])
    calls = _mock_prices(monkeypatch, {'ETH': {1614556800: '1500'}})
    loaded = AnalyticsSession().refresh(
        tables=None,
        from_timestamp=0,
        to_timestamp=0,
        include_ignored_assets=False,
        include_values=True,
    )['tables']['history_events']

    assert len(calls) == 1
    assert calls[0]['pairs'] == [('ETH', 1614556800)]
    assert loaded['source']['lookup_count'] == 1
    assert loaded['source']['priced_rows'] == 100  # all 100 rows still get the bucket's price


def test_price_lookups_should_chunk_at_500_pairs(monkeypatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        # 1200 distinct asset-hours -> 500 + 500 + 200
        _valued_event(i, f'ASSET{i}', '1', 1614556800000 + i * 3_600_000) for i in range(1200)
    ])
    calls = _mock_prices(monkeypatch, {})
    loaded = AnalyticsSession().refresh(
        tables=None,
        from_timestamp=0,
        to_timestamp=0,
        include_ignored_assets=False,
        include_values=True,
    )['tables']['history_events']

    assert [len(call['pairs']) for call in calls] == [500, 500, 200]
    assert loaded['source']['lookup_count'] == 1200


def test_valuation_should_not_block_queries(monkeypatch) -> None:
    """Price resolution takes minutes; it must run outside the connection lock so the
    previous snapshot stays queryable, exactly like the event paging above it.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [_valued_event(1, 'ETH', '2', 1614556800000)])
    session = AnalyticsSession()
    assert session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                           include_ignored_assets=False)['errors'] == {}

    started, proceed = Event(), Event()

    def blocking_prices(asset_timestamps, target_asset, max_seconds_distance):
        started.set()
        assert proceed.wait(timeout=5)
        return {'assets': {'ETH': {'1614556800': '1500'}}, 'target_asset': target_asset}

    monkeypatch.setattr(analytics, 'query_settings', lambda: {'main_currency': 'EUR'})
    monkeypatch.setattr(analytics, 'query_historical_prices', blocking_prices)

    with ThreadPoolExecutor(max_workers=2) as executor:
        refresh_future = executor.submit(
            session.refresh,
            tables=None,
            from_timestamp=0,
            to_timestamp=0,
            include_ignored_assets=False,
            include_values=True,
        )
        assert started.wait(timeout=5)
        query_future = executor.submit(
            session.query_sql,
            'select count(*) as count from history_events',
            10,
        )
        try:  # the un-valued snapshot answers while valuation is still in flight
            assert query_future.result(timeout=5)['rows'] == [{'count': 1}]
        finally:
            proceed.set()
        assert refresh_future.result(timeout=5)['errors'] == {}

    assert session.query_sql('select value from history_events', max_rows=10)['rows'] == [
        {'value': 3000.0},
    ]


def test_query_sql_without_loaded_tables_errors() -> None:
    assert AnalyticsSession().query_sql('select 1', max_rows=10)['error']['type'] == (
        'no_tables_loaded'
    )


def test_describe_unknown_table_errors() -> None:
    assert AnalyticsSession().describe_table('nope')['error']['type'] == 'unknown_table'
