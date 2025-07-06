"""
Database reports functionality

This module has been temporarily removed as part of the ProcessedAccountingEvent removal.
The database reports functionality needs to be completely rethought to work with the new
system where history events are decorated with accounting information rather than creating
separate ProcessedAccountingEvent objects.

TODO: Reimplement database reports to work with HistoryEventWithAccounting
"""
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.pnl import PnlTotals
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.misc import InputError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.filtering import ReportDataFilterQuery


class DBAccountingReports:
    """Placeholder database reports - functionality removed pending redesign"""

    def __init__(self, database: 'DBHandler'):
        self.db = database
        log.warning('Database reports functionality removed and needs redesign')

    def add_report(
            self,
            first_processed_timestamp: Timestamp,
            start_ts: Timestamp,
            end_ts: Timestamp,
            settings: DBSettings,
    ) -> int:
        """Placeholder add_report method"""
        log.error('add_report: functionality removed and needs redesign')
        raise InputError('Database reports functionality removed and needs redesign')

    def add_report_overview(
            self,
            report_id: int,
            last_processed_timestamp: Timestamp,
            processed_actions: int,
            total_actions: int,
            pnls: PnlTotals,
    ) -> None:
        """Placeholder add_report_overview method"""
        log.error('add_report_overview: functionality removed and needs redesign')
        raise InputError('Database reports functionality removed and needs redesign')

    def get_reports(
            self,
            report_id: int | None,
            with_limit: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        """Placeholder get_reports method"""
        log.error('get_reports: functionality removed and needs redesign')
        return [], 0

    def purge_report_data(self, report_id: int) -> None:
        """Placeholder purge_report_data method"""
        log.error('purge_report_data: functionality removed and needs redesign')
        raise InputError('Database reports functionality removed and needs redesign')

    def add_report_data(
            self,
            report_id: int,
            time: Timestamp,
            ts_converter: Any,
            event: Any,
    ) -> None:
        """Placeholder add_report_data method"""
        log.error('add_report_data: functionality removed and needs redesign')
        raise InputError('Database reports functionality removed and needs redesign')

    def get_report_data(
            self,
            filter_: 'ReportDataFilterQuery',
            with_limit: bool,
    ) -> tuple[list, int, int]:
        """Placeholder get_report_data method"""
        log.error('get_report_data: functionality removed and needs redesign')
        return [], 0, 0
