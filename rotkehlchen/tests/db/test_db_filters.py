import pytest

from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.db.filtering import (
    DBEvmTransactionJoinsFilter,
    DBFilterOrder,
    DBFilterPagination,
    DBFilterQuery,
    DBIgnoredAssetsFilter,
    DBLocationFilter,
    DBTimestampFilter,
    EvmTransactionsFilterQuery,
    InvalidFilter,
    TimestampProximityOrder,
)
from rotkehlchen.errors.misc import InputError
from rotkehlchen.tests.utils.database import clean_ignored_assets
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import Location, Timestamp, TimestampMS


def test_ethereum_transaction_filter():
    address = make_evm_address()
    filter_query = EvmTransactionsFilterQuery.make(
        limit=10,
        offset=10,
        accounts=[EvmAccount(address=address)],
        from_ts=Timestamp(1),
        to_ts=Timestamp(999),
    )
    query, bindings = filter_query.prepare()
    assert query == ' INNER JOIN evmtx_address_mappings WHERE evm_transactions.identifier=evmtx_address_mappings.tx_id AND ((evmtx_address_mappings.address = ?))  AND ((timestamp >= ? AND timestamp <= ?)) ORDER BY timestamp ASC LIMIT 10 OFFSET 10'  # noqa: E501
    assert bindings == [
        address,
        filter_query.from_ts,
        filter_query.to_ts,
    ]


@pytest.mark.parametrize(('and_op', 'order_by', 'pagination'), [
    (True, True, True),
    (False, True, True),
    (True, False, True),
    (True, True, False),
    (True, False, False),
])
def test_filter_arguments(and_op, order_by, pagination):
    """This one is just like the ethereum transactions filter test, but also using
    it as a testbed to test combinations of arguments"""
    accounts = [EvmAccount(make_evm_address()), EvmAccount(make_evm_address())]
    address_filter = DBEvmTransactionJoinsFilter(and_op=False, accounts=accounts)
    time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
    location_filter = DBLocationFilter(and_op=True, location=Location.KRAKEN)
    order_by_obj = DBFilterOrder(rules=[('timestamp', True)], case_sensitive=True) if order_by else None  # noqa: E501
    pagination_obj = DBFilterPagination(limit=10, offset=10) if pagination else None
    filter_query = DBFilterQuery(
        and_op=and_op,
        filters=[time_filter, location_filter],
        order_by=order_by_obj,
        pagination=pagination_obj,
    )
    filter_query.join_clause = address_filter
    query, bindings = filter_query.prepare()

    if and_op:
        expected_query = ' INNER JOIN evmtx_address_mappings WHERE evm_transactions.identifier=evmtx_address_mappings.tx_id AND ((evmtx_address_mappings.address = ?) OR (evmtx_address_mappings.address = ?))  AND ((timestamp >= ? AND timestamp <= ?) AND (location=?))'  # noqa: E501
    else:
        expected_query = ' INNER JOIN evmtx_address_mappings WHERE evm_transactions.identifier=evmtx_address_mappings.tx_id AND ((evmtx_address_mappings.address = ?) OR (evmtx_address_mappings.address = ?))  AND ((timestamp >= ? AND timestamp <= ?) OR (location=?))'  # noqa: E501

    if order_by:
        expected_query += ' ORDER BY timestamp ASC'

    if pagination:
        expected_query += ' LIMIT 10 OFFSET 10'

    assert query == expected_query
    assert bindings == [
        accounts[0].address,
        accounts[1].address,
        time_filter.from_ts,
        time_filter.to_ts,
        location_filter.location.serialize_for_db(),
    ]


def test_column_order_by_only_accepts_column_names():
    """A column ordering attribute is spliced into ORDER BY as an identifier, so prepare()
    only accepts plain (optionally table-qualified) column names and refuses anything else."""
    for attribute in ('name', 'last_update_timestamp', 'accounting_rules.identifier'):
        assert DBFilterOrder(
            rules=[(attribute, True)],
            case_sensitive=True,
        ).prepare() == (f'ORDER BY {attribute} ASC', [])

    for attribute in (
        'CASE WHEN 1=1 THEN 1 ELSE 1 END',
        '(SELECT 1)',
        'name COLLATE NOCASE',
        'name;',
        'ABS(timestamp - 1510000000000)',  # a computed expression must use TimestampProximityOrder
    ):
        with pytest.raises(InvalidFilter):
            DBFilterOrder(rules=[(attribute, True)], case_sensitive=True).prepare()


def test_timestamp_proximity_order_binds_anchor():
    """The proximity ordering emits a fixed expression with the anchor as a bound parameter,
    so no caller-supplied value is ever spliced into the query."""
    anchor = TimestampMS(1510000000000)
    assert DBFilterOrder(
        rules=[TimestampProximityOrder(anchor=anchor)],
        case_sensitive=True,
    ).prepare() == ('ORDER BY ABS(timestamp - ?) ASC', [anchor])
    assert DBFilterOrder(
        rules=[TimestampProximityOrder(anchor=anchor, ascending=False)],
        case_sensitive=False,
    ).prepare() == ('ORDER BY ABS(timestamp - ?) DESC', [anchor])


def test_filter_query_threads_order_bindings_after_filters():
    """A proximity order routed through DBFilterQuery.prepare contributes its anchor as a
    bound parameter placed after the WHERE filter bindings, matching the placeholder order."""
    anchor = TimestampMS(1700000000000)
    time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
    filter_query = DBFilterQuery(
        and_op=True,
        filters=[time_filter],
        order_by=DBFilterOrder(
            rules=[TimestampProximityOrder(anchor=anchor)],
            case_sensitive=True,
        ),
    )
    query, bindings = filter_query.prepare()
    assert query.endswith('ORDER BY ABS(timestamp - ?) ASC')
    assert bindings == [time_filter.from_ts, time_filter.to_ts, anchor]


def test_invalid_filter_is_input_error():
    """InvalidFilter subclasses InputError so the API maps it to a 400, not a 500."""
    assert issubclass(InvalidFilter, InputError)


def test_ignored_assets(database):
    """Test that the ignored asset filter works fine in all 4 cases"""
    clean_ignored_assets(database)
    # Test NOT IN with no ignored assets
    ignored_filter = DBIgnoredAssetsFilter(and_op=True, asset_key='assets.identifier', operator='NOT IN')  # noqa: E501
    querystr, bindings = ignored_filter.prepare()
    with database.conn.read_ctx() as cursor:
        assets_num = cursor.execute('SELECT COUNT(*) FROM assets').fetchone()[0]
        result = cursor.execute('SELECT COUNT(*) FROM assets WHERE ' + querystr[0], bindings).fetchone()[0]  # noqa: E501
        assert result == assets_num

    with database.user_write() as write_cursor:
        database.add_to_ignored_assets(write_cursor, A_ETH)
        database.add_to_ignored_assets(write_cursor, A_BTC)

    with database.conn.read_ctx() as cursor:
        # Test NOT IN with ignored assets
        result = cursor.execute('SELECT COUNT(*) FROM assets WHERE ' + querystr[0], bindings).fetchone()[0]  # noqa: E501
        assert result == assets_num - 2

        # Test IN with ignored assets
        ignored_filter = DBIgnoredAssetsFilter(and_op=True, asset_key='assets.identifier', operator='IN')  # noqa: E501
        querystr, bindings = ignored_filter.prepare()
        result = cursor.execute('SELECT COUNT(*) FROM assets WHERE ' + querystr[0], bindings).fetchone()[0]  # noqa: E501
        assert result == 2

    with database.user_write() as write_cursor:
        database.remove_from_ignored_assets(write_cursor, A_ETH)
        database.remove_from_ignored_assets(write_cursor, A_BTC)

    with database.conn.read_ctx() as cursor:
        # Test IN without ignored assets
        result = cursor.execute('SELECT COUNT(*) FROM assets WHERE ' + querystr[0], bindings).fetchone()[0]  # noqa: E501
        assert result == 0
