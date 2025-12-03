import pytest

from rotkehlchen.db.ranges import DBQueryRanges


def test_get_location_query_ranges(database):
    dbranges = DBQueryRanges(database)
    location1 = 'location1'
    location2 = 'location2'

    with database.user_write() as cursor:
        database.update_used_query_range(cursor, location1, 15, 25)
        database.update_used_query_range(cursor, location2, 10, 125)

        result = dbranges.get_location_query_ranges(cursor, location1, 0, 2)
        assert result == [(0, 14)]
        result = dbranges.get_location_query_ranges(cursor, location1, 8, 17)
        assert result == [(8, 14)]
        result = dbranges.get_location_query_ranges(cursor, location1, 19, 23)
        assert result == []
        result = dbranges.get_location_query_ranges(cursor, location1, 22, 57)
        assert result == [(26, 57)]
        result = dbranges.get_location_query_ranges(cursor, location1, 26, 125)
        assert result == [(26, 125)]

        result = dbranges.get_location_query_ranges(cursor, location2, 3, 9)
        assert result == [(3, 9)]
        result = dbranges.get_location_query_ranges(cursor, location2, 9, 17)
        assert result == [(9, 9)]
        result = dbranges.get_location_query_ranges(cursor, location2, 19, 23)
        assert result == []
        result = dbranges.get_location_query_ranges(cursor, location2, 120, 250)
        assert result == [(126, 250)]
        result = dbranges.get_location_query_ranges(cursor, location2, 126, 170)
        assert result == [(126, 170)]


def test_update_used_query_range(database):
    dbranges = DBQueryRanges(database)
    location1, location2, location3 = 'location1', 'location2', 'location3'

    with database.user_write() as cursor:
        # First check several successful scenarios with consecutive ranges
        database.update_used_query_range(cursor, location1, 15, 25)
        database.update_used_query_range(cursor, location2, 10, 125)

        start_ts, end_ts = 12, 90
        query_range = dbranges.get_location_query_ranges(cursor, location1, start_ts, end_ts)
        dbranges.update_used_query_range(
            cursor,
            location1,
            queried_ranges=[(start_ts, end_ts)] + query_range,
        )
        assert database.get_used_query_range(cursor, location1) == (12, 90)

        start_ts, end_ts = 250, 500
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
            queried_ranges=[(10, 20), (30, 510)],
        )
        assert database.get_used_query_range(cursor, location2) == (10, 510)

        # Check failure of various non-consecutive ranges with no saved range in the DB
        for queried_ranges in (
            [(1, 5), (10, 20)],
            [(10, 20), (1, 5)],
            [(1, 5), (10, 20), (30, 40)],
            [(1, 5), (3, 10), (0, 11), (14, 20)],
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
            [(1, 5)],
            [(55, 60)],
            [(1, 5), (55, 60)],  # gaps on both sides of saved range
            [(1, 20), (55, 60)],  # gap only on upper side
            [(1, 5), (40, 60)],  # gap only on lower side
        ):
            with pytest.raises(AssertionError):
                dbranges.update_used_query_range(
                    write_cursor=cursor,
                    location_string=location3,
                    queried_ranges=queried_ranges,
                )
