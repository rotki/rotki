import pytest

from rotkehlchen.db.filtering import (
    DBETHTransactionJoinsFilter,
    DBFilterOrder,
    DBFilterPagination,
    DBFilterQuery,
    DBLocationFilter,
    DBTimestampFilter,
    ETHTransactionsFilterQuery,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import Location, Timestamp


def test_ethereum_transaction_filter():
    addresses = [make_ethereum_address()]
    filter_query = ETHTransactionsFilterQuery.make(
        limit=10,
        offset=10,
        addresses=addresses,
        from_ts=Timestamp(1),
        to_ts=Timestamp(999),
    )
    query, bindings = filter_query.prepare()
    assert query == ' INNER JOIN ethtx_address_mappings WHERE ethereum_transactions.tx_hash=ethtx_address_mappings.tx_hash AND ethtx_address_mappings.address IN (?)  AND ((timestamp >= ? AND timestamp <= ?)) ORDER BY timestamp ASC LIMIT 10 OFFSET 10'  # noqa: E501
    assert bindings == [
        addresses[0],
        filter_query.from_ts,
        filter_query.to_ts,
    ]


@pytest.mark.parametrize('and_op,order_by,pagination', [
    (True, True, True),
    (False, True, True),
    (True, False, True),
    (True, True, False),
    (True, False, False),
])
def test_filter_arguments(and_op, order_by, pagination):
    """This one is just like the ethereum transactions filter test, but also using
    it as a testbed to test combinations of arguments"""
    addresses = [make_ethereum_address(), make_ethereum_address()]
    address_filter = DBETHTransactionJoinsFilter(and_op=False, addresses=addresses)
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
        expected_query = ' INNER JOIN ethtx_address_mappings WHERE ethereum_transactions.tx_hash=ethtx_address_mappings.tx_hash AND ethtx_address_mappings.address IN (?,?)  AND ((timestamp >= ? AND timestamp <= ?) AND (location=?))'  # noqa: E501
    else:
        expected_query = ' INNER JOIN ethtx_address_mappings WHERE ethereum_transactions.tx_hash=ethtx_address_mappings.tx_hash AND ethtx_address_mappings.address IN (?,?)  AND ((timestamp >= ? AND timestamp <= ?) OR (location=?))'  # noqa: E501

    if order_by:
        expected_query += ' ORDER BY timestamp ASC'

    if pagination:
        expected_query += ' LIMIT 10 OFFSET 10'

    assert query == expected_query
    assert bindings == [
        addresses[0],
        addresses[1],
        time_filter.from_ts,
        time_filter.to_ts,
        location_filter.location.serialize_for_db(),
    ]
