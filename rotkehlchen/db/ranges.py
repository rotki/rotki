from typing import TYPE_CHECKING

from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor


class DBQueryRanges:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def get_location_query_ranges(
            self,
            cursor: 'DBCursor',
            location_string: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> list[tuple[Timestamp, Timestamp]]:
        """Takes in the start/end ts for a location query and after checking the
        last query ranges of the DB provides a list of timestamp ranges that still
        need to be queried.

        May return a bit more liberal ranges so that we can avoid further queries
        in the future.
        """
        queried_range = self.db.get_used_query_range(cursor, location_string)
        if not queried_range:
            ranges_to_query = [(start_ts, end_ts)]
        else:
            ranges_to_query = []
            if start_ts < queried_range[0]:
                ranges_to_query.append((start_ts, Timestamp(queried_range[0] - 1)))

            if end_ts > queried_range[1]:
                ranges_to_query.append((Timestamp(queried_range[1] + 1), end_ts))

        return ranges_to_query

    def update_used_query_range(
            self,
            write_cursor: 'DBCursor',
            location_string: str,
            queried_ranges: list[tuple[Timestamp, Timestamp]],
    ) -> None:
        """Depending on the queried ranges update the DB"""
        if len(queried_ranges) == 0:
            return

        starts = [x[0] for x in queried_ranges]
        ends = [x[1] for x in queried_ranges]
        saved_range = self.db.get_used_query_range(write_cursor, location_string)
        if saved_range is not None:
            starts.append(saved_range[0])
            ends.append(saved_range[1])

        self.db.update_used_query_range(
            write_cursor=write_cursor,
            name=location_string,
            start_ts=min(starts),
            end_ts=max(ends),
        )
