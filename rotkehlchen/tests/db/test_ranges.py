from rotkehlchen.db.ranges import DBQueryRanges


def test_get_location_query_ranges(database):
    dbranges = DBQueryRanges(database)
    location1 = 'location1'
    location2 = 'location2'

    database.update_used_query_range(location1, 15, 25)
    database.update_used_query_range(location2, 10, 125)

    result = dbranges.get_location_query_ranges(location1, 0, 2)
    assert result == [(0, 14)]
    result = dbranges.get_location_query_ranges(location1, 8, 17)
    assert result == [(8, 14)]
    result = dbranges.get_location_query_ranges(location1, 19, 23)
    assert result == []
    result = dbranges.get_location_query_ranges(location1, 22, 57)
    assert result == [(26, 57)]
    result = dbranges.get_location_query_ranges(location1, 26, 125)
    assert result == [(26, 125)]

    result = dbranges.get_location_query_ranges(location2, 3, 9)
    assert result == [(3, 9)]
    result = dbranges.get_location_query_ranges(location2, 9, 17)
    assert result == [(9, 9)]
    result = dbranges.get_location_query_ranges(location2, 19, 23)
    assert result == []
    result = dbranges.get_location_query_ranges(location2, 120, 250)
    assert result == [(126, 250)]
    result = dbranges.get_location_query_ranges(location2, 126, 170)
    assert result == [(126, 170)]


def test_update_used_query_range(database):
    dbranges = DBQueryRanges(database)
    location1 = 'location1'
    location2 = 'location2'

    database.update_used_query_range(location1, 15, 25)
    database.update_used_query_range(location2, 10, 125)

    dbranges.update_used_query_range(location1, 0, 10, [])
    msg = 'empty used query range should do nothing'
    assert database.get_used_query_range(location1) == (15, 25), msg

    start_ts = 12
    end_ts = 90
    query_range = dbranges.get_location_query_ranges(location1, start_ts, end_ts)
    dbranges.update_used_query_range(
        location1,
        start_ts=start_ts,
        end_ts=end_ts,
        ranges_to_query=query_range,
    )
    assert database.get_used_query_range(location1) == (12, 90)

    start_ts = 250
    end_ts = 500
    query_range = dbranges.get_location_query_ranges(location2, start_ts, end_ts)
    dbranges.update_used_query_range(
        location2,
        start_ts=start_ts,
        end_ts=end_ts,
        ranges_to_query=query_range,
    )
    assert database.get_used_query_range(location2) == (10, 500)
