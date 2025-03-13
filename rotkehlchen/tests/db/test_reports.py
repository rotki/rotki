from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.accounting.structures.processed_event import ProcessedAccountingEvent
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.db.filtering import ReportDataFilterQuery
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.types import Location, Price, Timestamp
from rotkehlchen.utils.misc import create_order_by_rules_list, timestamp_to_date


def setup_db_account_settings(database):
    """Setup accounting reports and settings db"""
    dbreport = DBAccountingReports(database)

    settings = DBSettings(
        main_currency=A_GBP,
        calculate_past_cost_basis=False,
        include_gas_costs=False,
        pnl_csv_have_summary=False,
        pnl_csv_with_formulas=True,
        taxfree_after_period=15,
    )

    return dbreport, settings


def test_report_settings(database):
    dbreport, settings = setup_db_account_settings(database)

    start_ts = 1
    first_processed_timestamp = 4
    last_processed_timestamp = 9
    end_ts = 10
    report_id = dbreport.add_report(
        first_processed_timestamp=first_processed_timestamp,
        start_ts=start_ts,
        end_ts=end_ts,
        settings=settings,
    )
    total_actions = 10
    processed_actions = 2
    dbreport.add_report_overview(
        report_id=report_id,
        last_processed_timestamp=last_processed_timestamp,
        processed_actions=processed_actions,
        total_actions=total_actions,
        pnls=PnlTotals(),
    )
    data, entries_num = dbreport.get_reports(report_id=report_id, with_limit=False)
    assert len(data) == 1
    assert entries_num == 1
    report = data[0]
    assert report['identifier'] == report_id
    assert report['start_ts'] == start_ts
    assert report['first_processed_timestamp'] == first_processed_timestamp
    assert report['last_processed_timestamp'] == last_processed_timestamp
    assert report['processed_actions'] == processed_actions
    assert report['total_actions'] == total_actions

    returned_settings = report['settings']
    assert len(returned_settings) == 8
    for x in ('calculate_past_cost_basis', 'include_crypto2crypto', 'include_gas_costs', 'profit_currency', 'taxfree_after_period', 'cost_basis_method', 'eth_staking_taxable_after_withdrawal_enabled', 'include_fees_in_cost_basis'):  # noqa: E501
        setting_name = 'main_currency' if x == 'profit_currency' else x
        if setting_name == 'cost_basis_method':
            value = settings.cost_basis_method.serialize()
        else:
            value = getattr(settings, setting_name)
        assert returned_settings[x] == value


def test_report_events_sort_by_columns(database):
    """Test that sorting by asset, pnl_taxable and timestamp works correctly"""
    timestamp_1_secs, timestamp_2_secs, eth_price_ts_1, eth_price_ts_2, half_amount, hundred, forty = Timestamp(1741634066), Timestamp(1741634100), FVal('2000'), FVal('2200'), FVal(0.5), FVal('100'), FVal('40')  # noqa: E501

    dbreport, settings = setup_db_account_settings(database)

    report_id = dbreport.add_report(
        first_processed_timestamp=timestamp_1_secs,
        start_ts=timestamp_1_secs,
        end_ts=timestamp_2_secs,
        settings=settings,
    )

    events = [
        ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Received 1 ETH',
            location=Location.ETHEREUM,
            timestamp=timestamp_1_secs,
            asset=A_ETH,
            free_amount=ONE,
            taxable_amount=ZERO,
            price=Price(eth_price_ts_1),
            pnl=PNL(free=ZERO, taxable=eth_price_ts_1),
            cost_basis=None,
            index=0,
            extra_data={},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Send 0.5 ETH to 0xABC',
            location=Location.ETHEREUM,
            timestamp=timestamp_2_secs,
            asset=A_ETH,
            free_amount=ZERO,
            taxable_amount=half_amount,
            price=Price(eth_price_ts_2),
            pnl=PNL(taxable=half_amount, free=ONE),
            cost_basis=None,
            index=1,
            extra_data={},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Received 100 DAI',
            location=Location.ETHEREUM,
            timestamp=timestamp_2_secs,
            asset=A_DAI,
            free_amount=hundred,
            taxable_amount=ZERO,
            price=Price(ONE),
            pnl=PNL(taxable=ZERO, free=hundred),
            cost_basis=None,
            index=0,
            extra_data={},
        ), ProcessedAccountingEvent(
            event_type=AccountingEventType.TRANSACTION_EVENT,
            notes='Send 40 DAI to 0xABC',
            location=Location.ETHEREUM,
            timestamp=timestamp_2_secs,
            asset=A_DAI,
            free_amount=ZERO,
            taxable_amount=forty,
            price=Price(ONE),
            pnl=PNL(taxable=forty, free=ZERO),
            cost_basis=None,
            index=0,
            extra_data={},
        ),
    ]

    for event in events:
        dbreport.add_report_data(
            report_id=report_id,
            time=event.timestamp,
            ts_converter=timestamp_to_date,
            event=event,
        )

    test_cases = [
        {
            'column': 'asset',
            'expected_values': [A_DAI, A_DAI, A_ETH, A_ETH],
            'check_field': lambda event: event.asset,
        }, {
            'column': 'pnl_free',
            'expected_values': [ZERO, ZERO, ONE, hundred],
            'check_field': lambda event: event.pnl.free,
        }, {
            'column': 'pnl_taxable',
            'expected_values': [ZERO, half_amount, forty, eth_price_ts_1],
            'check_field': lambda event: event.pnl.taxable,
        }, {
            'column': 'timestamp',
            'expected_values': [timestamp_1_secs, timestamp_2_secs, timestamp_2_secs, timestamp_2_secs],  # noqa: E501
            'check_field': lambda event: event.timestamp,
        },
    ]

    for test_case in test_cases:
        for is_ascending in (True, False):
            filter_query = ReportDataFilterQuery.make(
                order_by_rules=create_order_by_rules_list(
                    data={
                        'order_by_attributes': [test_case['column']],
                        'ascending': [is_ascending],
                    },
                    default_order_by_fields=['timestamp'],
                    default_ascending=[False],
                ),
                report_id=report_id,
            )

            results, _, _ = dbreport.get_report_data(filter_=filter_query, with_limit=True)
            for idx, event in enumerate(results):
                field_value_fn = test_case['check_field']
                field_value = field_value_fn(event)

                index = idx if is_ascending else len(results) - 1 - idx
                expected_value = test_case['expected_values'][index]
                assert field_value == expected_value
