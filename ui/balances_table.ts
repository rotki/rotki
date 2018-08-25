import { format_currency_value, settings } from './settings';
import { timestamp_to_date } from './utils';

let TOTAL_BALANCES_TABLE: DataTables.Api = null;
let SAVED_BALANCES = {};


interface ItableDataItem {
    'asset': string;
    'amount': string;
    'usd_value': string;
    'percentage': string;
}

function create_full_data(): Array<ItableDataItem> {
    let inter_data: any = {};
    for (let location in SAVED_BALANCES) {
        if (SAVED_BALANCES.hasOwnProperty(location)) {
            // for every location's balances
            let balances = SAVED_BALANCES[location];
            for (let asset in balances) {
                if (balances.hasOwnProperty(asset)) {

                    let old_amount = 0;
                    let old_value = 0;
                    if (inter_data.hasOwnProperty(asset)) {
                        old_amount = inter_data[asset]['amount'];
                        old_value = inter_data[asset]['usd_value'];
                    }

                    let amount = old_amount + balances[asset]['amount'];
                    let value = old_value + balances[asset]['usd_value'];
                    inter_data[asset] = {'amount': amount, 'usd_value': value};
                }
            }
        }
    }

    // now let's get the total usd
    let total_usd: number = 0;
    for (let asset in inter_data) {
        if (inter_data.hasOwnProperty(asset)) {
            total_usd += inter_data[asset]['usd_value'];
        }
    }

    let full_data: Array<ItableDataItem> = [];
    // we should have all balances by now
    for (let asset in inter_data) {
        if (inter_data.hasOwnProperty(asset)) {
            const amount_n: number = inter_data[asset]['amount'];
            const amount: string = amount_n.toFixed(settings.floating_precision);
            const value_n: number = inter_data[asset]['usd_value'];
            const percentage_n = value_n / total_usd;
            const percentage = (percentage_n * 100).toFixed(settings.floating_precision);
            const value = value_n.toFixed(settings.floating_precision);
            full_data.push({
                'asset': asset,
                'amount': amount,
                'usd_value': value,
                'percentage': percentage
            });
        }
    }
    return full_data;
}

export function total_balances_get() {
    return SAVED_BALANCES;
}

export function total_table_recreate() {
    // only create the total table if we are in the dashboard
    if (settings.current_location !== 'index') {
        return;
    }

    let full_data = create_full_data();

    if (!TOTAL_BALANCES_TABLE) {
        init_balances_table(full_data);
    } else {
        if (!$('#table_balances_total_body').length) {
            // if table has already been initialized but no longer existing on the page
            TOTAL_BALANCES_TABLE.destroy(false);
            init_balances_table(full_data);
        } else {
            // update the already existing table
            TOTAL_BALANCES_TABLE.clear();
            TOTAL_BALANCES_TABLE.rows.add(full_data);
            balance_table_init_callback.call(TOTAL_BALANCES_TABLE);
            $(TOTAL_BALANCES_TABLE.column(2).header()).text(settings.main_currency.ticker_symbol + ' value');
            TOTAL_BALANCES_TABLE.draw();
        }
    }
    update_last_balance_save();
}

export function total_table_add_balances(location: string, query_result: any) {
    let data = {};
    for (let asset in query_result) {
        if (query_result.hasOwnProperty(asset)) {
            if (asset === 'location' || asset === 'net_usd') {
                continue;
            }
            let amount = parseFloat(query_result[asset]['amount']);
            let value = parseFloat(query_result[asset]['usd_value']);
            data[asset] = {'amount': amount, 'usd_value': value};
        }
    }
    SAVED_BALANCES[location] = data;
    total_table_recreate();
}

function balance_table_init_callback(settings: any, json: any) {
    let api;
    if (!settings) { // called manually by us via .call() through a DT instance
        api = this;
    } else { // called from inside initComplete
        api = this.api();
    }

    if (api.data().count()) {
        api.column(2).every(function() {
            let column = this;
            let sum = column
                .data()
                .reduce(function (a: any, b: any) {
                    a = parseFloat(a);
                    if (isNaN(a)) { a = 0; }

                    b = parseFloat(b);
                    if (isNaN(b)) { b = 0; }

                    return a + b;
                });
            sum = format_currency_value(sum);
            $(column.footer()).html('Total Sum: ' + sum);
        });
    }
}

function update_last_balance_save() {
    let str_value = 'Never';
    if (settings.last_balance_save != 0) {
        str_value = timestamp_to_date(settings.last_balance_save);
    }
    $('#last_balance_save_field').html(str_value);
}

function add_balances_table_html() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">All Balances</h1></div></div>';
    str += '<div class="list-group"><div class="list-group-item"><i class="fa fa-save fa-fw"></i> Last Time Balances were saved:<span id="last_balance_save_field" class="pull-right small">Never</span></div></div>';
    str += '<div class="row"><table id="table_balances_total"><thead><tr><th>Asset</th><th>Amount</th><th>USD Value</th><th>% of net value</th></tr/></thead><tfoot><tr><th></th><th></th><th></th><th></th></tr></tfoot><tbody id="table_balances_total_body"></tbody></table></div>';
    $(str).appendTo($('#dashboard-contents'));
}

function init_balances_table(data: Array<ItableDataItem>) {
    add_balances_table_html();

    TOTAL_BALANCES_TABLE = $('#table_balances_total').DataTable({
        'data': data,
        'columns': [
            {'data': 'asset'},
            {'data': 'amount'},
            {
                'title': settings.main_currency.ticker_symbol + ' value',
                'data': 'usd_value',
                'render': function (data: string | number, type: any, row: any) {
                    return format_currency_value(data, row['asset'], row['amount']);
                }
            },
            {'data': 'percentage'}
        ],
        'initComplete': balance_table_init_callback,
        'order': [[3, 'desc']]
    });
    // also save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function get_total_asssets_value(asset_dict) {
    let value = 0;
    for (let asset in asset_dict) {
        if (asset_dict.hasOwnProperty(asset)) {
            value += parseFloat(asset_dict[asset]['usd_value']);
        }
    }
    return value;
}
export function* iterate_saved_balances() {
    let saved_balances = total_balances_get();
    for (var location in saved_balances) {
        if (saved_balances.hasOwnProperty(location)) {
            let total = get_total_asssets_value(saved_balances[location]);
            if (settings.EXCHANGES.indexOf(location) >= 0) {
                yield [location, total, null];
            } else {
                let icon;
                if (location == 'blockchain') {
                    icon = 'fa-hdd-o';
                } else if (location == 'banks') {
                    icon = 'fa-university';
                } else {
                    throw 'Invalid location at dashboard box from saved balance creation';
                }
                yield [location, total, icon];
            }
        }
    }
}

export function reload_balance_table_if_existing() {
    if (TOTAL_BALANCES_TABLE) {
        TOTAL_BALANCES_TABLE.rows().invalidate();
        balance_table_init_callback.call(TOTAL_BALANCES_TABLE);
        $(TOTAL_BALANCES_TABLE.column(2).header()).text(settings.main_currency.ticker_symbol + ' value');
        TOTAL_BALANCES_TABLE.draw();
    }
}
