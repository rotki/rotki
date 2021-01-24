from typing import TYPE_CHECKING, List, Tuple

from rotkehlchen.typing import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


class DBQueryRanges():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def get_location_query_ranges(
            self,
            location_string: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[Tuple[Timestamp, Timestamp]]:
        """Takes in the start/end ts for a location query and after checking the
        last query ranges of the DB provides a list of timestamp ranges that still
        need to be queried.

        May return a bit more liberal ranges so that we can avoid further queries
        in the future.
        """
        queried_range = self.db.get_used_query_range(location_string)
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
            location_string: str,
            start_ts: Timestamp,
            end_ts: Timestamp,
            ranges_to_query: List[Tuple[Timestamp, Timestamp]],
    ) -> None:
        """Depending on the ranges to query and the given start and end ts update the DB"""
        if len(ranges_to_query) == 0:
            return

        starts = [x[0] for x in ranges_to_query]
        starts.append(start_ts)
        ends = [x[1] for x in ranges_to_query]
        ends.append(end_ts)
        saved_range = self.db.get_used_query_range(location_string)
        if saved_range:
            starts.append(saved_range[0])
            ends.append(saved_range[1])

        self.db.update_used_query_range(
            name=location_string,
            start_ts=min(starts),
            end_ts=max(ends),
        )
