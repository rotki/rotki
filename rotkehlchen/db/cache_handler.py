import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from pysqlcipher3 import dbapi2 as sqlcipher
from typing_extensions import Literal

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT, FREE_REPORTS_LOOKUP_LIMIT
from rotkehlchen.accounting.typing import NamedJson
from rotkehlchen.db.filtering import ReportDataFilterQuery
from rotkehlchen.errors import DeserializationError, InputError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import Timestamp
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _get_reports_or_events_maybe_limit(
        entry_type: Literal['events', 'reports'],
        entries_found: int,
        entries: List[Dict[str, Any]],
        with_limit: bool,
) -> Tuple[List[Dict[str, Any]], int]:
    if with_limit is False:
        return entries, entries_found

    if entry_type == 'events':
        limit = FREE_PNL_EVENTS_LIMIT
    elif entry_type == 'reports':
        limit = FREE_REPORTS_LOOKUP_LIMIT

    returning_entries_length = min(limit, len(entries))
    return entries[:returning_entries_length], entries_found


class DBAccountingReports():

    def __init__(self, database: 'DBHandler'):
        self.db = database

    def add_report(
            self,
            first_processed_timestamp: Timestamp,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> int:
        cursor = self.db.conn_transient.cursor()
        timestamp = ts_now()
        query = """
        INSERT INTO pnl_reports(
            name, timestamp, start_ts, end_ts, first_processed_timestamp
        )
        VALUES (?, ?, ?, ?, ?)"""
        cursor.execute(
            query,
            (f'Report from {start_ts} to {end_ts}',
             timestamp,
             start_ts,
             end_ts,
             first_processed_timestamp,
             ),
        )
        identifier = cursor.lastrowid
        self.db.conn_transient.commit()
        return identifier

    def add_report_overview(
            self,
            report_id: int,
            ledger_actions_profit_loss: str,
            defi_profit_loss: str,
            loan_profit: str,
            margin_positions_profit_loss: str,
            settlement_losses: str,
            ethereum_transaction_gas_costs: str,
            asset_movement_fees: str,
            general_trade_profit_loss: str,
            taxable_trade_profit_loss: str,
            total_taxable_profit_loss: str,
            total_profit_loss: str,
    ) -> None:
        """Inserts the report overview data

        May raise:
        - InputError if the given report id does not exist
        """
        cursor = self.db.conn_transient.cursor()
        cursor.execute(
            'UPDATE pnl_reports SET ledger_actions_profit_loss=?, defi_profit_loss=?, '
            'loan_profit=?, margin_positions_profit_loss=?, settlement_losses=?, '
            'ethereum_transaction_gas_costs=?, asset_movement_fees=?, general_trade_profit_loss=?,'
            ' taxable_trade_profit_loss=?, total_taxable_profit_loss=?, total_profit_loss=? '
            ' WHERE identifier=?',
            (ledger_actions_profit_loss, defi_profit_loss, loan_profit,
             margin_positions_profit_loss, settlement_losses,
             ethereum_transaction_gas_costs, asset_movement_fees,
             general_trade_profit_loss, taxable_trade_profit_loss,
             total_taxable_profit_loss, total_profit_loss, report_id),
        )
        if cursor.rowcount != 1:
            raise InputError(
                f'Could not insert overview for {report_id}. '
                f'Report id could not be found in the DB',
            )
        self.db.conn_transient.commit()

    def _get_report_size(self, report_id: int) -> int:
        """Returns an approximation of the DB size in bytes for the given report.

        It's an approximation since length() in sqlite returns the string length
        and not the byte length of a field. Also integers are stored depending on
        their size and there is no easy way (apart from checking each integer) to
        figure out the byte size. Finally there probably is various padding and
        prefixes which are not taken into account.
        """
        cursor = self.db.conn_transient.cursor()
        return cursor.execute(
            """SELECT SUM(row_size) FROM (SELECT
            8 + /*identifier - assume biggest int size */
            8 + /*report_id  - assume biggest int size */
            8 + /*timestamp  - assume biggest int size */
            1 + /*event_type */
            length(data) AS row_size FROM pnl_events WHERE report_id=?)""",
            (report_id,),
        ).fetchone()[0]

    def get_reports(
            self,
            report_id: Optional[int],
            with_limit: bool,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Queries all historical saved PnL reports.

        If `with_limit` is true then the api limit is applied
        """
        cursor = self.db.conn_transient.cursor()
        bindings: Union[Tuple, Tuple[int]] = ()
        query = 'SELECT * from pnl_reports'
        if report_id is not None:
            bindings = (report_id,)
            query += ' WHERE identifier=?'
        results = cursor.execute(query, bindings)

        reports = []
        for report in results:
            this_report_id = report[0]
            size_result = self._get_report_size(this_report_id)
            reports.append({
                'identifier': this_report_id,
                'name': report[1],
                'timestamp': report[2],
                'start_ts': report[3],
                'end_ts': report[4],
                'first_processed_timestamp': report[5],
                'size_on_disk': size_result,
                'ledger_actions_profit_loss': report[6],
                'defi_profit_loss': report[7],
                'loan_profit': report[8],
                'margin_positions_profit_loss': report[9],
                'settlement_losses': report[10],
                'ethereum_transaction_gas_costs': report[11],
                'asset_movement_fees': report[12],
                'general_trade_profit_loss': report[13],
                'taxable_trade_profit_loss': report[14],
                'total_taxable_profit_loss': report[15],
                'total_profit_loss': report[16],
            })

        if report_id is not None:
            query = 'SELECT COUNT(*) FROM pnl_reports'
            results = cursor.execute('SELECT COUNT(*) FROM pnl_reports').fetchone()
            total_filter_count = results[0]
        else:
            total_filter_count = len(reports)

        return _get_reports_or_events_maybe_limit(
            entry_type='reports',
            entries=reports,
            entries_found=total_filter_count,
            with_limit=with_limit,
        )

    def purge_report_data(self, report_id: int) -> None:
        """Deletes all report data of the given report from the DB

        Raises InputError if the report did not exist in the DB.
        """
        cursor = self.db.conn_transient.cursor()
        cursor.execute('DELETE FROM pnl_reports WHERE identifier=?', (report_id,))
        if cursor.rowcount != 1:
            raise InputError(
                f'Could not delete PnL report {report_id} from the DB. Report was not found',
            )
        self.db.conn.commit()
        self.db.update_last_write()

    def add_report_data(self, report_id: int, time: Timestamp, event: NamedJson) -> None:
        """Adds a new entry to a transient report for the PnL history in a given time range
        May raise:
        - DeserializationError if there is a conflict at serialization of the event
        - InputError if the event can not be written to the DB. Probably report id does not exist.
        """
        cursor = self.db.conn_transient.cursor()
        query = """
        INSERT INTO pnl_events(
            report_id, timestamp, event_type, data
        )
        VALUES(?, ?, ?, ?);"""
        try:
            cursor.execute(query, (report_id, time) + event.to_db_tuple())
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            raise InputError(
                f'Could not write {event} data to the DB due to {str(e)}. '
                f'Probably report {report_id} does not exist?',
            ) from e
        self.db.conn_transient.commit()

    def get_report_data(
            self,
            filter_: ReportDataFilterQuery,
            with_limit: bool,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Retrieve the event data of a PnL report depending on the given filter

        May raise:
        - InputError if the report ID does not exist in the DB
        """
        cursor = self.db.conn_transient.cursor()
        report_id = filter_.report_id
        query_result = cursor.execute(
            'SELECT COUNT(*) FROM pnl_reports WHERE identifier=?',
            (report_id,),
        )
        if query_result.fetchone()[0] != 1:
            raise InputError(
                f'Tried to get PnL events from non existing report with id {report_id}',
            )

        query, bindings = filter_.prepare()
        query = 'SELECT event_type, data FROM pnl_events ' + query
        results = cursor.execute(query, bindings)

        records = []
        for result in results:
            try:
                record = NamedJson.deserialize_from_db(result).data
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
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

        return _get_reports_or_events_maybe_limit(
            entry_type='events',
            entries_found=total_filter_count,
            entries=records,
            with_limit=with_limit,
        )
