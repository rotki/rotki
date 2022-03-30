from typing import Any, Dict, List, Tuple

from rotkehlchen.accounting.mixins.event import AccountingEventMixin
from rotkehlchen.accounting.processed_event import ProcessedAccountingEvent
from rotkehlchen.db.reports import DBAccountingReports, ReportDataFilterQuery
from rotkehlchen.types import Timestamp


def accounting_history_process(
        accountant,
        start_ts: Timestamp,
        end_ts: Timestamp,
        history_list: List[AccountingEventMixin],
) -> Tuple[Dict[str, Any], List[ProcessedAccountingEvent]]:
    report_id = accountant.process_history(
        start_ts=start_ts,
        end_ts=end_ts,
        events=history_list,
    )
    dbpnl = DBAccountingReports(accountant.csvexporter.database)
    report = dbpnl.get_reports(report_id=report_id, with_limit=False)[0][0]
    events = dbpnl.get_report_data(
        filter_=ReportDataFilterQuery.make(report_id=1),
        with_limit=False,
    )[0]
    return report, events
