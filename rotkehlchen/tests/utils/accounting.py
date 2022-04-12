import csv
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from rotkehlchen.accounting.export.csv import CSV_INDEX_OFFSET, FILENAME_ALL_CSV
from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR
from rotkehlchen.db.reports import DBAccountingReports, ReportDataFilterQuery
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.types import AssetAmount, Fee, Location, Price, Timestamp, TradeType
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant


history1 = [
    Trade(
        timestamp=Timestamp(1446979735),
        location=Location.EXTERNAL,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(82)),
        rate=Price(FVal('268.678317859')),
        fee=None,
        fee_currency=None,
        link=None,
    ), Trade(
        timestamp=Timestamp(1446979735),
        location=Location.EXTERNAL,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(1450)),
        rate=Price(FVal('0.2315893')),
        fee=None,
        fee_currency=None,
        link=None,
    ), Trade(
        timestamp=Timestamp(1473505138),  # cryptocompare hourly BTC/EUR price: 556.435
        location=Location.POLONIEX,
        base_asset=A_ETH,  # cryptocompare hourly ETH/EUR price: 10.36
        quote_asset=A_BTC,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal(50)),
        rate=Price(FVal('0.01858275')),
        fee=Fee(FVal('0.06999999999999999')),
        fee_currency=A_ETH,
        link=None,
    ), Trade(
        timestamp=Timestamp(1475042230),  # cryptocompare hourly BTC/EUR price: 537.805
        location=Location.POLONIEX,
        base_asset=A_ETH,  # cryptocompare hourly ETH/EUR price: 11.925
        quote_asset=A_BTC,
        trade_type=TradeType.SELL,
        amount=AssetAmount(FVal(25)),
        rate=Price(FVal('0.02209898')),
        fee=Fee(FVal('0.00082871175')),
        fee_currency=A_BTC,
        link=None,
    ),
]


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


def check_pnls_and_csv(accountant: 'Accountant', expected_pnls: PnlTotals) -> None:
    pnls = accountant.pots[0].pnls
    assert_pnl_totals_close(expected=expected_pnls, got=pnls)
    assert_csv_export(accountant, expected_pnls)
    # also check the totals
    assert pnls.taxable.is_close(expected_pnls.taxable)
    assert pnls.free.is_close(expected_pnls.free)


def assert_pnl_totals_close(expected: PnlTotals, got: PnlTotals) -> None:
    # ignore prefork acquisitions for these tests
    got.pop(AccountingEventType.PREFORK_ACQUISITION)

    assert len(expected) == len(got)
    for event_type, expected_pnl in expected.items():
        assert expected_pnl.free.is_close(got[event_type].free)
        assert expected_pnl.taxable.is_close(got[event_type].taxable)


def _check_boolean_settings(row: Dict[str, Any], accountant: 'Accountant'):
    """Check boolean settings are exported correctly to the spreadsheet CSV"""
    booleans = ('include_crypto2crypto', 'include_gas_costs', 'account_for_assets_movements', 'calculate_past_cost_basis')  # noqa: E501

    for setting in booleans:
        if row['free_amount'] == setting:
            assert row['taxable_amount'] == str(getattr(accountant.pots[0].settings, setting))
            break


def _check_summaries_row(row: Dict[str, Any], accountant: 'Accountant'):
    if row['free_amount'] == 'rotki version':
        assert row['taxable_amount'] == get_current_version(check_for_updates=False).our_version
    elif row['free_amount'] == 'taxfree_after_period':
        assert row['taxable_amount'] == str(accountant.pots[0].settings.taxfree_after_period)
    else:
        _check_boolean_settings(row, accountant)


def assert_csv_export(
        accountant: 'Accountant',
        expected_pnls: PnlTotals,
) -> None:
    """Test the contents of the csv export match the actual result"""
    csvexporter = accountant.csvexporter
    if len(accountant.pots[0].processed_events) == 0:
        return  # nothing to do for no events as no csv is generated

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        # first make sure we export without formulas
        csvexporter.settings = csvexporter.settings._replace(pnl_csv_with_formulas=False)
        accountant.csvexporter.export(
            events=accountant.pots[0].processed_events,
            pnls=accountant.pots[0].pnls,
            directory=tmpdir,
        )

        calculated_pnls = PnlTotals()
        with open(tmpdir / FILENAME_ALL_CSV, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['type'] == '':
                    break  # have summaries and reached the end

                event_type = AccountingEventType.deserialize(row['type'])
                taxable = FVal(row['pnl_taxable'])
                free = FVal(row['pnl_free'])
                if taxable != ZERO or free != ZERO:
                    calculated_pnls[event_type] += PNL(taxable=taxable, free=free)

        assert_pnl_totals_close(expected_pnls, calculated_pnls)

        # export with formulas and summary
        csvexporter.settings = csvexporter.settings._replace(pnl_csv_with_formulas=True, pnl_csv_have_summary=True)  # noqa: E501
        accountant.csvexporter.export(
            events=accountant.pots[0].processed_events,
            pnls=accountant.pots[0].pnls,
            directory=tmpdir,
        )
        index = CSV_INDEX_OFFSET
        at_summaries = False
        with open(tmpdir / FILENAME_ALL_CSV, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if at_summaries:
                    _check_summaries_row(row, accountant)
                    continue

                if row['type'] == '':
                    at_summaries = True
                    continue  # have summaries and reached the end

                if row['pnl_taxable'] != '0':
                    value = f'G{index}*H{index}'
                    if row['type'] == AccountingEventType.TRADE and 'Amount out' in row['notes']:
                        assert row['pnl_taxable'] == f'={value}-J{index}'
                    elif row['type'] == AccountingEventType.FEE:
                        assert row['pnl_taxable'] == f'={value}+{value}-J{index}'

                if row['pnl_free'] != '0':
                    value = f'F{index}*H{index}'
                    if row['type'] == AccountingEventType.TRADE and 'Amount out' in row['notes']:
                        assert row['pnl_free'] == f'={value}-L{index}'
                    elif row['type'] == AccountingEventType.FEE:
                        assert row['pnl_free'] == f'={value}+{value}-:{index}'

                index += 1
