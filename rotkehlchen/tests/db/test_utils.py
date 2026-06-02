
import pytest

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.db.utils import (
    SingleDBAssetBalance,
    combine_asset_balances,
    db_tuple_to_str,
    form_query_to_filter_timestamps,
    update_table_schema,
)
from rotkehlchen.fval import FVal
from rotkehlchen.types import SUPPORTED_EVM_EVMLIKE_CHAINS, SupportedBlockchain


@pytest.mark.parametrize(
    (('query_in', 'timestamp_attribute', 'from_ts', 'to_ts', 'expected_query_out', 'expected_bindings')),  # noqa: E501
    [
        (
            'SELECT * FROM margin_positions',
            'timestamp',
            None,
            None,
            'SELECT * FROM margin_positions ORDER BY timestamp ASC;',
            (),
        ),
        (
            'SELECT * FROM margin_positions',
            'timestamp',
            1609336000,
            None,
            'SELECT * FROM margin_positions WHERE timestamp >= ? ORDER BY timestamp ASC;',
            (1609336000,),
        ),
        (
            'SELECT * FROM margin_positions',
            'timestamp',
            None,
            1609336240,
            'SELECT * FROM margin_positions WHERE timestamp <= ? ORDER BY timestamp ASC;',
            (1609336240,),
        ),
        (
            'SELECT * FROM margin_positions',
            'timestamp',
            1609336000,
            1609336240,
            'SELECT * FROM margin_positions WHERE timestamp >= ? AND timestamp <= ? ORDER BY timestamp ASC;',  # noqa: E501
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


@pytest.mark.parametrize(
    ('data', 'tuple_type', 'expected_str'),
    [(
        ('44', 'F', 1674510513, 1674510513, '1', 'ETH', '0.1', 'USD', 'link', 'notes'),
        'margin_position',
        'Margin position with id 44 in bitmex for ETH closed at timestamp 1674510513',
    ), (
        (b'\xba\x9aR\xa1D\xd4\xe7\x95\x80\xa5W\x16\x0e\x9f\x82i\xd3\xe57<\xe4K\xce\x00\xeb\xd6\tu@4\xb7\xbd', '10', 1674510513, 1, '0xfrom', '0xto', '1', '2', '21000', '1', '0x', 1),  # noqa: E501
        'evm_transaction',
        'EVM transaction with hash 0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd and chain id 10',  # noqa: E501
    ), (
        (12345, 67890, 1674510513, True, b'\x12\x34\x56\x78\x9a\xbc\xde\xf0\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\xcc\xdd\xee\xff\x00'),  # noqa: E501
        'solana_transaction',
        'Solana transaction with signature 123456789abcdef0...',
    ), (
        (1, 5, -1, 2, b'\x01\x02\x03'),
        'solana_instruction',
        'Solana instruction with execution_index 5 in transaction 1',
    ), (
        (1, 0, b'address_bytes_here'),
        'solana_account_key',
        'Solana account key at index 0 for transaction 1',
    ), (
        (1, 1, 0, 5, 1),
        'solana_instruction_account',
        'Solana instruction account at order 0 for instruction 1',
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


@pytest.mark.parametrize(('db_settings', 'expected_chains'), [
    ({'evmchains_to_skip_detection': []}, set(SUPPORTED_EVM_EVMLIKE_CHAINS)),
    ({'evmchains_to_skip_detection': [SupportedBlockchain.POLYGON_POS, SupportedBlockchain.BASE, SupportedBlockchain.ARBITRUM_ONE]}, {SupportedBlockchain.ETHEREUM, SupportedBlockchain.OPTIMISM, SupportedBlockchain.AVALANCHE, SupportedBlockchain.GNOSIS, SupportedBlockchain.SCROLL, SupportedBlockchain.BINANCE_SC, SupportedBlockchain.ZKSYNC_LITE, SupportedBlockchain.HYPERLIQUID, SupportedBlockchain.MONAD}),  # noqa: E501
])
def test_get_chains_to_detect_evm_accounts(database, expected_chains):
    assert set(database.get_chains_to_detect_evm_accounts()) == expected_chains


def test_update_table_schema_rejects_pk_renumber(database):
    """update_table_schema must refuse to silently renumber an existing INTEGER PRIMARY KEY,
    since that orphans external references (e.g. tag_mappings.object_reference). It is allowed
    only when the id is preserved, or explicitly opted into via allow_pk_renumber."""
    schema = 'id INTEGER PRIMARY KEY, name TEXT'
    with database.user_write() as write_cursor:
        write_cursor.execute('CREATE TABLE pk_test (id INTEGER PRIMARY KEY, name TEXT)')
        write_cursor.executemany(
            'INSERT INTO pk_test(id, name) VALUES(?, ?)',
            [(1, 'a'), (3, 'b')],  # gap at 2
        )

        def current_ids() -> list:
            return write_cursor.execute('SELECT id FROM pk_test ORDER BY id').fetchall()

        # dropping the id from an explicit insert_columns is rejected
        with pytest.raises(ValueError, match='would renumber the INTEGER PRIMARY KEY'):
            update_table_schema(
                write_cursor=write_cursor,
                table_name='pk_test',
                schema=schema,
                insert_columns='name',
                insert_order='(name)',
            )
        write_cursor.execute('DROP TABLE IF EXISTS pk_test_new')  # clean the half-built table

        # including the id preserves the original ids (and the gap)
        update_table_schema(
            write_cursor=write_cursor,
            table_name='pk_test',
            schema=schema,
            insert_columns='id, name',
            insert_order='(id, name)',
        )
        assert current_ids() == [(1,), (3,)]

        # explicit opt-in renumbers without raising
        update_table_schema(
            write_cursor=write_cursor,
            table_name='pk_test',
            schema=schema,
            insert_columns='name',
            insert_order='(name)',
            allow_pk_renumber=True,
        )
        assert current_ids() == [(1,), (2,)]
