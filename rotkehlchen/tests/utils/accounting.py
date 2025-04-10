import csv
import dataclasses
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import requests

from rotkehlchen.accounting.export.csv import CSV_INDEX_OFFSET, FILENAME_ALL_CSV
from rotkehlchen.accounting.mixins.event import AccountingEventMixin, AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.api.server import APIServer
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USDC, A_WBTC
from rotkehlchen.db.filtering import ReportDataFilterQuery
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.types import Fee, Location, Price, Timestamp, TimestampMS, TradeType
from rotkehlchen.utils.version_check import get_current_version

if TYPE_CHECKING:
    from rotkehlchen.accounting.accountant import Accountant
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.tests.fixtures.google import GoogleService


TIMESTAMP_1_MS = TimestampMS(1000)
TIMESTAMP_1_SEC = Timestamp(1)

MOCKED_PRICES = {
    A_WBTC.identifier: {
        'EUR': {
            TIMESTAMP_1_SEC: Price(ONE),
        },
    },
    A_USDC.identifier: {
        'EUR': {
            TIMESTAMP_1_SEC: Price(ONE),
        },
    },
}


history1 = [
    Trade(
        timestamp=Timestamp(1446979735),
        location=Location.EXTERNAL,
        base_asset=A_BTC,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=FVal(82),
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
        amount=FVal(1450),
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
        amount=FVal(50),
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
        amount=FVal(25),
        rate=Price(FVal('0.02209898')),
        fee=Fee(FVal('0.00082871175')),
        fee_currency=A_BTC,
        link=None,
    ),
]


def _get_pnl_report_after_processing(
        report_id: int,
        database: 'DBHandler',
) -> tuple[dict[str, Any], list[ProcessedAccountingEvent]]:
    dbpnl = DBAccountingReports(database)
    report = dbpnl.get_reports(report_id=report_id, with_limit=False)[0][0]
    events = dbpnl.get_report_data(
        filter_=ReportDataFilterQuery.make(report_id=1),
        with_limit=False,
    )[0]
    return report, events


def accounting_create_and_process_history(
        rotki: 'Rotkehlchen',
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> tuple[dict[str, Any], list[ProcessedAccountingEvent]]:
    report_id, error_or_empty = rotki.process_history(start_ts=start_ts, end_ts=end_ts)
    assert error_or_empty == ''
    return _get_pnl_report_after_processing(report_id=report_id, database=rotki.data.db)


def accounting_history_process(
        accountant: 'Accountant',
        start_ts: Timestamp,
        end_ts: Timestamp,
        history_list: Sequence[AccountingEventMixin],
) -> tuple[dict[str, Any], list[ProcessedAccountingEvent]]:
    report_id = accountant.process_history(
        start_ts=start_ts,
        end_ts=end_ts,
        events=history_list,
    )
    return _get_pnl_report_after_processing(report_id=report_id, database=accountant.csvexporter.database)  # noqa: E501


def check_pnls_and_csv(
        accountant: 'Accountant',
        expected_pnls: PnlTotals,
        google_service: Optional['GoogleService'] = None,
) -> None:
    pnls = accountant.pots[0].pnls
    assert_pnl_totals_close(expected=expected_pnls, got=pnls)
    assert_csv_export(accountant, expected_pnls, google_service)
    # also check the totals
    assert pnls.taxable.is_close(expected_pnls.taxable)
    assert pnls.free.is_close(expected_pnls.free)


def assert_pnl_totals_close(expected: PnlTotals, got: PnlTotals) -> None:
    # ignore prefork acquisitions for these tests
    got.pop(AccountingEventType.PREFORK_ACQUISITION)

    iterate_pnl = got
    check_pnl = expected
    if len(expected) >= len(got):
        iterate_pnl = expected
        check_pnl = got

    reduced_length = 0
    for event_type, iterate_pnl_val in iterate_pnl.items():
        check_pnl_val = check_pnl.get(event_type)
        if check_pnl_val is None:
            if iterate_pnl_val.free == ZERO and iterate_pnl_val.taxable == ZERO:
                reduced_length += 1
                continue
            # else
            raise AssertionError(f'Expected {event_type}: {iterate_pnl_val}')

        assert iterate_pnl_val.free.is_close(check_pnl_val.free)
        assert iterate_pnl_val.taxable.is_close(check_pnl_val.taxable)

    assert len(iterate_pnl) == len(check_pnl) + reduced_length


def _check_boolean_settings(row: dict[str, Any], accountant: 'Accountant'):
    """Check boolean settings are exported correctly to the spreadsheet CSV"""
    booleans = ('include_crypto2crypto', 'include_gas_costs', 'calculate_past_cost_basis')

    for setting in booleans:
        if row['free_amount'] == setting:
            assert row['taxable_amount'] == str(getattr(accountant.pots[0].settings, setting))
            break


def _check_summaries_row(row: dict[str, Any], accountant: 'Accountant'):
    if row['free_amount'] == 'rotki version':
        assert row['taxable_amount'] == str(get_current_version().our_version)
    elif row['free_amount'] == 'taxfree_after_period':
        assert row['taxable_amount'] == str(accountant.pots[0].settings.taxfree_after_period)
    else:
        _check_boolean_settings(row, accountant)


def _check_column(attribute: str, index: int, sheet_id: str, expected: dict[str, Any], got_columns: list[list[str]]):  # noqa: E501
    expected_value = FVal(expected[attribute])
    got_value = FVal(got_columns[index][0])
    msg = f'Sheet: {sheet_id}, row: {index + CSV_INDEX_OFFSET} {attribute} mismatch. {got_value} != {expected_value}'  # noqa: E501
    assert expected_value.is_close(got_value), msg


def _check_total(sheet_id: str, offset: int, total_type: str, expected_pnls: PnlTotals, result: list[dict[str, Any]]) -> bool:  # noqa: E501
    """Check each total line and return true if all lines are checked"""
    if total_type != 'TOTAL':  # must be a pnl total
        accounting_type = AccountingEventType.deserialize(total_type.removesuffix(' total'))
        assert accounting_type in expected_pnls

    for pnl_type in ('taxable', 'free'):
        if total_type == 'TOTAL':
            expected_value = getattr(expected_pnls, pnl_type)
        else:
            expected_value = getattr(expected_pnls[accounting_type], pnl_type)
        got_value = FVal(result[3 if pnl_type == 'taxable' else 4]['values'][offset][0])
        msg = f'Sheet: {sheet_id}, row: {offset} {pnl_type} {total_type} mismatch. {got_value} != {expected_value}'  # noqa: E501
        assert expected_value.is_close(got_value), msg

    return total_type == 'TOTAL'


def upload_csv_and_check(
        service: 'GoogleService',
        csv_data: list[dict[str, Any]],
        expected_csv_data: list[dict[str, Any]],
        expected_pnls: PnlTotals,
) -> None:
    """Creates a new google sheet, uploads the CSV and then checks it renders properly"""
    sheet_id = service.create_spreadsheet()
    service.add_rows(sheet_id=sheet_id, csv_data=csv_data)
    result = service.get_cell_ranges(
        sheet_id=sheet_id,
        range_names=['I2:I', 'J2:J', 'F2:F', 'G2:G', 'H2:H'],
    )
    # Check that the data length matches
    assert len(result[0]['values']) == len(expected_csv_data)
    assert len(result[1]['values']) == len(expected_csv_data)
    for idx, expected in enumerate(expected_csv_data):
        _check_column(
            attribute='pnl_taxable',
            index=idx,
            sheet_id=sheet_id,
            expected=expected,
            got_columns=result[0]['values'],
        )
        _check_column(
            attribute='pnl_free',
            index=idx,
            sheet_id=sheet_id,
            expected=expected,
            got_columns=result[1]['values'],
        )

    offset = len(expected_csv_data) + 2
    assert result[3]['values'][offset][0] == 'TAXABLE'
    assert result[4]['values'][offset][0] == 'FREE'
    offset += 1
    while offset < len(csv_data):
        should_break = _check_total(
            sheet_id=sheet_id,
            offset=offset,
            total_type=result[2]['values'][offset][0],
            expected_pnls=expected_pnls,
            result=result,
        )
        if should_break:
            break  # reached the end
        offset += 1


def assert_csv_export(
        accountant: 'Accountant',
        expected_pnls: PnlTotals,
        google_service: Optional['GoogleService'] = None,
) -> None:
    """Test the contents of the csv export match the actual result

    If google_service exists then it's also uploaded to a sheet to check the formular rendering
    """
    csvexporter = accountant.csvexporter
    if len(accountant.pots[0].processed_events) == 0:
        return  # nothing to do for no events as no csv is generated

    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        # first make sure we export without formulas
        csvexporter.settings = dataclasses.replace(csvexporter.settings, pnl_csv_with_formulas=False)  # noqa: E501
        accountant.csvexporter.export(
            events=accountant.pots[0].processed_events,
            pnls=accountant.pots[0].pnls,
            directory=tmpdir,
        )

        calculated_pnls = PnlTotals()
        expected_csv_data = []
        with open(tmpdir / FILENAME_ALL_CSV, newline='', encoding='utf8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                expected_csv_data.append(row)
                if row['type'] == '':
                    continue  # have summaries and reached the end

                event_type = AccountingEventType.deserialize(row['type'])
                taxable = FVal(row['pnl_taxable'])
                free = FVal(row['pnl_free'])
                calculated_pnls[event_type] += PNL(taxable=taxable, free=free)

        assert_pnl_totals_close(expected_pnls, calculated_pnls)

        # export with formulas and summary
        csvexporter.settings = dataclasses.replace(csvexporter.settings, pnl_csv_with_formulas=True, pnl_csv_have_summary=True)  # noqa: E501
        accountant.csvexporter.export(
            events=accountant.pots[0].processed_events,
            pnls=accountant.pots[0].pnls,
            directory=tmpdir,
        )
        index = CSV_INDEX_OFFSET
        at_summaries = False
        to_upload_data = []
        with open(tmpdir / FILENAME_ALL_CSV, newline='', encoding='utf8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                to_upload_data.append(row)

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

        if google_service is not None:
            upload_csv_and_check(
                service=google_service,
                csv_data=to_upload_data,
                expected_csv_data=expected_csv_data,
                expected_pnls=expected_pnls,
            )


def toggle_ignore_an_asset(
        rotkehlchen_api_server: APIServer,
        asset_to_ignore: Asset,
) -> None:
    """Utility function to add/remove an ignored asset"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    # check if the asset is already ignored
    with rotki.data.db.conn.read_ctx() as cursor:
        ignored_assets = rotki.data.db.get_ignored_asset_ids(cursor)
    already_ignored = asset_to_ignore.identifier in ignored_assets

    if already_ignored:
        # remove the asset from the ignored list
        response = requests.delete(
            api_url_for(
                rotkehlchen_api_server,
                'ignoredassetsresource',
            ), json={'assets': [asset_to_ignore.identifier]},
        )
        result = assert_proper_sync_response_with_result(response)
        assert asset_to_ignore.identifier not in result

        with rotki.data.db.conn.read_ctx() as cursor:
            result = rotki.data.db.get_ignored_asset_ids(cursor)
        assert asset_to_ignore.identifier not in result
        return

    # else add the asset to the ignored list
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'ignoredassetsresource',
        ), json={'assets': [asset_to_ignore.identifier]},
    )
    assert response.status_code == 200
    result = assert_proper_sync_response_with_result(response)
    assert asset_to_ignore.identifier in result['successful']

    with rotki.data.db.conn.read_ctx() as cursor:
        result = rotki.data.db.get_ignored_asset_ids(cursor)
    assert asset_to_ignore.identifier in result


def get_calculated_asset_amount(cost_basis, asset: Asset) -> FVal | None:
    """Get the amount of asset accounting has calculated we should have after
    the history has been processed on a cost basis object
    """
    asset_events = cost_basis.get_events(asset)

    amount = ZERO
    for acquisition_event in asset_events.acquisitions_manager.get_acquisitions():
        amount += acquisition_event.remaining_amount

    return amount if amount != ZERO else None
