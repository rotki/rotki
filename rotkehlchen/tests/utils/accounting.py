import csv
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from rotkehlchen.accounting.export.csv import FILENAME_ALL_CSV
from rotkehlchen.accounting.mixins.event import AccountingEventMixin
from rotkehlchen.accounting.processed_event import ProcessedAccountingEvent
from rotkehlchen.constants import ZERO
from rotkehlchen.db.reports import DBAccountingReports, ReportDataFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.types import Timestamp

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.db.settings import DBSettings


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


def assert_csv_export(
        accountant: 'Accountant',
        expected_pnl: FVal,
) -> None:
    """Test the contents of the csv export match the actual result"""
    csvexporter = accountant.csvexporter
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        # first make sure we export without formulas
        csvexporter.settings = csvexporter.settings._replace(pnl_csv_with_formulas=False)
        accountant.csvexporter.export(
            events=accountant.pots[0].processed_events,
            pnls=accountant.pots[0].pnls,
            directory=tmpdir,
        )

        with open(tmpdir / FILENAME_ALL_CSV, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            calculated_pnl = ZERO
            for row in reader:
                calculated_pnl += FVal(row['pnl'])

        assert expected_pnl.is_close(calculated_pnl)
