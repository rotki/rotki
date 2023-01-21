from typing import Any

import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.db.utils import (
    SingleDBAssetBalance,
    combine_asset_balances,
    db_tuple_to_str,
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


@pytest.mark.parametrize(
    ('data', 'tuple_type', 'expected_str'),
    [(
        ('1', 1674510513, 'B', 'ETH', 'USD', 'A', '1', '100', '0.1', 'USD', 'link', 'no notes'),
        'trade',
        'buy trade with id 1 in kraken and base/quote asset ETH / USD at timestamp 1674510513',
    ), (
        ('42', 'C', 'A', 1674510513, 'ETH', '1', 'USD', '0.1', 'link', 'address', 'txid'),
        'asset_movement',
        'deposit of ETH with id 42 in poloniex at timestamp 1674510513',
    ), (
        ('44', 'F', 1674510513, 1674510513, '1', 'ETH', '0.1', 'USD', 'link', 'notes'),
        'margin_position',
        'Margin position with id 44 in bitmex for ETH closed at timestamp 1674510513',
    ), (
        (b'\xba\x9aR\xa1D\xd4\xe7\x95\x80\xa5W\x16\x0e\x9f\x82i\xd3\xe57<\xe4K\xce\x00\xeb\xd6\tu@4\xb7\xbd', '10', 1674510513, 1, '0xfrom', '0xto', '1', '2', '21000', '1', '0x', 1),  # noqa: E501
        'evm_transaction',
        'EVM transaction with hash 0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd and chain id 10',  # noqa: E501
    ), (
        ('what', 'ever'), 'invalid_db_tuple_type', None,
    )],
)
def test_db_tuple_to_str(data, tuple_type, expected_str):
    if expected_str:
        assert db_tuple_to_str(data, tuple_type) == expected_str
    else:
        with pytest.raises(AssertionError):
            db_tuple_to_str(data, tuple_type)
