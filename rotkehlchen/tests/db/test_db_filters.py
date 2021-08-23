import pytest

from rotkehlchen.db.filtering import (
    DBETHTransactionAddressFilter,
    DBFilterOrder,
    DBFilterPagination,
    DBFilterQuery,
    DBTimestampFilter,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.typing import Timestamp


def test_ethereum_transaction_filter():
    address = make_ethereum_address()
    address_filter = DBETHTransactionAddressFilter(and_op=False, address=address)
    time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
    filter_query = DBFilterQuery(
        and_op=True,
        filters=[address_filter, time_filter],
        order_by=DBFilterOrder(attribute='timestamp', ascending=True),
        pagination=DBFilterPagination(limit=10, offset=10),
    )
    query, bindings = filter_query.prepare()
    assert query == 'WHERE (from_address = ? OR to_address = ?) AND (timestamp >= ? AND timestamp <= ?) ORDER BY timestamp ASC LIMIT 10 OFFSET 10'  # noqa: E501
    assert bindings == [
        address,
        address,
        time_filter.from_ts,
        time_filter.to_ts,
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
    address = make_ethereum_address()
    address_filter = DBETHTransactionAddressFilter(and_op=False, address=address)
    time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
    order_by_obj = DBFilterOrder(attribute='timestamp', ascending=True) if order_by else None
    pagination_obj = DBFilterPagination(limit=10, offset=10) if pagination else None
    filter_query = DBFilterQuery(
        and_op=and_op,
        filters=[address_filter, time_filter],
        order_by=order_by_obj,
        pagination=pagination_obj,
    )
    query, bindings = filter_query.prepare()

    if and_op:
        expected_query = 'WHERE (from_address = ? OR to_address = ?) AND (timestamp >= ? AND timestamp <= ?)'  # noqa: E501
    else:
        expected_query = 'WHERE (from_address = ? OR to_address = ?) OR (timestamp >= ? AND timestamp <= ?)'  # noqa: E501

    if order_by:
        expected_query += ' ORDER BY timestamp ASC'

    if pagination:
        expected_query += ' LIMIT 10 OFFSET 10'

    assert query == expected_query
    assert bindings == [
        address,
        address,
        time_filter.from_ts,
        time_filter.to_ts,
    ]


# def test_filter_arguments():
#     time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
#     filter_query = DBFilterQuery(
#         and_op=True,
#         filters=[time_filter],
#         order_by=DBFilterOrder(attribute='timestamp', ascending=True),
#     )
#     query, bindings = filter_query.prepare()
#     assert query == 'WHERE (timestamp >= ? AND timestamp <= ?) ORDER BY timestamp ASC'
#     assert bindings == [
#         time_filter.from_ts,
#         time_filter.to_ts,
#     ]


# def test_filter_no_order():
#     time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
#     filter_query = DBFilterQuery(
#         and_op=True,
#         filters=[time_filter],
#         pagination=DBFilterPagination(limit=10, offset=10),
#     )
#     query, bindings = filter_query.prepare()
#     assert query == 'WHERE (timestamp >= ? AND timestamp <= ?) LIMIT 10 OFFSET 10'
#     assert bindings == [
#         time_filter.from_ts,
#         time_filter.to_ts,
#     ]


# def test_filter_no_order():
#     time_filter = DBTimestampFilter(and_op=True, from_ts=Timestamp(1), to_ts=Timestamp(999))
#     filter_query = DBFilterQuery(
#         and_op=True,
#         filters=[time_filter],
#         pagination=DBFilterPagination(limit=10, offset=10),
#     )
#     query, bindings = filter_query.prepare()
#     assert query == 'WHERE (timestamp >= ? AND timestamp <= ?) LIMIT 10 OFFSET 10'
#     assert bindings == [
#         time_filter.from_ts,
#         time_filter.to_ts,
#     ]
