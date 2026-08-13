from typing import Any

import pytest

from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.types import Timestamp


def test_get_location_query_ranges(database: Any) -> None:
    dbranges = DBQueryRanges(database)
    location1 = 'location1'
    location2 = 'location2'

    with database.user_write() as cursor:
        database.update_used_query_range(cursor, location1, 15, 25)
        database.update_used_query_range(cursor, location2, 10, 125)

        result = dbranges.get_location_query_ranges(cursor, location1, Timestamp(0), Timestamp(2))
        assert result == [(0, 14)]
        result = dbranges.get_location_query_ranges(cursor, location1, Timestamp(8), Timestamp(17))
        assert result == [(8, 14)]
        result = dbranges.get_location_query_ranges(cursor, location1, Timestamp(19), Timestamp(23))  # noqa: E501
        assert result == []
        result = dbranges.get_location_query_ranges(cursor, location1, Timestamp(22), Timestamp(57))  # noqa: E501
        assert result == [(26, 57)]
        result = dbranges.get_location_query_ranges(cursor, location1, Timestamp(26), Timestamp(125))  # noqa: E501
        assert result == [(26, 125)]

        result = dbranges.get_location_query_ranges(cursor, location2, Timestamp(3), Timestamp(9))
        assert result == [(3, 9)]
        result = dbranges.get_location_query_ranges(cursor, location2, Timestamp(9), Timestamp(17))
        assert result == [(9, 9)]
        result = dbranges.get_location_query_ranges(cursor, location2, Timestamp(19), Timestamp(23))  # noqa: E501
        assert result == []
        result = dbranges.get_location_query_ranges(cursor, location2, Timestamp(120), Timestamp(250))  # noqa: E501
        assert result == [(126, 250)]
        result = dbranges.get_location_query_ranges(cursor, location2, Timestamp(126), Timestamp(170))  # noqa: E501
        assert result == [(126, 170)]


def test_update_used_query_range(database: Any) -> None:
    dbranges = DBQueryRanges(database)
    location1, location2, location3 = 'location1', 'location2', 'location3'

    with database.user_write() as cursor:
        # First check several successful scenarios with consecutive ranges
        database.update_used_query_range(cursor, location1, 15, 25)
        database.update_used_query_range(cursor, location2, 10, 125)

        start_ts, end_ts = Timestamp(12), Timestamp(90)
        query_range = dbranges.get_location_query_ranges(cursor, location1, start_ts, end_ts)
        dbranges.update_used_query_range(
            cursor,
            location1,
            queried_ranges=[(start_ts, end_ts)] + query_range,
        )
        assert database.get_used_query_range(cursor, location1) == (12, 90)

        start_ts, end_ts = Timestamp(250), Timestamp(500)
        query_range = dbranges.get_location_query_ranges(cursor, location2, start_ts, end_ts)
        dbranges.update_used_query_range(
            cursor,
            location2,
            queried_ranges=[(start_ts, end_ts)] + query_range,
        )
        # Check that a gap within the new queried ranges is fine if the range from the db already covers that gap.  # noqa: E501
        dbranges.update_used_query_range(
            write_cursor=cursor,
            location_string=location2,
            queried_ranges=[(Timestamp(10), Timestamp(20)), (Timestamp(30), Timestamp(510))],
        )
        assert database.get_used_query_range(cursor, location2) == (10, 510)

        # Check failure of various non-consecutive ranges with no saved range in the DB
        for queried_ranges in (
            [(Timestamp(1), Timestamp(5)), (Timestamp(10), Timestamp(20))],
            [(Timestamp(10), Timestamp(20)), (Timestamp(1), Timestamp(5))],
            [(Timestamp(1), Timestamp(5)), (Timestamp(10), Timestamp(20)), (Timestamp(30), Timestamp(40))],  # noqa: E501
            [(Timestamp(1), Timestamp(5)), (Timestamp(3), Timestamp(10)), (Timestamp(0), Timestamp(11)), (Timestamp(14), Timestamp(20))],  # noqa: E501
        ):
            with pytest.raises(AssertionError):
                dbranges.update_used_query_range(
                    write_cursor=cursor,
                    location_string=location3,
                    queried_ranges=queried_ranges,
                )

        # Check failure of various ranges that are non-consecutive even when combined with an existing saved range from the DB.  # noqa: E501
        database.update_used_query_range(
            write_cursor=cursor,
            name=location3,
            start_ts=10,
            end_ts=50,
        )
        for queried_ranges in (
            [(Timestamp(1), Timestamp(5))],
            [(Timestamp(55), Timestamp(60))],
            [(Timestamp(1), Timestamp(5)), (Timestamp(55), Timestamp(60))],
            [(Timestamp(1), Timestamp(20)), (Timestamp(55), Timestamp(60))],
            [(Timestamp(1), Timestamp(5)), (Timestamp(40), Timestamp(60))],
        ):
            with pytest.raises(AssertionError):
                dbranges.update_used_query_range(
                    write_cursor=cursor,
                    location_string=location3,
                    queried_ranges=queried_ranges,
                )
