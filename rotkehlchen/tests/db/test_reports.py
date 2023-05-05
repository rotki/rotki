from rotkehlchen.accounting.pnl import PnlTotals
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.tests.utils.constants import A_GBP


def test_report_settings(database):
    dbreport = DBAccountingReports(database)

    settings = DBSettings(
        main_currency=A_GBP,
        calculate_past_cost_basis=False,
        include_gas_costs=False,
        account_for_assets_movements=True,
        pnl_csv_have_summary=False,
        pnl_csv_with_formulas=True,
        taxfree_after_period=15,
    )
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
    assert len(returned_settings) == 9
    for x in ('account_for_assets_movements', 'calculate_past_cost_basis', 'include_crypto2crypto', 'include_gas_costs', 'profit_currency', 'taxfree_after_period', 'cost_basis_method', 'eth_staking_taxable_after_withdrawal_enabled', 'include_fees_in_cost_basis'):  # noqa: E501
        setting_name = 'main_currency' if x == 'profit_currency' else x
        if setting_name == 'cost_basis_method':
            value = settings.cost_basis_method.serialize()
        else:
            value = getattr(settings, setting_name)
        assert returned_settings[x] == value
