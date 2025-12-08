import logging
import operator
from itertools import pairwise
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
        all_ranges = queried_ranges.copy()
        if (saved_range := self.db.get_used_query_range(write_cursor, location_string)) is not None:  # noqa: E501
            all_ranges.append(saved_range)
            starts.append(saved_range[0])
            ends.append(saved_range[1])

        # Check that queried ranges are consecutive with no unqueried gaps
        for (_, current_end), (next_start, _) in pairwise(sorted_ranges := sorted(all_ranges, key=operator.itemgetter(0))):  # noqa: E501
            if current_end < next_start - 1:  # `start - 1` to allow end 14, start 15 for instance
                log.error(msg :=
                    f'Gap detected in {location_string} queried ranges: {sorted_ranges}. '
                    f'Range ending at {current_end} and next range starting at {next_start}. '
                    'Cannot save ranges to the DB.',
                )
                assert False, msg  # hard fail in develop since range gaps are a programming error and should never happen.  # noqa: E501, PT015, B011
                return  # type: ignore[unreachable]  # simply return without saving the range in production

        self.db.update_used_query_range(
            write_cursor=write_cursor,
            name=location_string,
            start_ts=min(starts),
            end_ts=max(ends),
        )
