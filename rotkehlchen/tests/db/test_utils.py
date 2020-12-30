import pytest

from rotkehlchen.db.utils import form_query_to_filter_timestamps


@pytest.mark.parametrize(
    ('query_in, timestamp_attribute, from_ts, to_ts, expected_query_out, expected_bindings'),
    [
        (
            'SELECT * FROM adex_events',
            'timestamp',
            None,
            None,
            'SELECT * FROM adex_events ORDER BY timestamp ASC;',
            (),
        ),
        (
            'SELECT * FROM adex_events',
            'timestamp',
            1609336000,
            None,
            'SELECT * FROM adex_events WHERE timestamp >= ? ORDER BY timestamp ASC;',
            (1609336000,),
        ),
        (
            'SELECT * FROM adex_events',
            'timestamp',
            None,
            1609336240,
            'SELECT * FROM adex_events WHERE timestamp <= ? ORDER BY timestamp ASC;',
            (1609336240,),
        ),
        (
            'SELECT * FROM adex_events',
            'timestamp',
            1609336000,
            1609336240,
            'SELECT * FROM adex_events WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC;',  # noqa:E501
            (1609336000, 1609336240),
        ),
    ],
)
def test_form_query_to_filter_timestamps(
        query_in,
        timestamp_attribute,
        from_ts,
        to_ts,
        expected_query_out,
        expected_bindings,
):
    query_out, bindings = form_query_to_filter_timestamps(
        query=query_in,
        timestamp_attribute=timestamp_attribute,
        from_ts=from_ts,
        to_ts=to_ts,
    )
    assert query_out == expected_query_out
    assert bindings == expected_bindings
