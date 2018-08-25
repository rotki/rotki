import { format_currency_value, settings } from './settings';
import { form_button, form_entry, invisible_anchor, loading_placeholder, page_header, table_html } from './elements';
import { date_text_to_utc_ts, prompt_directory_select_async, showError, showInfo, showWarning, timestamp_to_date, utc_now } from './utils';
import client from './zerorpc_client';
import { create_task, monitor_add_callback } from './monitor';

export function create_taxreport_ui() {
    let str = page_header('Tax Report');
    str += form_entry('Start Date', 'analysis_start_date', '', '');
    str += form_entry('End Date', 'analysis_end_date', '', '');
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
    let str =  table_html(2, 'report_overview');
    str += table_html(10, 'report_details');
    $(str).insertAfter('#tax_report_anchor');
}

function export_csv_callback(event: any) {
    event.preventDefault();
    prompt_directory_select_async((directories) => {
        if (directories === undefined) {
            return;
        }
        let dir = directories[0];
        client.invoke(
            'export_processed_history_csv',
            dir,
            (error, res) => {
                if (error || res == null) {
                    showError('Exporting History to CSV error', error);
                    return;
                }
                if (!res['result']) {
                    showError('Exporting History to CSV error', res['message']);
                    return;
                }
                showInfo('Success', 'History exported to CVS successfully');
            });
    });
}

function generate_report_callback(event: any) {
    event.preventDefault();
    let start_ts = $('#analysis_start_date').val();
    let end_ts = $('#analysis_end_date').val();

    start_ts = date_text_to_utc_ts(start_ts);
    end_ts = date_text_to_utc_ts(end_ts);
    let now_ts = utc_now();
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
    let str = loading_placeholder('tax_report_loading');
    $(str).insertAfter('#tax_report_anchor');

    clean_taxreport_ui();
    client.invoke(
        'process_trade_history_async',
        start_ts,
        end_ts,
        (error, res) => {
            if (error || res == null) {
                showError('Trade History Processing Error', error);
                return;
            }
            // else
            create_task(
                res['task_id'],
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

function create_taxreport_overview(results: any) {
    $('#tax_report_loading').remove();

    let data = [];
    for (let result in results) {
        if (results.hasOwnProperty(result)) {
            let row = {'result': result, 'value': results[result]};
            data.push(row);
        }
    }
    let init_obj = {
        'data': data,
        'columns': [
            {'data': 'result', 'title': 'Result'},
            {
                'data': 'value',
                'title': settings.main_currency.ticker_symbol + ' value',
                'render': function (data: any, type: any, row: any) {
                    // no need for conversion here as it's already in main_currency
                    return parseFloat(data).toFixed(settings.floating_precision);
                }
            }
        ],
        'order': [[1, 'desc']]
    };
    $('#report_overview_table').DataTable(init_obj);
}

export function create_taxreport_details(all_events: any) {
    let init_obj = {
        'data': all_events,
        'columns': [
            {'data': 'type', 'title': 'Type'},
            {
                'data': 'paid_in_profit_currency',
                'title': 'Paid in ' + settings.main_currency.ticker_symbol,
                'render': function (data: any, type: any, row: any) {
                    // it's already in main currency
                    return show_float_or_empty(data);
                }
            },
            {'data': 'paid_asset', 'title': 'Paid Asset'},
            {
                'data': 'paid_in_asset',
                'title': 'Paid In Asset',
                'render': function (data: any, type: any, row: any) {
                    return show_float_or_empty(data);
                }
            },
            {
                'data': 'taxable_amount',
                'title': 'Taxable Amount',
                'render': function (data: any, type: any, row: any) {
                    return show_float_or_empty(data);
                }
            },
            {
                'data': 'taxable_bought_cost',
                'title': 'Taxable Bought Cost',
                'render': function (data: any, type: any, row: any) {
                    return show_float_or_empty(data);
                }
            },
            {'data': 'received_asset', 'title': 'Received Asset'},
            {
                'data': 'received_in_profit_currency',
                'title': 'Received in ' + settings.main_currency.ticker_symbol,
                'render': function (data: any, type: any, row: any) {
                    // it's already in main currency
                    return show_float_or_empty(data);
                }
            },
            {
                'data': 'time',
                'title': 'Time',
                'render': function (data: any, type: any, row: any) {
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
    monitor_add_callback('process_trade_history', function (result: any) {
        if ('error' in result) {
            showError(
                'Trade History Query Error',
                'Querying trade history died because of: ' + result['error'] + '. ' +
                    'Check the logs for more details'
            );
            return;
        }
        if (result['message'] !== '') {
            showWarning(
                'Trade History Query Warning',
                'During trade history query we got:' + result['message'] + '. History report is probably not complete.'
            );
        }
        if ($('#elementId').length === 0) {
            let str = form_button('Export CSV', 'export_csv');
            $(str).insertAfter('#generate_report');
            $('#export_csv').click(export_csv_callback);
        }
        create_taxreport_overview(result['result']['overview']);
        create_taxreport_details(result['result']['all_events']);
        // also save the page
        settings.page_taxreport = $('#page-wrapper').html();
    });
}

