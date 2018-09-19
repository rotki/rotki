import { form_button, form_entry, invisible_anchor, loading_placeholder, page_header, table_html } from './elements';
import { date_text_to_utc_ts, prompt_directory_select_async, showError, showInfo, showWarning, timestamp_to_date, utc_now } from './utils';
import { create_task, monitor_add_callback } from './monitor';
import { pages, settings } from './settings';
import { ActionResult } from './model/action-result';
import { AsyncQueryResult } from './model/balance-result';
import { TradeHistoryOverview, TradeHistoryResult } from './model/trade-history-result';
import { EventEntry } from './model/event-entry';
import { client } from './rotkehlchen_service';

export function create_taxreport_ui() {
    let str = page_header('Tax Report');
    str += form_entry('Start Date', 'analysis_start_date');
    str += form_entry('End Date', 'analysis_end_date');
    str += form_button('Generate Report', 'generate_report');
    str += invisible_anchor('tax_report_anchor');
    str += table_html(2, 'report_overview');
    str += table_html(10, 'report_details');
    $('#page-wrapper').html(str);
}

export function add_taxreport_listeners() {
    $('#analysis_start_date').datetimepicker({format: settings.datetime_format});
    $('#analysis_end_date').datetimepicker({format: settings.datetime_format});
    $('#generate_report').click(generate_report_callback);
    $('#export_csv').click(export_csv_callback);
}

function clean_taxreport_ui() {
    $('#export_csv').remove();
    $('#report_overview_table_wrapper').parent().remove();
    $('#report_details_table_wrapper').parent().remove();
    let str = table_html(2, 'report_overview');
    str += table_html(10, 'report_details');
    $(str).insertAfter('#tax_report_anchor');
}

function export_csv_callback(event: JQuery.Event) {
    event.preventDefault();
    prompt_directory_select_async((directories: string[]) => {
        if (directories === undefined) {
            return;
        }
        const dir = directories[0];
        client.invoke(
            'export_processed_history_csv',
            dir,
            (error: Error, res: ActionResult<boolean>) => {
                if (error || res == null) {
                    showError('Exporting History to CSV error', error.message);
                    return;
                }
                if (!res.result) {
                    showError('Exporting History to CSV error', res.message);
                    return;
                }
                showInfo('Success', 'History exported to CVS successfully');
            });
    });
}

function generate_report_callback(event: JQuery.Event) {
    event.preventDefault();
    const start_ts_text = $('#analysis_start_date').val() as string;
    const end_ts_text = $('#analysis_end_date').val() as string;

    const start_ts = date_text_to_utc_ts(start_ts_text);
    const end_ts = date_text_to_utc_ts(end_ts_text);
    const now_ts = utc_now();
    if (end_ts <= start_ts) {
        showError('Input Error', 'The end time should be after the start time.');
        return;
    }

    if (end_ts > now_ts) {
        showError('Input Error', 'The end time should not be in the future.');
        return;
    }

    if (($('#tax_report_loading').length)) {
        showError(
            'In Progress Error',
            'A tax report is already being generated. Please wait until the ' +
            'current report is finished until you can generate a new one'
        );
        return;
    }
    const str = loading_placeholder('tax_report_loading');
    $(str).insertAfter('#tax_report_anchor');

    clean_taxreport_ui();
    client.invoke(
        'process_trade_history_async',
        start_ts,
        end_ts,
        (error: Error, res: AsyncQueryResult) => {
            if (error || res == null) {
                showError('Trade History Processing Error', error.message);
                return;
            }
            // else
            create_task(
                res.task_id,
                'process_trade_history',
                'Create tax report',
                false,
                true
            );
        });
}

function show_float_or_empty(data: string) {
    if (data === '') {
        return '';
    }
    return parseFloat(data).toFixed(settings.floating_precision);
}

function create_taxreport_overview(results: TradeHistoryOverview) {
    const data = [];
    for (const result in results) {
        if (results.hasOwnProperty(result)) {
            const row = {'result': result, 'value': results[result]};
            data.push(row);
        }
    }
    const init_obj = {
        'data': data,
        'columns': [
            {'data': 'result', 'title': 'Result'},
            {
                'data': 'value',
                'title': settings.main_currency.ticker_symbol + ' value',
                'render': (dat: string) => {
                    // no need for conversion here as it's already in main_currency
                    return parseFloat(dat).toFixed(settings.floating_precision);
                }
            }
        ],
        'order': [[1, 'desc']]
    };
    $('#report_overview_table').DataTable(init_obj);
}

function create_taxreport_details(all_events: EventEntry[]) {
    const init_obj = {
        'data': all_events,
        'columns': [
            {'data': 'type', 'title': 'Type'},
            {
                'data': 'paid_in_profit_currency',
                'title': 'Paid in ' + settings.main_currency.ticker_symbol,
                'render': (data: string) => {
                    // it's already in main currency
                    return show_float_or_empty(data);
                }
            },
            {'data': 'paid_asset', 'title': 'Paid Asset'},
            {
                'data': 'paid_in_asset',
                'title': 'Paid In Asset',
                'render': (data: string) => show_float_or_empty(data)
            },
            {
                'data': 'taxable_amount',
                'title': 'Taxable Amount',
                'render': (data: string) => show_float_or_empty(data)
            },
            {
                'data': 'taxable_bought_cost',
                'title': 'Taxable Bought Cost',
                'render': (data: string) => show_float_or_empty(data)
            },
            {'data': 'received_asset', 'title': 'Received Asset'},
            {
                'data': 'received_in_profit_currency',
                'title': 'Received in ' + settings.main_currency.ticker_symbol,
                'render': (data: string) => {
                    // it's already in main currency
                    return show_float_or_empty(data);
                }
            },
            {
                'data': 'time',
                'title': 'Time',
                'render': (data: number, type: string) => {
                    if (type === 'sort') {
                        return data;
                    }
                    return timestamp_to_date(data);
                }
            },
            {'data': 'is_virtual', 'title': 'Virtual ?'}
        ],
        'pageLength': 25,
        'order': [[8, 'asc']]
    };
    $('#report_details_table').DataTable(init_obj);
}

export function init_taxreport() {
    monitor_add_callback('process_trade_history', (result: ActionResult<TradeHistoryResult>) => {
        $('#tax_report_loading').remove();        
        if (result.error) {
            showError(
                'Trade History Query Error',
                `Querying trade history died because of: ${result.error}. Check the logs for more details`
            );
            return;
        }
        if (result.message !== '') {
            showWarning(
                'Trade History Query Warning',
                'During trade history query we got:' + result.message + '. History report is probably not complete.'
            );
        }
        if ($('#elementId').length === 0) {
            const str = form_button('Export CSV', 'export_csv');
            $(str).insertAfter('#generate_report');
            $('#export_csv').click(export_csv_callback);
        }
        create_taxreport_overview(result.result.overview);
        create_taxreport_details(result.result.all_events);
        // also save the page
        pages.page_taxreport = $('#page-wrapper').html();
    });
}
