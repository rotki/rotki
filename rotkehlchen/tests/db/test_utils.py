from typing import Any

import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.db.utils import (
    SingleDBAssetBalance,
    combine_asset_balances,
    form_query_to_filter_timestamps,
    need_cursor,
    need_writable_cursor,
)
from rotkehlchen.fval import FVal


@pytest.mark.parametrize(
    ('query_in, timestamp_attribute, from_ts, to_ts, expected_query_out, expected_bindings'),
    [
        (
            'SELECT * FROM trades',
            'timestamp',
            None,
            None,
            'SELECT * FROM trades ORDER BY timestamp ASC;',
            (),
        ),
        (
            'SELECT * FROM trades',
            'timestamp',
            1609336000,
            None,
            'SELECT * FROM trades WHERE timestamp >= ? ORDER BY timestamp ASC;',
            (1609336000,),
        ),
        (
            'SELECT * FROM trades',
            'timestamp',
            None,
            1609336240,
            'SELECT * FROM trades WHERE timestamp <= ? ORDER BY timestamp ASC;',
            (1609336240,),
        ),
        (
            'SELECT * FROM trades',
            'timestamp',
            1609336000,
            1609336240,
            'SELECT * FROM trades WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC;',  # noqa: E501
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


def _tuple_to_balance(data: tuple) -> SingleDBAssetBalance:
    """Just a convenience function to not write too much"""
    return SingleDBAssetBalance(
        time=data[0],
        amount=FVal(data[1]),
        usd_value=FVal(data[2]),
        category=BalanceType.ASSET,
    )


def test_combine_asset_balances():
    a = [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 1, 1)),
        _tuple_to_balance((3, 1, 1)),
        _tuple_to_balance((4, 1, 1)),
    ]
    assert combine_asset_balances(a) == [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 1, 1)),
        _tuple_to_balance((3, 1, 1)),
        _tuple_to_balance((4, 1, 1)),
    ], 'no common time even failed'

    a = [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 1, 1)),
        _tuple_to_balance((3, 1, 1)),
        _tuple_to_balance((4, 1, 1)),
        _tuple_to_balance((5, 1, 1)),
    ]
    assert combine_asset_balances(a) == [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 1, 1)),
        _tuple_to_balance((3, 1, 1)),
        _tuple_to_balance((4, 1, 1)),
        _tuple_to_balance((5, 1, 1)),
    ], 'no common time odd failed'

    a = [
        _tuple_to_balance((1, 1, 2)),
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 2, 1)),
        _tuple_to_balance((2, 1, 2)),
    ]
    assert combine_asset_balances(a) == [
        _tuple_to_balance((1, 2, 3)),
        _tuple_to_balance((2, 3, 3)),
    ], 'common time even failed'

    a = [
        _tuple_to_balance((1, 1, 2)),
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 2, 1)),
        _tuple_to_balance((2, 1, 2)),
        _tuple_to_balance((3, 2, 2)),
    ]
    assert combine_asset_balances(a) == [
        _tuple_to_balance((1, 2, 3)),
        _tuple_to_balance((2, 3, 3)),
        _tuple_to_balance((3, 2, 2)),
    ], 'common time odd failed'

    a = [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 1, 1)),
        _tuple_to_balance((2, 2, 1)),
        _tuple_to_balance((3, 1, 2)),
    ]
    assert combine_asset_balances(a) == [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 3, 2)),
        _tuple_to_balance((3, 1, 2)),
    ], 'common time appearing outside of pair with even failed'

    a = [
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((1, 1, 1)),
        _tuple_to_balance((2, 2, 1)),
        _tuple_to_balance((3, 1, 2)),
        _tuple_to_balance((3, 1, 2)),
    ]
    assert combine_asset_balances(a) == [
        _tuple_to_balance((1, 2, 2)),
        _tuple_to_balance((2, 2, 1)),
        _tuple_to_balance((3, 2, 4)),
    ], 'common time appearing outside of pair with odd failed'


def test_need_cursor_and_need_writable_cursor(database):
    """Test that the decorator handles all possible argument combos"""
    class OtherDB:

        def __init__(self, db) -> None:
            self.db = db

        @need_writable_cursor('db.user_write')
        def set_setting(self, write_cursor, name, value) -> None:
            self.db.set_setting(write_cursor, name, value)

        @need_cursor('db.conn.read_ctx')
        def get_setting(self, cursor, name) -> Any:
            return self.db.get_setting(cursor, name)

    # pylint: disable=no-value-for-parameter
    otherdb = OtherDB(database)
    otherdb.set_setting('premium_should_sync', True)
    assert otherdb.get_setting('premium_should_sync') is True
    otherdb.set_setting(name='premium_should_sync', value=False)
    assert otherdb.get_setting('premium_should_sync') is False
    with otherdb.db.user_write() as cursor:
        otherdb.set_setting(cursor, 'premium_should_sync', True)
        assert otherdb.get_setting('premium_should_sync') is True
        otherdb.set_setting(write_cursor=cursor, name='premium_should_sync', value=False)
        assert otherdb.get_setting('premium_should_sync') is False
        otherdb.set_setting(cursor, name='premium_should_sync', value=True)
        assert otherdb.get_setting('premium_should_sync') is True
