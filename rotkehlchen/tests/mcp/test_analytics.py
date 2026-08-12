import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any
from unittest.mock import Mock

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
    sync_privacy_mode,
)
from rotkehlchen.mcp.backend import configure_backend, get_backend_config, set_privacy_mode
from rotkehlchen.mcp.taxonomy import RECIPES

ADDRESS = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
TX_HASH = '0x' + 'ab' * 32


def test_sync_privacy_mode_should_clear_data_only_when_mode_changes(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    session = analytics.get_analytics_session()
    clear = Mock(wraps=session.clear)
    monkeypatch.setattr(session, 'clear', clear)
    monkeypatch.setattr(analytics, 'query_settings', lambda: {'mcp_privacy_mode': 'strict'})

    assert sync_privacy_mode() is session
    assert get_backend_config().privacy_mode == 'strict'
    clear.assert_called_once_with()

    sync_privacy_mode()
    clear.assert_called_once_with()


def test_sync_privacy_mode_should_reject_invalid_backend_value(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(analytics, 'query_settings', lambda: {'mcp_privacy_mode': 'invalid'})

    with pytest.raises(analytics.BackendQueryError, match='invalid MCP privacy mode'):
        sync_privacy_mode()


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


class HistoricalPricesMock:
    def __init__(self, prices: dict[str, dict[int, str]]) -> None:
        self.prices = prices
        self.calls: list[dict[str, Any]] = []

    def __call__(
            self,
            asset_timestamps: list[tuple[str, int]],
            target_asset: str,
            max_seconds_distance: int,
    ) -> dict[str, Any]:
        self.calls.append({
            'pairs': list(asset_timestamps),
            'target_asset': target_asset,
            'max_seconds_distance': max_seconds_distance,
        })
        assets: dict[str, dict[str, str]] = {}
        for asset, timestamp in asset_timestamps:
            if (price := self.prices.get(asset, {}).get(timestamp)) is not None:
                # both levels come back as strings over JSON, as the real endpoint does
                assets.setdefault(asset, {})[str(timestamp)] = price
        return {'assets': assets, 'target_asset': target_asset}


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


def test_sanitize_balanced_keeps_venue_label_but_strict_hashes_it() -> None:
    row = {'location_label': 'kraken', 'label': 'my tag'}
    # a bare venue name carries no user-authored text, so it stays readable in balanced mode
    assert _sanitize_row(row, privacy_mode='balanced')['location_label'] == 'kraken'
    # capitalisation of the venue name is not user information either
    assert _sanitize_row({'location_label': 'Kraken'}, 'balanced')['location_label'] == 'Kraken'
    for user_assigned in ('Coinbase 1', 'Kraken main', ADDRESS):
        # anything the user typed themselves is hashed only, even in balanced mode
        assert 'location_label' not in (
            sanitized := _sanitize_row({'location_label': user_assigned}, 'balanced')
        )
        assert sanitized['location_label_hash'].startswith('anon_')

    strict = _sanitize_row(row, privacy_mode='strict')
    assert 'location_label' not in strict  # not even the venue name in strict mode
    assert strict['location_label_hash'].startswith('anon_')
    assert 'label' not in strict  # user-authored label is an identifier in strict mode


@pytest.mark.parametrize('identifier', [
    ADDRESS,                                        # EVM address
    TX_HASH,                                        # EVM tx hash
    'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',   # bech32 BTC
    '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',           # base58 BTC
    '7EYnhQoR9YM3N7UoaKRoA44Uy8JeaZV3qyouov87awMs',  # base58 Solana
])
def test_generated_notes_should_never_carry_an_identifier(identifier: str) -> None:
    """The templates interpolate no address today, but an asset *name* is attacker
    controlled on a scam token, so the scrub is what keeps that true rather than assumed.
    """
    balanced = _sanitize_row(
        {'auto_notes': f'Receive 1.0 {identifier} after a swap in kraken'},
        privacy_mode='balanced',
    )
    assert identifier not in balanced['auto_notes']
    assert 'anon_' in balanced['auto_notes']
    assert balanced['auto_notes'].startswith('Receive 1.0 ')  # still readable
    # strict keeps redacting outright
    assert _sanitize_row(
        {'auto_notes': f'Receive 1.0 {identifier} after a swap in kraken'},
        privacy_mode='strict',
    )['auto_notes'] == analytics.REDACTED_TEXT


def test_generated_notes_readable_but_user_notes_still_redacted() -> None:
    """``auto_notes`` is template-generated and safe; ``user_notes`` is decoder-written *and*
    user-editable, so its mixed provenance keeps it redacted in every non-raw mode.
    """
    row = {
        'auto_notes': 'Deposit 5 ETH to kraken',
        'user_notes': f'Burn 0.00013 XDAI for gas at {ADDRESS}',
        'notes': 'my private note',
    }
    for privacy_mode in ('balanced', 'strict'):
        sanitized = _sanitize_row(row, privacy_mode=privacy_mode)
        assert sanitized['user_notes'] == analytics.REDACTED_TEXT
        assert sanitized['notes'] == analytics.REDACTED_TEXT
        assert sanitized['has_auto_notes'] is True
        assert ADDRESS not in str(sanitized)

    assert _sanitize_row(row, 'balanced')['auto_notes'] == 'Deposit 5 ETH to kraken'
    assert _sanitize_row(row, 'strict')['auto_notes'] == analytics.REDACTED_TEXT


def test_empty_generated_notes_stay_null() -> None:
    sanitized = _sanitize_row({'auto_notes': ''}, privacy_mode='balanced')
    assert sanitized['auto_notes'] is None
    assert sanitized['has_auto_notes'] is False


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
    # read-only scalar functions and literals must not be mistaken for writes
    ("select replace(counterparty, '-', ' ') from history_events limit 1", True),
    ("select * from history_events where auto_notes like '%update%'", True),
    ("select * from history_events where auto_notes = 'a; drop table x'", True),
    ('select "update" from history_events', True),
    # ... while real writes stay rejected
    ('insert into history_events values (1)', False),
    ('select 1; insert into history_events values (1)', False),
])
def test_validate_sql(sql: str, valid: bool) -> None:
    assert (_validate_sql(sql) is None) is valid


def _mock_history_pages(monkeypatch: pytest.MonkeyPatch, entries: list[Any]) -> None:
    """``entries`` may hold plain event dicts or, as the real endpoint returns for grouped
    swaps and matched movements, sub-lists of them.
    """
    def fake_page(limit: int, offset: int, **kwargs: Any) -> dict[str, Any]:
        page = entries[offset:offset + limit]
        return {
            'entries': page,
            'entries_found': len(entries),
            'entries_total': len(entries),
            'entries_limit': -1,
        }
    monkeypatch.setattr(analytics, 'query_history_events_page', fake_page)


def test_session_refresh_then_query_sql_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_session_should_support_cross_thread_refresh_and_query(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_refresh_should_load_without_blocking_queries(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_refresh_should_not_publish_data_if_privacy_mode_changes(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='raw')
    started = Event()
    proceed = Event()
    monkeypatch.setitem(
        analytics.TABLE_LOADERS,
        'history_events',
        BlockingTableLoader(started=started, proceed=proceed),
    )
    session = AnalyticsSession()

    with ThreadPoolExecutor(max_workers=1) as executor:
        refresh_future = executor.submit(
            session.refresh,
            tables=None,
            from_timestamp=0,
            to_timestamp=0,
            include_ignored_assets=False,
        )
        assert started.wait(timeout=5)
        assert set_privacy_mode('strict') is True
        proceed.set()
        result = refresh_future.result(timeout=5)

    assert result['tables'] == {}
    assert result['errors'] == {
        'privacy_mode': 'Privacy mode changed during refresh; retry it',
    }
    assert session.query_sql('select * from history_events', 10)['error']['type'] == (
        'no_tables_loaded'
    )


def test_overlapping_refreshes_should_not_publish_out_of_order(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_history_events_promote_entry_and_scrub_auto_notes(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The API wraps fields in an ``entry`` envelope; columns must read as ``timestamp``/
    ``location`` (not ``entry_timestamp``), and ``auto_notes`` stays readable in balanced
    mode with any embedded identifier scrubbed.
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
    # the description stays readable, but the address embedded in it never leaks
    assert row['auto_notes'].startswith('Send 1.5 ETH to anon_')
    assert ADDRESS not in str(row)


def test_refresh_accepts_millisecond_timestamps(monkeypatch: pytest.MonkeyPatch) -> None:
    """An LLM passing ms (the unit of the timestamp column) must not silently load 0 rows:
    ms bounds are normalized to the seconds the backend filter expects.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    captured: dict[str, Any] = {}

    def fake_page(
            limit: int,
            offset: int,
            from_timestamp: int | None = None,
            to_timestamp: int | None = None,
            **kwargs: Any,
    ) -> dict[str, Any]:
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


def test_load_is_uncapped_by_default_and_respects_max_events(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def _mock_prices(
        monkeypatch: pytest.MonkeyPatch,
        prices: dict[str, dict[int, str]],
        currency: str = 'EUR',
) -> list[dict[str, Any]]:
    """Mock the settings + historical-price backends, recording every price call made."""
    prices_mock = HistoricalPricesMock(prices=prices)
    monkeypatch.setattr(analytics, 'query_settings', lambda: {'main_currency': currency})
    monkeypatch.setattr(analytics, 'query_historical_prices', prices_mock)
    return prices_mock.calls


def _valued_event(identifier: int, asset: str, amount: str, timestamp: int) -> dict[str, Any]:
    return {
        'identifier': identifier,
        'asset': asset,
        'amount': amount,
        'timestamp': timestamp,
        'event_type': 'spend',
    }


def test_include_values_off_should_not_query_prices(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_include_values_should_multiply_amount_by_cached_price(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    assert all(
        call['max_seconds_distance'] == analytics.PRICE_LOOKUP_RADIUS_SECONDS for call in calls
    )
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


def test_unpriced_events_should_be_null_never_zero(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_null_results_should_stay_json_serializable(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_price_lookups_should_dedupe_into_hour_buckets(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_price_lookups_should_chunk_at_500_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_valuation_should_not_block_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    """Price resolution takes minutes; it must run outside the connection lock so the
    previous snapshot stays queryable, exactly like the event paging above it.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [_valued_event(1, 'ETH', '2', 1614556800000)])
    session = AnalyticsSession()
    assert session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                           include_ignored_assets=False)['errors'] == {}

    started, proceed = Event(), Event()

    def blocking_prices(
            asset_timestamps: list[tuple[str, int]],
            target_asset: str,
            max_seconds_distance: int,
    ) -> dict[str, Any]:
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


def test_grouped_sublist_entries_should_not_be_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without aggregate_by_group_ids the API nests each EVM/Solana swap and each matched
    asset movement in a sub-list, so a page mixes dicts with lists of dicts. Keeping only the
    dicts silently lost every on-chain swap -- exactly the trades an agent asks about.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    swap_legs = [
        {'entry': {'identifier': 2, 'asset': 'ETH', 'amount': '1', 'event_subtype': 'spend',
                   'group_identifier': '0xswap', 'sequence_index': 0}},
        {'entry': {'identifier': 3, 'asset': 'USDC', 'amount': '3000',
                   'event_subtype': 'receive', 'group_identifier': '0xswap',
                   'sequence_index': 1}},
    ]
    _mock_history_pages(monkeypatch, [
        {'entry': {'identifier': 1, 'asset': 'BTC', 'amount': '1', 'event_subtype': 'receive'}},
        swap_legs,  # a grouped sub-list, as the endpoint really returns it
    ])
    session = AnalyticsSession()
    loaded = session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                             include_ignored_assets=False)

    assert loaded['tables']['history_events']['rows'] == 3  # not 1
    assert session.query_sql(
        'select asset from history_events order by asset',
        max_rows=10,
    )['rows'] == [{'asset': 'BTC'}, {'asset': 'ETH'}, {'asset': 'USDC'}]


def test_aggregate_by_group_ids_should_be_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    captured: list[Any] = []

    def fake_page(
            limit: int,
            offset: int,
            aggregate_by_group_ids: bool = False,
            **kwargs: Any,
    ) -> dict[str, Any]:
        captured.append(aggregate_by_group_ids)
        return {'entries': [] if offset else [
            {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'grouped_events_num': 3},
        ], 'entries_found': 1, 'entries_total': 1, 'entries_limit': -1}

    monkeypatch.setattr(analytics, 'query_history_events_page', fake_page)

    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                    include_ignored_assets=False)
    assert captured == [False]  # default request is unchanged

    captured.clear()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                    include_ignored_assets=False, aggregate_by_group_ids=True)
    assert captured == [True]
    # the count survives flattening and is queryable
    assert session.query_sql(
        'select grouped_events_num from history_events',
        max_rows=10,
    )['rows'] == [{'grouped_events_num': 3}]


def _paged_backend(monkeypatch: pytest.MonkeyPatch, pages: list[list[dict[str, Any]]], entries_found: int) -> None:  # noqa: E501
    """Serve pre-baked pages by offset, so a page can be empty mid-range."""
    def fake_page(limit: int, offset: int, **kwargs: Any) -> dict[str, Any]:
        index = offset // limit
        return {
            'entries': pages[index] if index < len(pages) else [],
            'entries_found': entries_found,
            'entries_total': entries_found,
            'entries_limit': -1,
        }
    monkeypatch.setattr(analytics, 'query_history_events_page', fake_page)
    monkeypatch.setattr(analytics, 'PAGE_SIZE', 2)


def _event(identifier: int) -> dict[str, Any]:
    return {'identifier': identifier, 'asset': 'ETH', 'amount': '1', 'event_type': 'spend'}


def test_complete_load_should_report_completeness(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _paged_backend(monkeypatch, [[_event(1), _event(2)], [_event(3)]], entries_found=3)

    source = AnalyticsSession().refresh(
        tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False,
    )['tables']['history_events']['source']

    assert source['completeness'] == 'complete'
    assert source['rows_loaded'] == 3
    assert source['backend_metadata']['entries_found'] == 3


def test_empty_middle_page_should_not_end_the_load(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pages come back short and a whole window can filter out, so stopping at the first
    empty page silently truncated the load while still reporting it as complete.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _paged_backend(
        monkeypatch,
        [[_event(1), _event(2)], [], [_event(3), _event(4)]],
        entries_found=6,
    )

    source = AnalyticsSession().refresh(
        tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False,
    )['tables']['history_events']['source']

    assert source['rows_loaded'] == 4  # the events after the empty window are not lost
    assert source['completeness'] == 'complete'


def test_persistently_empty_pages_should_stop_and_say_so(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _paged_backend(monkeypatch, [[_event(1), _event(2)]], entries_found=1000)

    source = AnalyticsSession().refresh(
        tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False,
    )['tables']['history_events']['source']

    assert source['rows_loaded'] == 2
    assert source['completeness'] == 'stopped_early'  # never claim complete coverage


def test_max_events_cap_should_report_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, max_events=3)
    _paged_backend(
        monkeypatch,
        [[_event(1), _event(2)], [_event(3), _event(4)], [_event(5), _event(6)]],
        entries_found=6,
    )

    source = AnalyticsSession().refresh(
        tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False,
    )['tables']['history_events']['source']

    assert source['rows_loaded'] == 3
    assert source['completeness'] == 'truncated_by_max_events'
    assert source['cache_truncated'] is True


def _described(session: AnalyticsSession, table: str = 'history_events') -> dict[str, Any]:
    return {column['name']: column for column in session.describe_table(table)['columns']}


def test_describe_should_report_sqlite_type_beside_pandas_dtype(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pandas dtype is not what SQL sees; reporting it alone misled every query."""
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'event_type': 'spend',
         'auto_notes': 'Deposit 1 ETH to kraken'},
        {'identifier': 2, 'asset': 'BTC', 'amount': '2', 'event_type': 'receive'},
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)
    columns = _described(session)

    assert all(column['sqlite_type'] for column in columns.values())
    assert columns['asset']['sqlite_type'] == 'TEXT'
    # the has_ flag is a real bool filled for the event that lacked the field entirely
    assert columns['has_auto_notes']['dtype'] == 'bool'
    assert session.query_sql(
        'select has_auto_notes, count(*) as count from history_events '
        'group by has_auto_notes order by has_auto_notes',
        max_rows=10,
    )['rows'] == [{'has_auto_notes': 0, 'count': 1}, {'has_auto_notes': 1, 'count': 1}]


def test_describe_should_list_enum_values_and_null_fractions(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'event_type': 'spend'},
        {'identifier': 2, 'asset': 'ETH', 'amount': '2', 'event_type': 'spend'},
        {'identifier': 3, 'asset': 'BTC', 'amount': '3', 'event_type': 'receive',
         'extra_data_cdp_id': None},
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)
    columns = _described(session)

    assert columns['event_type']['distinct_count'] == 2
    assert columns['event_type']['top_values'] == [
        {'value': 'spend', 'rows': 2},
        {'value': 'receive', 'rows': 1},
    ]
    assert columns['asset']['null_fraction'] == 0.0
    # a column that exists but carries nothing is called out rather than looking substantial
    assert columns['extra_data_cdp_id']['all_null'] is True
    assert columns['extra_data_cdp_id']['null_fraction'] == 1.0


def test_describe_should_list_counterparty_values_beyond_the_general_scan_cap(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """describe_table documents counterparty as one of the columns it lists values for, but
    every real account has far more than the general cap, so it never got a listing at all.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': index, 'asset': 'ETH', 'amount': '1', 'event_type': 'spend',
         # one dominant counterparty so the column still reads as an enum, plus a long tail
         # comfortably past MAX_DISTINCT_VALUES_SCANNED
         'counterparty': 'gas' if index % 2 == 0 else f'protocol_{index}'}
        for index in range(160)
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)

    assert (counterparty := _described(session)['counterparty'])['distinct_count'] == 81
    assert counterparty['top_values'][0] == {'value': 'gas', 'rows': 80}
    # the report cap still bounds the payload, so listing more does not make it bigger
    assert len(counterparty['top_values']) == analytics.MAX_DISTINCT_VALUES_REPORTED


def test_describe_should_not_list_values_of_a_column_where_nothing_repeats(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sparse column holding a distinct amount per row is not an enum. Listing its "top
    values" put per-row financial data in what is meant to be a schema summary.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': index, 'asset': 'ETH', 'amount': '1', 'event_type': 'spend',
         'extra_data_amount': f'{index}.38752450{index}'}
        for index in range(28)
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)

    assert (column := _described(session)['extra_data_amount'])['distinct_count'] == 28
    assert 'top_values' not in column  # the count is the useful part; the amounts are not
    # a short domain is still listed even when nothing repeats -- it is the whole vocabulary
    assert _described(session)['event_type']['top_values'] == [{'value': 'spend', 'rows': 28}]


def test_describe_should_never_emit_hashed_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Listing anon_ values would be noise at best and defeats the point at worst."""
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'address': ADDRESS,
         'ens_name': 'vitalik.eth'},
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)
    described = session.describe_table('history_events')
    columns = _described(session)

    assert 'anon_' not in str(described)
    assert columns['address_hash']['hashed'] is True
    assert columns['address_hash']['hashed_reason'] == 'pii'
    assert 'top_values' not in columns['address_hash']
    # a column the allowlist does not know is hashed too, but for a different reason
    assert columns['ens_name_hash']['hashed_reason'] == 'unrecognized'


def test_direction_column_should_use_rotki_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """The serialized event carries no direction, so it is derived locally -- otherwise the
    "aggregate on direction" guidance refers to a column that does not exist.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'mev reward'},
        {'identifier': 2, 'asset': 'ETH', 'amount': '1', 'location': 'ethereum',
         'event_type': 'informational', 'event_subtype': 'mev reward'},
        {'identifier': 3, 'asset': 'ETH', 'amount': '1', 'location': 'ethereum',
         'event_type': 'spend', 'event_subtype': 'fee'},
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)

    assert session.query_sql(
        'select event_type, direction from history_events order by identifier',
        max_rows=10,
    )['rows'] == [
        {'event_type': 'staking', 'direction': 'in'},
        {'event_type': 'informational', 'direction': 'neutral'},  # not counted twice
        {'event_type': 'spend', 'direction': 'out'},
    ]


def test_event_group_should_separate_income_from_returned_principal(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of the column: every row below is event_type "staking" and direction
    "in", so nothing else on the row tells earnings apart from principal coming back.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'reward'},
        {'identifier': 2, 'asset': 'ETH', 'amount': '32', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'remove asset'},
        {'identifier': 3, 'asset': 'ETH', 'amount': '10', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'redeem wrapped'},
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)

    assert session.query_sql(
        'select event_subtype, direction, event_group from history_events order by identifier',
        max_rows=10,
    )['rows'] == [
        {'event_subtype': 'reward', 'direction': 'in', 'event_group': 'income'},
        # an unstake returns principal: direction "in", but not income
        {'event_subtype': 'remove asset', 'direction': 'in', 'event_group': 'staking'},
        # so does an LST redemption -- its earnings are appreciation, not any row here
        {'event_subtype': 'redeem wrapped', 'direction': 'in', 'event_group': 'staking'},
    ]


def test_partial_beacon_withdrawal_should_be_income_but_exit_should_not(
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rotki files both under staking/remove asset, so only is_exit tells them apart. A
    partial withdrawal is a skim of the balance above 32 ETH and therefore pure reward.
    """
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '0.03', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'remove asset',
         'entry_type': 'eth withdrawal event', 'validator_index': 42, 'is_exit': False},
        {'identifier': 2, 'asset': 'ETH', 'amount': '32.1', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'remove asset',
         'entry_type': 'eth withdrawal event', 'validator_index': 42, 'is_exit': True},
        # a non-withdrawal row carries no is_exit at all and must keep its taxonomy group
        {'identifier': 3, 'asset': 'ETH', 'amount': '5', 'location': 'ethereum',
         'event_type': 'staking', 'event_subtype': 'remove asset', 'entry_type': 'evm event'},
    ])
    session = AnalyticsSession()
    session.refresh(tables=None, from_timestamp=0, to_timestamp=0, include_ignored_assets=False)

    assert session.query_sql(
        'select identifier, event_group from history_events order by identifier',
        max_rows=10,
    )['rows'] == [
        {'identifier': 1, 'event_group': 'income'},   # partial withdrawal: reward
        {'identifier': 2, 'event_group': 'staking'},  # full exit: returned principal
        {'identifier': 3, 'event_group': 'staking'},
    ]


def test_unparsable_event_should_not_fail_the_load(monkeypatch: pytest.MonkeyPatch) -> None:
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'identifier': 1, 'asset': 'ETH', 'amount': '1', 'location': 'ethereum',
         'event_type': 'not_a_real_type', 'event_subtype': 'nonsense'},
    ])
    session = AnalyticsSession()
    assert session.refresh(tables=None, from_timestamp=0, to_timestamp=0,
                           include_ignored_assets=False)['errors'] == {}
    assert session.query_sql('select direction, event_group from history_events', 10)['rows'] == [
        {'direction': None, 'event_group': None},
    ]


def test_every_shipped_recipe_should_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    """Doubles as regression coverage: a recipe breaks the moment the schema drifts."""
    configure_backend(base_url='http://backend/api/1', timeout=5, privacy_mode='balanced')
    _mock_history_pages(monkeypatch, [
        {'entry': {'identifier': 1, 'asset': 'ETH', 'amount': '0.01',
                   'timestamp': 1614556800000, 'location': 'ethereum', 'event_type': 'spend',
                   'event_subtype': 'fee', 'counterparty': 'gas', 'sequence_index': 0,
                   'group_identifier': '0xaaa'}},
        {'entry': {'identifier': 2, 'asset': 'ETH', 'amount': '1',
                   'timestamp': 1614556800000, 'location': 'ethereum',
                   'event_type': 'staking', 'event_subtype': 'mev reward',
                   'sequence_index': 0, 'group_identifier': '0xbbb'}},
        {'entry': {'identifier': 3, 'asset': 'ETH', 'amount': '2',
                   'timestamp': 1614556800000, 'location': 'kraken', 'event_type': 'trade',
                   'event_subtype': 'spend', 'sequence_index': 0,
                   'group_identifier': '0xccc'}},
        {'entry': {'identifier': 4, 'asset': 'USDC', 'amount': '6000',
                   'timestamp': 1614556800000, 'location': 'kraken', 'event_type': 'trade',
                   'event_subtype': 'receive', 'sequence_index': 1,
                   'group_identifier': '0xccc'}},
    ])
    _mock_prices(monkeypatch, {'ETH': {1614556800: '1500'}, 'USDC': {1614556800: '1'}})
    monkeypatch.setattr(analytics, 'query_all_balances', lambda refresh, timeout: {
        'assets': {'ETH': {'amount': '3', 'usd_value': '4500'}},
        'liabilities': {},
        'net_value': '4500',
    })
    session = AnalyticsSession()
    assert session.refresh(
        tables=['history_events', 'balances'],
        from_timestamp=0,
        to_timestamp=0,
        include_ignored_assets=False,
        include_values=True,
    )['errors'] == {}

    for recipe in RECIPES:
        result = session.query_sql(recipe['sql'], max_rows=100)
        assert 'error' not in result, f'recipe failed: {recipe["question"]}: {result}'
        assert 'excludes' in recipe and 'requires' in recipe


def test_query_sql_without_loaded_tables_errors() -> None:
    assert AnalyticsSession().query_sql('select 1', max_rows=10)['error']['type'] == (
        'no_tables_loaded'
    )


def test_describe_unknown_table_errors() -> None:
    assert AnalyticsSession().describe_table('nope')['error']['type'] == 'unknown_table'


def test_price_lookup_radius_should_cover_a_full_hour_around_every_bucketed_event() -> None:
    """Timestamps are floored to the hour before being priced, but the backend centres its
    ``BETWEEN queried - distance AND queried + distance`` search on what we send. An equal
    radius therefore searched two hours *behind* an event late in its bucket and barely one
    second ahead of it, missing cached prices minutes later than the event itself.
    """
    latest_offset = analytics.PRICE_TOLERANCE_SECONDS - 1  # the worst case within a bucket
    window_start = -analytics.PRICE_LOOKUP_RADIUS_SECONDS
    window_end = analytics.PRICE_LOOKUP_RADIUS_SECONDS

    # relative to the bucket, the event wants prices from one hour before to one hour after
    assert window_start <= latest_offset - analytics.PRICE_TOLERANCE_SECONDS
    assert window_end >= latest_offset + analytics.PRICE_TOLERANCE_SECONDS
    # and the equal radius the fix replaced could not cover that
    assert latest_offset + analytics.PRICE_TOLERANCE_SECONDS > analytics.PRICE_TOLERANCE_SECONDS
