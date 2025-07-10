import logging
from collections.abc import Callable
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Literal, overload

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.pnl import PnlTotals
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.asset import WrongAssetType
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.filtering import ReportDataFilterQuery


@overload
def _get_reports_or_events_maybe_limit(
        entry_type: Literal['events'],
        entries_found: int,
        entries_total: int,
        entries: list[ProcessedAccountingEvent],
        with_limit: bool,
        limit: int,
) -> tuple[list[ProcessedAccountingEvent], int, int]:
    ...


@overload
def _get_reports_or_events_maybe_limit(
        entry_type: Literal['events'],
        entries_found: int,
        entries_total: None,
        entries: list[ProcessedAccountingEvent],
        with_limit: bool,
        limit: int,
) -> tuple[list[ProcessedAccountingEvent], int, None]:
    ...


@overload
def _get_reports_or_events_maybe_limit(
        entry_type: Literal['reports'],
        entries_found: int,
        entries_total: int,
        entries: list[dict[str, Any]],
        with_limit: bool,
        limit: int,
) -> tuple[list[dict[str, Any]], int, int]:
    ...


@overload
def _get_reports_or_events_maybe_limit(
        entry_type: Literal['reports'],
        entries_found: int,
        entries_total: None,
        entries: list[dict[str, Any]],
        with_limit: bool,
        limit: int,
) -> tuple[list[dict[str, Any]], int, None]:
    ...


def _get_reports_or_events_maybe_limit(
        entry_type: Literal['events', 'reports'],
        entries_found: int,
        entries_total: int | None,
        entries: list[dict[str, Any]] | list[ProcessedAccountingEvent],
        with_limit: bool,
        limit: int,
) -> tuple[list[dict[str, Any]] | list[ProcessedAccountingEvent], int, int | None]:
    if with_limit is False:
        return entries, entries_found, entries_total

    returning_entries_length = min(limit, len(entries))

    return entries[:returning_entries_length], entries_found, entries_total


class DBAccountingReports:

    def __init__(self, database: 'DBHandler'):
        self.db = database

    def add_report(
            self,
            first_processed_timestamp: Timestamp,
            start_ts: Timestamp,
            end_ts: Timestamp,
            settings: DBSettings,
    ) -> int:
        with self.db.transient_write() as cursor:
            timestamp = ts_now()
            query = """
            INSERT INTO pnl_reports(
                timestamp, start_ts, end_ts, first_processed_timestamp,
                last_processed_timestamp, processed_actions, total_actions
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)"""
            cursor.execute(
                query,
                (timestamp, start_ts, end_ts, first_processed_timestamp,
                 0, 0, 0,  # will be set later
                 ),
            )
            report_id = cursor.lastrowid
            cursor.executemany(
                'INSERT OR IGNORE INTO pnl_report_settings(report_id, name, type, value) '
                'VALUES(?, ?, ?, ?)',
                [
                    (report_id, 'profit_currency', 'string', settings.main_currency.identifier),
                    (report_id, 'taxfree_after_period', 'integer', settings.taxfree_after_period),
                    (report_id, 'include_crypto2crypto', 'bool', settings.include_crypto2crypto),
                    (report_id, 'calculate_past_cost_basis', 'bool', settings.calculate_past_cost_basis),  # noqa: E501
                    (report_id, 'include_gas_costs', 'bool', settings.include_gas_costs),
                    (report_id, 'cost_basis_method', 'string', settings.cost_basis_method.serialize()),  # noqa: E501
                    (report_id, 'eth_staking_taxable_after_withdrawal_enabled', 'bool', settings.eth_staking_taxable_after_withdrawal_enabled),  # noqa: E501
                    (report_id, 'include_fees_in_cost_basis', 'bool', settings.include_fees_in_cost_basis),  # noqa: E501
                ])

        return report_id

    def add_report_overview(
            self,
            report_id: int,
            last_processed_timestamp: Timestamp,
            processed_actions: int,
            total_actions: int,
            pnls: PnlTotals,
    ) -> None:
        """Inserts the report overview data

        May raise:
        - InputError if the given report id does not exist
        """
        with self.db.transient_write() as cursor:
            cursor.execute(
                'UPDATE pnl_reports SET last_processed_timestamp=?,'
                ' processed_actions=?, total_actions=? WHERE identifier=?',
                (last_processed_timestamp, processed_actions, total_actions, report_id),
            )
            if cursor.rowcount != 1:
                raise InputError(
                    f'Could not insert overview for {report_id}. '
                    f'Report id could not be found in the DB',
                )

            tuples = []
            for event_type, entry in pnls.items():
                tuples.append((report_id, event_type.serialize(), str(entry.taxable), str(entry.free)))  # noqa: E501
            cursor.executemany(
                'INSERT OR IGNORE INTO pnl_report_totals(report_id, name, taxable_value, free_value) VALUES(?, ?, ?, ?)',  # noqa: E501
                tuples,
            )

    def get_reports(
            self,
            report_id: int | None,
            with_limit: bool,
            limit: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Queries all historical saved PnL reports.

        If `with_limit` is true then the api limit is applied
        """
        bindings: tuple | tuple[int] = ()
        query = 'SELECT * from pnl_reports'
        reports: list[dict[str, Any]] = []
        if report_id is not None:
            bindings = (report_id,)
            query += ' WHERE identifier=?'

        with self.db.conn_transient.read_ctx() as cursor:
            cursor.execute(query, bindings)
            for report in cursor:
                this_report_id = report[0]
                with self.db.conn_transient.read_ctx() as other_cursor:
                    other_cursor.execute(
                        'SELECT name, taxable_value, free_value FROM pnl_report_totals WHERE report_id=?',  # noqa: E501
                        (this_report_id,),
                    )
                    overview = {x[0]: {'taxable': x[1], 'free': x[2]} for x in other_cursor}
                    other_cursor.execute(
                        'SELECT name, type, value FROM pnl_report_settings WHERE report_id=?',
                        (this_report_id,),
                    )
                    settings = {}
                    for x in other_cursor:
                        if x[1] == 'integer':
                            settings[x[0]] = int(x[2])
                        elif x[1] == 'bool':
                            settings[x[0]] = x[2] == '1'
                        else:
                            settings[x[0]] = x[2]
                    reports.append({
                        'identifier': this_report_id,
                        'timestamp': report[1],
                        'start_ts': report[2],
                        'end_ts': report[3],
                        'first_processed_timestamp': report[4],
                        'last_processed_timestamp': report[5],
                        'processed_actions': report[6],
                        'total_actions': report[7],
                        'overview': overview,
                        'settings': settings,
                    })

            if report_id is not None:
                results = cursor.execute('SELECT COUNT(*) FROM pnl_reports').fetchone()
                total_filter_count = results[0]
            else:
                total_filter_count = len(reports)

        entries, entries_found, _ = _get_reports_or_events_maybe_limit(
            entry_type='reports',
            entries=reports,
            entries_found=total_filter_count,
            entries_total=None,
            with_limit=with_limit,
            limit=limit,
        )

        return entries, entries_found

    def purge_report_data(self, report_id: int) -> None:
        """Deletes all report data of the given report from the DB

        Raises InputError if the report did not exist in the DB.
        """
        with self.db.transient_write() as cursor:
            cursor.execute('DELETE FROM pnl_reports WHERE identifier=?', (report_id,))
            if cursor.rowcount != 1:
                raise InputError(
                    f'Could not delete PnL report {report_id} from the DB. Report was not found',
                )

    def add_report_data(
            self,
            report_id: int,
            time: Timestamp,
            ts_converter: Callable[[Timestamp], str],
            event: ProcessedAccountingEvent,
    ) -> None:
        """Adds a new entry to a transient report for the PnL history in a given time range
        May raise:
        - DeserializationError if there is a conflict at serialization of the event
        - InputError if the event can not be written to the DB. Probably report id does not exist.
        """
        data = event.serialize_for_db(ts_converter)

        try:
            asset_symbol = event.asset.symbol_or_name()
        except WrongAssetType:
            asset_symbol = None

        query = """
        INSERT INTO pnl_events(
            report_id, timestamp, data, pnl_taxable, pnl_free, asset
        )
        VALUES(?, ?, ?, ?, ?, ?);"""
        with self.db.transient_write() as cursor:
            try:
                cursor.execute(
                    query,
                    (
                        report_id,
                        time,
                        data,
                        str(event.pnl.taxable),
                        str(event.pnl.free),
                        asset_symbol,
                    ),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                raise InputError(
                    f'Could not write {event} data to the DB due to {e!s}. '
                    f'Probably report {report_id} does not exist?',
                ) from e

    def get_report_data(
            self,
            filter_: 'ReportDataFilterQuery',
            with_limit: bool,
            limit: int,
    ) -> tuple[list[ProcessedAccountingEvent], int, int]:
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
        query = f'SELECT timestamp, data FROM pnl_events {query}'
        cursor.execute(query, bindings)

        records = []
        for result in cursor:
            try:
                record = ProcessedAccountingEvent.deserialize_from_db(result[0], result[1])
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
                    f'Error deserializing AccountingEvent from the DB. Skipping it.'
                    f'Error was: {e!s}',
                )
                continue

            records.append(record)

        entries_found = len(records)
        if filter_.pagination is not None:
            no_pagination_filter = deepcopy(filter_)
            no_pagination_filter.pagination = None
            query, bindings = no_pagination_filter.prepare()
            entries_found = cursor.execute(f'SELECT COUNT(*) FROM pnl_events {query}', bindings).fetchone()[0]  # noqa: E501

        return _get_reports_or_events_maybe_limit(
            entry_type='events',
            entries_found=entries_found,
            entries_total=cursor.execute('SELECT COUNT(*) FROM pnl_events').fetchone()[0],
            entries=records,
            with_limit=with_limit,
            limit=limit,
        )
