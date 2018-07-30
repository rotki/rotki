import { settings } from './settings';
import { dt_edit_drawcallback, showError, showInfo, timestamp_to_date } from './utils';
import { form_button, form_entry, form_select, form_text  } from './elements';
import client from './zerorpc_client';


let OTC_TRADES_TABLE = null as DataTables.Api;

interface TradeData {
    id: any;
    timestamp: string;
    pair: string;
    trade_type: string;
    amount: string | number;
    rate: string | number;
    fee: string | number;
    fee_currency: string;
    link: string;
    notes: string;
}

let CURRENT_TRADE = {} as TradeData;

function update_valhtml(selector_text: any, val: any) {
    $(selector_text).val(val);
    $(selector_text).html(val);
}

function format (d: any) {
    // `d` is the original data object for the row
    return '<table cellpadding="5" cellspacing="0" border="0" style="padding-left:50px;">' +
        '<tr>' +
        '<td>Extra Info</td>' +
        '<td>' + d.notes + '</td>' +
        '</tr>' +
        '<tr>' +
        '<td>Links:</td>' +
        '<td>' + d.link + '</td>' +
        '</tr>' +
        '<tr>' +
        '<td>Fee:</td>' +
        '<td>' + d.fee + ' ' + d.fee_currency + '</td>' +
        '</tr>' +
        '</table>';
}

function edit_otc_trade(row: any) {
    let data = row.data();
    let ts = timestamp_to_date(data.timestamp);
    $('#otc_timestamp').val(ts);
    $('#otc_pair').val(data.pair);
    $('#otc_type').val(data.type);
    $('#otc_amount').val(data.amount);
    $('#otc_rate').val(data.rate);
    $('#otc_fee').val(data.fee);
    $('#otc_fee_currency').val(data.fee_currency);
    $('#otc_link').val(data.link);
    $('#otc_notes').val(data.notes);

    CURRENT_TRADE = {
        'id': data.id,
        'timestamp': ts,
        'pair': data.pair,
        'trade_type': data.type,
        'amount': data.amount,
        'rate': data.rate,
        'fee': data.fee,
        'fee_currency': data.fee_currency,
        'link': data.link,
        'notes': data.notes
    };

    update_valhtml('#otctradesubmit', 'Edit Trade');
}

function delete_otc_trade(row: any) {
    let data = row.data();
    client.invoke(
        'delete_otctrade',
        data.id,
        (error, res) => {
            if (error || res == null) {
                showError('Error at Trade Deletion', error);
            } else {
                if (!res['result']) {
                    showError('Error at Trade Deletion', res['message']);
                } else {
                    showInfo('Succcess', 'Trade Deleted');
                    reload_table_data();
                }
            }
        });
}

function reload_table_data() {
    client.invoke('query_otctrades', (error, result) => {
        if (error || result == null) {
            console.log('Error at querying OTC trades: ' + error);
        } else {
            update_valhtml('#otc_timestamp', '');
            update_valhtml('#otc_pair', '');
            update_valhtml('#otc_amount', '');
            update_valhtml('#otc_rate', '');
            update_valhtml('#otc_fee', '');
            update_valhtml('#otc_fee_currency', '');
            update_valhtml('#otc_link', '');
            update_valhtml('#otc_notes', '');

            OTC_TRADES_TABLE.clear();
            OTC_TRADES_TABLE.rows.add(result);
            OTC_TRADES_TABLE.draw();
        }
    });
}

function create_otctrades_table() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">OTC Trades List</h1></div></div>';
    str += '<div class="row"><table id="table_otctrades"><thead><tr><th></th><th>Pair</th><th>Type</th><th>Amount</th><th>Rate</th><th>Time</th></tr/></thead><tbody id="table_otctrades_body"></tbody></table></div>';
    $(str).insertAfter($('#otc_table_anchor'));
    client.invoke('query_otctrades', (error, result) => {
        if (error || result == null) {
            console.log('Error at querying OTC trades: ' + error);
        } else {
            for (let i = 0; i < result.length; i++) {
                let str = '<tr><td></td><td></td/><td></td><td></td></tr>';
                $(str).appendTo($('#table_otctrades_body'));
            }
            OTC_TRADES_TABLE = $('#table_otctrades').DataTable({
                'data': result,
                'columns': [
                    {
                        'className': 'details-control',
                        'orderable': false,
                        'data': null,
                        'defaultContent': '',
                        'render': function () {
                            return '<i class="fa fa-plus-square" aria-hidden="true"></i>';
                        },
                        width: '15px'
                    },
                    { 'data': 'pair' },
                    { 'data': 'type' },
                    { 'data': 'amount' },
                    { 'data': 'rate' },
                    {
                        'render': function (data: any, type: any, row: any) {
                            if (type === 'sort') {
                                return data;
                            }
                            return timestamp_to_date(data);
                        },
                        'data': 'timestamp'
                    },
                ],
                'order': [[5, 'asc']],
                drawCallback : dt_edit_drawcallback('table_otctrades', edit_otc_trade, delete_otc_trade)
            });
        }
    });
}

export function create_otctrades_ui() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class="page-header">OTC Trades Management</h1></div></div>';
    str += '<div class="row"><div class="col-lg-12"><div class="panel panel-default"><div class="panel-heading">Register New Trade</div><div class="panel-body"></div></div></div></div>';
    $('#page-wrapper').html(str);

    str = form_entry('time', 'otc_timestamp', '', 'Time that the trade took place');
    str += form_entry('pair', 'otc_pair', '', 'Pair for the trade. BASECURRENCY_QUOTE_CURRENCY');
    str += form_select('trade type', 'otc_type', ['buy', 'sell'], '');
    str += form_entry('amount', 'otc_amount', '', 'Amount bought/sold');
    str += form_entry('rate', 'otc_rate', '', 'Rate of the trade');
    str += form_entry('fee', 'otc_fee', '', 'Fee if any that the trade occured');
    str += form_entry('fee currency', 'otc_fee_currency', '', 'Currency the fee was paid in');
    str += form_entry('link', 'otc_link', '', 'A link to the trade. e.g.: in an explorer');
    str += form_text('Enter additional notes', 'otc_notes', 3, '', 'Additional notes to store for the trade');
    str += form_button('Add Trade', 'otctradesubmit');
    str += '<div id="otc_table_anchor"></div>';
    $(str).appendTo($('.panel-body'));

    create_otctrades_table();
}

export function add_otctrades_listeners() {
    // if we are reloading the page, recreate the table
    if (OTC_TRADES_TABLE) {
        // first remove the 2 table divs
        $('#otc_table_anchor').next('div').remove();
        $('#otc_table_anchor').next('div').remove();
        // and then recreate it
        create_otctrades_table();
    }
    $('#otctradesubmit').click(function(event: any) {
        event.preventDefault();
        let otc_timestamp = $('#otc_timestamp').val();
        let otc_pair = $('#otc_pair').val();
        let otc_type = $('#otc_type').val();
        let otc_amount = $('#otc_amount').val();
        let otc_rate = $('#otc_rate').val();
        let otc_fee = $('#otc_fee').val();
        let otc_fee_currency = $('#otc_fee_currency').val();
        let otc_link = $('#otc_link').val();
        let otc_notes = $('#otc_notes').val();
        let trade_id = null;
        if ('id' in CURRENT_TRADE) {
            trade_id = CURRENT_TRADE['id'];
        }
        let payload = {
            'otc_id': trade_id,
            'otc_timestamp': otc_timestamp,
            'otc_pair': otc_pair,
            'otc_type': otc_type,
            'otc_amount': otc_amount,
            'otc_rate': otc_rate,
            'otc_fee': otc_fee,
            'otc_fee_currency': otc_fee_currency,
            'otc_link': otc_link,
            'otc_notes': otc_notes
        };

        // depending on the type of button value we call different function
        let command = 'add_otctrade';
        if ($('#otctradesubmit').val() === 'Edit Trade') {
            command = 'edit_otctrade';
        }

        // and now send the data to the python process
        client.invoke(
            command,
            payload,
            (error, res) => {
                if (error || res == null) {
                    showError('Trade Addition Error', error);
                } else {
                    if (!res['result']) {
                        showError('Trade Addition Error', res['message']);
                    } else {
                        showInfo('Success', 'Trade submitted');
                        reload_table_data();
                        // also make sure we are back to adding a trade
                        // in case we were editing
                        $('#otctradesubmit').val('Add Trade');
                        $('#otctradesubmit').html('Add Trade');
                    }
                }
            });

    });
    $('#otc_timestamp').datetimepicker({
        format: settings.datetime_format
    });
    // Add event listener for opening and closing details
    $('#table_otctrades tbody').on('click', 'td.details-control', function () {
        let tr = $(this).closest('tr');
        let tdi = tr.find('i.fa');
        let row = OTC_TRADES_TABLE.row(tr);

        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
            tdi.first().removeClass('fa-minus-square');
            tdi.first().addClass('fa-plus-square');
        } else {
            // Open this row
            row.child(format(row.data())).show();
            tr.addClass('shown');
            tdi.first().removeClass('fa-plus-square');
            tdi.first().addClass('fa-minus-square');
        }
    });
}

