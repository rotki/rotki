import {dt_edit_drawcallback, showError, showInfo, timestamp_to_date} from './utils';
import {form_button, form_entry, form_select, form_text} from './elements';
import {settings} from './settings';
import {OtcTrade} from './model/otc-trade';
import 'datatables.net';
import {service} from './rotkehlchen_service';

let OTC_TRADES_TABLE: DataTables.Api;
let CURRENT_TRADE: OtcTrade | {} = {};

function update_valhtml(selector_text: string, val: string = '') {
    $(selector_text).val(val);
    $(selector_text).html(val);
}

function format(d: OtcTrade) {
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

function edit_otc_trade(row: DataTables.RowMethods) {
    const data = row.data() as OtcTrade;
    const ts = timestamp_to_date(data.timestamp, false);
    $('#otc_timestamp').val(ts);
    $('#otc_pair').val(data.pair);
    $('#otc_type').val(data.trade_type);
    $('#otc_amount').val(data.amount);
    $('#otc_rate').val(data.rate);
    $('#otc_fee').val(data.fee);
    $('#otc_fee_currency').val(data.fee_currency);
    $('#otc_link').val(data.link);
    $('#otc_notes').val(data.notes);

    CURRENT_TRADE = data;

    update_valhtml('#otctradesubmit', 'Edit Trade');
}

function delete_otc_trade(row: DataTables.RowMethods) {
    const data = row.data() as OtcTrade;
    service.delete_otctrade(data.id).then(() => {
        showInfo('Success', 'Trade Deleted');
        reload_table_data();
    }).catch(reason => {
        showError('Error at Trade Deletion', reason.message);
    });
}

function reload_table_data() {
    service.query_otctrades().then(value => {
        update_valhtml('#otc_timestamp');
        update_valhtml('#otc_pair');
        update_valhtml('#otc_amount');
        update_valhtml('#otc_rate');
        update_valhtml('#otc_fee');
        update_valhtml('#otc_fee_currency');
        update_valhtml('#otc_link');
        update_valhtml('#otc_notes');

        OTC_TRADES_TABLE.clear();
        OTC_TRADES_TABLE.rows.add(value);
        OTC_TRADES_TABLE.draw();
    }).catch(reason => {
        console.log(`Error at querying OTC trades: ${reason.message}`);
    });
}

function create_otctrades_table() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">OTC Trades List</h1></div></div>';
    str += `<div class="row">
    <table id="table_otctrades">
        <thead>
        <tr>
            <th></th>
            <th>Pair</th>
            <th>Type</th>
            <th>Amount</th>
            <th>Rate</th>
            <th>Time</th>
        </tr>
        </thead>
        <tbody id="table_otctrades_body"></tbody>
    </table>
</div>`;

    $(str).insertAfter($('#otc_table_anchor'));
    service.query_otctrades().then(value => {
        for (let i = 0; i < value.length; i++) {
            const rowTemplate = '<tr><td></td><td></td><td></td><td></td></tr>';
            $(rowTemplate).appendTo($('#table_otctrades_body'));
        }
        OTC_TRADES_TABLE = $('#table_otctrades').DataTable({
            'data': value,
            'columns': [
                {
                    'className': 'details-control',
                    'orderable': false,
                    'data': undefined,
                    'defaultContent': '',
                    'render': () => '<i class="fa fa-plus-square" aria-hidden="true"></i>',
                    'width': '15px'
                },
                {'data': 'pair'},
                {'data': 'trade_type'},
                {'data': 'amount'},
                {'data': 'rate'},
                {
                    'render': (data: number, type: string) => {
                        if (type === 'display') {
                            return timestamp_to_date(data);
                        }
                        return data;
                    },
                    'data': 'timestamp'
                },
            ],
            'order': [[5, 'asc']],
            drawCallback: dt_edit_drawcallback('table_otctrades', edit_otc_trade, delete_otc_trade)
        });
    }).catch(reason => {
        console.log(`Error at querying OTC trades: ${reason.message}`);
    });
}

export function create_otctrades_ui() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class="page-header">OTC Trades Management</h1></div></div>';
    str += `<div class="row">
    <div class="col-lg-12">
        <div class="panel panel-default">
            <div class="panel-heading">Register New Trade</div>
            <div class="panel-body"></div>
        </div>
    </div>
</div>`;
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
    $('#otctradesubmit').click(function (event) {
        event.preventDefault();
        const otc_timestamp = $('#otc_timestamp').val();
        const otc_pair = $('#otc_pair').val();
        const otc_type = $('#otc_type').val();
        const otc_amount = $('#otc_amount').val();
        const otc_rate = $('#otc_rate').val();
        const otc_fee = $('#otc_fee').val();
        const otc_fee_currency = $('#otc_fee_currency').val();
        const otc_link = $('#otc_link').val();
        const otc_notes = $('#otc_notes').val();
        let trade_id = null;
        if ('id' in CURRENT_TRADE) {
            trade_id = CURRENT_TRADE['id'];
        }
        const payload = {
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

        let add = true;
        if ($('#otctradesubmit').val() === 'Edit Trade') {
            add = false;
        }

        service.modify_otc_trades(add, payload).then(() => {
            showInfo('Success', 'Trade submitted');
            reload_table_data();
            // also make sure we are back to adding a trade
            // in case we were editing
            $('#otctradesubmit').val('Add Trade');
            $('#otctradesubmit').html('Add Trade');
        }).catch((reason: Error) => {
            showError('Trade Addition Error', reason.message);
        });

    });
    $('#otc_timestamp').datetimepicker({
        format: settings.datetime_format
    });
    // Add event listener for opening and closing details
    $('#table_otctrades tbody').on('click', 'td.details-control', (event: JQuery.TriggeredEvent) => {
        const tr = $(event.target).closest('tr');
        const tdi = tr.find('i.fa');
        const row = OTC_TRADES_TABLE.row(tr);

        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
            tdi.first().removeClass('fa-minus-square');
            tdi.first().addClass('fa-plus-square');
        } else {
            // Open this row
            row.child(format(row.data() as OtcTrade)).show();
            tr.addClass('shown');
            tdi.first().removeClass('fa-plus-square');
            tdi.first().addClass('fa-minus-square');
        }
    });
}
