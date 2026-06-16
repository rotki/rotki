from typing import Any

import pytest

from rotkehlchen.mcp import analytics
from rotkehlchen.mcp.analytics import (
    AnalyticsSession,
    _flatten,
    _sanitize_row,
    _validate_sql,
)
from rotkehlchen.mcp.backend import configure_backend

ADDRESS = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
TX_HASH = '0x' + 'ab' * 32


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


def test_query_sql_without_loaded_tables_errors() -> None:
    assert AnalyticsSession().query_sql('select 1', max_rows=10)['error']['type'] == (
        'no_tables_loaded'
    )


def test_describe_unknown_table_errors() -> None:
    assert AnalyticsSession().describe_table('nope')['error']['type'] == 'unknown_table'
