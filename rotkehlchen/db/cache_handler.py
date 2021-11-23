import logging
from copy import deepcopy

from typing import TYPE_CHECKING, Dict, List, Any, Tuple
from typing_extensions import Literal

from rotkehlchen.accounting.accountant import FREE_PNL_EVENTS_LIMIT
from rotkehlchen.typing import NamedJson
from rotkehlchen.db.filtering import ReportsFilterQuery, ReportDataFilterQuery, ReportIDFilterQuery
from rotkehlchen.errors import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

FREE_REPORTS_LOOKUP_LIMIT = 20

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def deserialize_report_from_db(report: Any) -> Dict[str, Any]:
    return {
        'identifier': report[0],
        'name': report[1],
        'timestamp': report[2],
        'start_ts': report[3],
        'end_ts': report[4],
        'size_on_disk': report[5],
    }


def _return_reports_or_events_maybe_limit(
        entry_type: Literal['events', 'reports'],
        entries_found: int,
        entries: List[Dict[str, Any]],
        with_limit: bool,
) -> Tuple[List[Dict[str, Any]], int]:
    if with_limit is False:
        return entries, entries_found

    if entry_type == 'events':
        limit = FREE_PNL_EVENTS_LIMIT
    if entry_type == 'reports':
        limit = FREE_REPORTS_LOOKUP_LIMIT

    count: int = 0
    for _ in entries:
        count += 1

    returning_entries_length = min(limit, len(entries))

    return entries[:returning_entries_length], entries_found


class DBAccountingReports(LockableQueryMixIn):

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator):
        super().__init__()
        self.db = database
        self.msg_aggregator = msg_aggregator

    @protect_with_lock()
    def query(
            self,
            filter_query: ReportsFilterQuery,
            with_limit: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Queries for all reports/events of a Profit and Loss Report which has been performed
        historically. Returns a list of all transactions filtered and sorted according to the
        parameters.

        If `with_limit` is true then the api limit is applied

        if `recent_first` is true then the transactions are returned with the most
        recent first on the list

        May raise:
        - TODO check what it may raise
        """
        entries, total_filter_count = self.get_reports(filter_=filter_query)

        return _return_reports_or_events_maybe_limit(
            entry_type='reports',
            entries=entries,
            entries_found=total_filter_count,
            with_limit=with_limit,
        )

    def add_report(self, start_ts: Timestamp, end_ts: Timestamp) -> int:
        cursor = self.db.conn_transient.cursor()
        timestamp = ts_now()
        query = """
        INSERT INTO pnl_reports(
            name, timestamp, start_ts, end_ts
        )
        VALUES (?, ?, ?, ?)"""
        cursor.execute(query, (f"Report from {start_ts} to {end_ts}", timestamp, start_ts, end_ts))
        identifier = cursor.lastrowid
        self.db.conn_transient.commit()
        return identifier

    def get_reports(self, filter_: ReportsFilterQuery) -> Tuple[List[Dict[str, Any]], int]:
        cursor = self.db.conn_transient.cursor()
        query, bindings = filter_.prepare()
        query = 'SELECT * FROM pnl_reports ' + query
        results = cursor.execute(query, bindings)

        reports = []
        for result in results:
            try:
                report = deserialize_report_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing PnL Report for index from the DB. Skipping it.'
                    f'Error was: {str(e)}',
                )
                continue

            reports.append(report)

        if filter_.pagination is not None:
            no_pagination_filter = deepcopy(filter_)
            no_pagination_filter.pagination = None
            query, bindings = no_pagination_filter.prepare()
            query = 'SELECT COUNT(*) FROM pnl_reports ' + query
            results = cursor.execute(query, bindings).fetchone()
            total_filter_count = results[0]
        else:
            total_filter_count = len(reports)

        return reports, total_filter_count

    def purge_report_data(self, filter_: ReportIDFilterQuery) -> None:
        """Deletes all report related data from the DB"""
        cursor = self.db.conn_transient.cursor()
        query, bindings = filter_.prepare()
        query = 'DELETE FROM pnl_reports ' + query
        cursor.execute(query, bindings)
        self.db.conn.commit()
        self.db.update_last_write()


class DBAccountingReportData(LockableQueryMixIn):

    def __init__(self, database: 'DBHandler', msg_aggregator: MessagesAggregator):
        super().__init__()
        self.db = database
        self.msg_aggregator = msg_aggregator

    @protect_with_lock()
    def query(
            self,
            filter_query: ReportDataFilterQuery,
            with_limit: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Queries for all reports/events of a Profit and Loss Report which has been performed
        historically. Returns a list of all transactions filtered and sorted according to the
        parameters.

        If `with_limit` is true then the api limit is applied

        if `recent_first` is true then the transactions are returned with the most
        recent first on the list

        May raise:
        - TODO check what it may raise
        """
        entries, total_filter_count = self.get_data(filter_=filter_query)

        return _return_reports_or_events_maybe_limit(
            entry_type='events',
            entries_found=total_filter_count,
            entries=entries,
            with_limit=with_limit,
        )

    def add_report_data(self, report_id: int, time: Timestamp, event: NamedJson) -> None:
        """Adds a new entry to a transient report for the PnL history in a given time range
        May raise:
        - sqlcipher.IntegrityError if there is a conflict at serialization of the event
        """
        cursor = self.db.conn_transient.cursor()
        query = """
        INSERT INTO pnl_events(
            report_id, timestamp, event_type, data
        )
        VALUES(?, ?, ?, ?);"""
        cursor.execute(query, (report_id, time) + event.to_db_tuple())
        self.db.conn_transient.commit()

    def get_data(self, filter_: ReportDataFilterQuery) -> Tuple[List[Dict[str, Any]], int]:
        cursor = self.db.conn_transient.cursor()
        query, bindings = filter_.prepare()
        query = 'SELECT event_type, data FROM pnl_events ' + query
        results = cursor.execute(query, bindings)

        records = []
        for result in results:
            try:
                record = NamedJson.deserialize_from_db(result).data
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing AccountingEvent from the DB. Skipping it.'
                    f'Error was: {str(e)}',
                )
                continue

            records.append(record)

        if filter_.pagination is not None:
            no_pagination_filter = deepcopy(filter_)
            no_pagination_filter.pagination = None
            query, bindings = no_pagination_filter.prepare()
            query = 'SELECT COUNT(*) FROM pnl_events ' + query
            results = cursor.execute(query, bindings).fetchone()
            total_filter_count = results[0]
        else:
            total_filter_count = len(records)

        return records, total_filter_count
