import {format_asset_title_for_ui, timestamp_to_date} from './utils';
import {format_currency_value, pages, settings} from './settings';
import {AssetBalance} from './model/asset-balance';
import 'datatables.net';

let TOTAL_BALANCES_TABLE: DataTables.Api | null = null;
let SAVED_BALANCES: { [location: string]: { [asset: string]: AssetBalance } } = {};

function create_full_data(): AssetBalance[] {
    const inter_data: { [asset: string]: AssetBalance } = {};
    for (const location in SAVED_BALANCES) {
        if (!SAVED_BALANCES.hasOwnProperty(location)) {
            continue;
        }

        const balances = SAVED_BALANCES[location];
        for (const asset in balances) {
            if (!balances.hasOwnProperty(asset)) {
                continue;
            }

            let old_amount = 0;
            let old_value = 0;
            if (inter_data.hasOwnProperty(asset)) {
                const assetData = inter_data[asset];
                old_amount = assetData.amount as number;
                old_value = assetData.usd_value as number;
            }

            const amount = old_amount + (balances[asset].amount as number);
            const value = old_value + (balances[asset].usd_value as number);

            inter_data[asset] = {
                amount: amount,
                usd_value: value
            };
        }
    }

    // now let's get the total usd
    let total_usd = 0;
    for (const asset in inter_data) {
        if (!inter_data.hasOwnProperty(asset)) {
            continue;
        }
        let asset_usd_value;
        if (typeof inter_data[asset].usd_value === 'string') {
            asset_usd_value = parseFloat(inter_data[asset].usd_value as string);
        } else {
            asset_usd_value = inter_data[asset].usd_value as number;
        }
        total_usd += asset_usd_value;
    }


    const full_data: AssetBalance[] = [];
    // we should have all balances by now
    for (const asset in inter_data) {
        if (!inter_data.hasOwnProperty(asset)) {
            continue;
        }
        let amount;
        if (typeof inter_data[asset].amount  === 'string') {
            amount = parseFloat(inter_data[asset].amount as string);
        } else {
            amount = inter_data[asset].amount as number;
        }

        const amountStr = amount.toFixed(settings.floating_precision);
        let value;
        if (typeof inter_data[asset].usd_value === 'string') {
            value = parseFloat(inter_data[asset].usd_value as string);
        } else {
            value = inter_data[asset].usd_value as number;
        }
        const percentage = value / total_usd;
        const percentageStr = (percentage * 100).toFixed(settings.floating_precision);
        const valueStr = value.toFixed(settings.floating_precision);
        full_data.push({
            asset: asset,
            amount: amountStr,
            usd_value: valueStr,
            percentage: percentageStr
        });
    }
    return full_data;
}

export function total_balances_get() {
    return SAVED_BALANCES;
}

export function reset_total_balances() {
    TOTAL_BALANCES_TABLE = null;
    SAVED_BALANCES = {};
}

export function total_table_recreate() {
    // only create the total table if we are in the dashboard
    if (settings.current_location !== 'index') {
        return;
    }

    const full_data = create_full_data();

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
            $(TOTAL_BALANCES_TABLE.column(2).header()).text(`${settings.main_currency.ticker_symbol} value`);
            TOTAL_BALANCES_TABLE.draw();
        }
    }
    update_last_balance_save();
}

export function total_table_add_balances(location: string, query_result: { [asset: string]: AssetBalance }) {
    const data: { [asset: string]: AssetBalance } = {};
    for (const asset in query_result) {
        if (!query_result.hasOwnProperty(asset)) {
            continue;
        }

        if (asset === 'location' || asset === 'net_usd') {
            continue;
        }

        const amount = parseFloat(query_result[asset].amount.toString());
        const value = parseFloat(query_result[asset].usd_value.toString());
        data[asset] = {amount: amount, usd_value: value};
    }
    SAVED_BALANCES[location] = data;
    total_table_recreate();
}

export function total_table_modify_balance_for_asset(location: string, asset: string, data: AssetBalance) {
    if (!SAVED_BALANCES.hasOwnProperty(location)) {
        SAVED_BALANCES[location] = {};
    }
    SAVED_BALANCES[location][asset] = data;
    total_table_recreate();
}

export function total_table_modify_all_balances_for_location(location: string, data: { [asset: string]: AssetBalance }) {
    if (!SAVED_BALANCES.hasOwnProperty(location)) {
        SAVED_BALANCES[location] = {};
    }
    SAVED_BALANCES[location] = data;
    total_table_recreate();
}

function balance_table_init_callback(datatablesApi?: DataTables.Api, _json?: any) {
    let api: DataTables.Api;
    if (!datatablesApi) { // called manually by us via .call() through a DT instance
        // @ts-ignore
        api = this;
    } else { // called from inside initComplete
        // @ts-ignore
        api = this.api();
    }

    if (!api.data().count()) {
        return;
    }

    const column = api.column(2);
    let sum = column.data()
        .flatten()
        .reduce((a: any, b: any) => {
            a = parseFloat(a);
            if (isNaN(a)) {
                a = 0;
            }

            b = parseFloat(b);
            if (isNaN(b)) {
                b = 0;
            }

            return a + b;
        });
    sum = format_currency_value(sum);
    $(column.footer()).html(`Total Sum: ${sum}`);
}

function add_balances_table_html() {
    const str = `<div class="row">
    <div class="col-lg-12"><h1 class=page-header">All Balances</h1></div>
</div>
<div class="row">
    <table id="table_balances_total">
        <thead>
        <tr>
            <th>Asset</th>
            <th>Amount</th>
            <th>USD Value</th>
            <th>% of net value</th>
        </tr>
        </thead>
        <tfoot>
        <tr>
            <th></th>
            <th></th>
            <th></th>
            <th></th>
        </tr>
        </tfoot>
        <tbody id="table_balances_total_body"></tbody>
    </table>
</div>`;
    $(str).appendTo($('#dashboard-contents'));
}

function update_last_balance_save() {
    let str_value = 'Never';
    if (settings.last_balance_save !== 0) {
        str_value = timestamp_to_date(settings.last_balance_save);
    }
    $('#last_balance_save_field').html(str_value);
}

function init_balances_table(data: AssetBalance[]) {
    add_balances_table_html();

    TOTAL_BALANCES_TABLE = $('#table_balances_total').DataTable({
        'data': data,
        'columns': [
            {
                'title': 'asset',
                'data': 'asset',
                'render': (_data: any, _type: string, row: { [key: string]: string }) => format_asset_title_for_ui(row['asset'])
            },
            {'data': 'amount'},
            {
                'title': `${settings.main_currency.ticker_symbol} value`,
                'data': 'usd_value',
                'render': (_data: string, _type: string, row: AssetBalance) => {
                    return format_currency_value(_data, row.asset as string, row.amount as string);
                }
            },
            {'data': 'percentage'}
        ],
        'initComplete': balance_table_init_callback as any,
        'order': [[3, 'desc']]
    });
    // also save the dashboard page
    pages.page_index = $('#page-wrapper').html();
}

export function reload_balance_table_if_existing() {
    if (TOTAL_BALANCES_TABLE) {
        TOTAL_BALANCES_TABLE.rows().invalidate();
        balance_table_init_callback.call(TOTAL_BALANCES_TABLE);
        $(TOTAL_BALANCES_TABLE.column(2).header()).text(`${settings.main_currency.ticker_symbol} value`);
        TOTAL_BALANCES_TABLE.draw();
    }
}

export function get_total_assets_value(asset_dict: { [asset: string]: AssetBalance }) {
    let value = 0;
    for (const asset in asset_dict) {
        if (asset_dict.hasOwnProperty(asset)) {
            value += parseFloat(asset_dict[asset].usd_value.toString());
        }
    }
    return value;
}

export function* iterate_saved_balances() {
    const saved_balances = total_balances_get();

    for (const location in saved_balances) {
        if (!saved_balances.hasOwnProperty(location)) {
            continue;
        }

        const total = get_total_assets_value(saved_balances[location]);
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            yield [location, total, null];
        } else {
            let icon;
            if (location === 'blockchain') {
                icon = 'fa-hdd-o';
            } else if (location === 'banks') {
                icon = 'fa-university';
            } else {
                throw new Error('Invalid location at dashboard box from saved balance creation');
            }
            yield [location, total, icon];
        }
    }
}
