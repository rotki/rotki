var settings = require("./settings.js")();

let TOTAL_BALANCES_TABLE = null;

function balance_table_init_callback(settings, json) {
    var api;
    if (!settings) { // called manually by us via .call() through a DT instance
        api = this;
    } else { // called from inside initComplete
        api = this.api();
    }

    api.column(2).every(function(){
        var column = this;
        var sum = column
            .data()
            .reduce(function (a, b) {
                a = parseFloat(a);
                if(isNaN(a)){ a = 0; }

                b = parseFloat(b);
                if(isNaN(b)){ b = 0; }

                return a + b;
            });
        sum = format_currency_value(sum);
        $(column.footer()).html('Total Sum: ' + sum);
    });
}

function add_balances_table(result) {
    var str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">All Balances</h1></div></div>';
    str += '<div class="row"><table id="table_balances_total"><thead><tr><th>Asset</th><th>Amount</th><th>USD Value</th><th>% of net value</th></tr/></thead><tfoot><tr><th></th><th></th><th></th><th></th></tr></tfoot><tbody id="table_balances_total_body"></tbody></table></div>';
    $(str).appendTo($('#dashboard-contents'));
    // TODO: Perhaps change how query_all_balances returns from the python side
    // so we can have it in the form of
    // [{'asset': 'BTC', 'amount: 1, 'usd_value': 1, 'netvalue_perc': 0.1}, ... ]
    // and thus avoid any need for the following preprocessing and instead feed it
    // directly to datatables
    let data = [];
    for (var asset in result) {
        if(result.hasOwnProperty(asset)) {
            if (asset == 'net_usd_perc_location' || asset == 'net_usd') {
                continue;
            }
            let amount = parseFloat(result[asset]['amount']);
            amount = amount.toFixed(settings.floating_precision);
            let value = parseFloat(result[asset]['usd_value']);
            value = value.toFixed(settings.floating_precision);
            let percentage = result[asset]['percentage_of_net_value'];
            data.push({'asset': asset, 'amount': amount, 'usd_value': value, 'percentage': percentage});
        }
    }
    TOTAL_BALANCES_TABLE = $('#table_balances_total').DataTable({
        "data": data,
        "columns": [
            {"data": "asset"},
            {"data": "amount"},
            {
                "title": settings.main_currency.ticker_symbol + ' value',
                "data": 'usd_value',
                "render": function (data, type, row) {
                    return format_currency_value(data);
                }
            },
            {"data": "percentage"}
        ],
        'initComplete': balance_table_init_callback,
        "order": [[3, 'desc']]
    });
    // also save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function reload_balance_table_if_existing() {
    if (TOTAL_BALANCES_TABLE) {
        TOTAL_BALANCES_TABLE.rows().invalidate();
        balance_table_init_callback.call(TOTAL_BALANCES_TABLE);
        $(TOTAL_BALANCES_TABLE.column(2).header()).text(settings.main_currency.ticker_symbol + ' value');
        TOTAL_BALANCES_TABLE.draw();
    }
}


module.exports = function() {
    this.add_balances_table = add_balances_table;
    this.reload_balance_table_if_existing = reload_balance_table_if_existing;
};
