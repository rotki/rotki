var settings = require("./settings.js")();
require("./monitor.js");
require("./utils.js")();
var dt = require( 'datatables.net' )();

let SAVED_TABLES = {};

function create_exchange_table(name) {
    var str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">' + name + '</h1></div></div>';
    str += '<div class="row"><table id="table_'+name+'"><thead><tr><th>Asset</th><th>Amount</th><th>USD Value</th></tr/></thead><tbody id="table_'+name+'_body"></tbody></table></div>';
    $('#page-wrapper').html(str);
    client.invoke("query_exchange_balances_async", name, (error, res) => {
        if (error || res == null) {
            console.log("Error at exchange " + name + " balances: " + error);
        } else {
            console.log("Query "+ name + "  returned task id " + res['task_id']);
            create_task(
                res['task_id'],
                'query_exchange_balances',
                'Query '+ name + ' Balances'
            );
        }
    });
}

function populate_exchange_table(name, result) {
    // TODO: Perhaps change how query_all_balances returns from the python side
    // so we can have it in the form of
    // [{'asset': 'BTC', 'amount: 1, 'usd_value': 1, 'netvalue_perc': 0.1}, ... ]
    // and thus avoid any need for the following preprocessing and instead feed it
    // directly to datatables
    let data = [];
    for (var asset in result) {
        if(result.hasOwnProperty(asset)) {
            let amount = parseFloat(result[asset]['amount']);
            amount = amount.toFixed(settings.floating_precision);
            let value = parseFloat(result[asset]['usd_value']);
            value = value.toFixed(settings.floating_precision);
            data.push({'asset': asset, 'amount': amount, 'usd_value': value});
        }
    }
    SAVED_TABLES[name] = $('#table_'+name).DataTable({
        "data": data,
        "columns": [
            {"data": "asset"},
            {"data": "amount"},
            {
                // seems to not work. Why? I solve it by specifically changing the name right below
                // "name": settings.main_currency.ticker_symbol + " value",
                "data": 'usd_value',
                "render": function (data, type, row) {
                    return format_currency_value(data);
                }
            }
        ],
        "order": [[2, 'desc']]
    });
    $(SAVED_TABLES[name].column(2).header()).text(settings.main_currency.ticker_symbol + ' value');
    // also save the exchange page
    settings.page_exchange[name] = $('#page-wrapper').html();
}

function reload_exchange_tables_if_existing() {
    for (var name in SAVED_TABLES) {
        if(SAVED_TABLES.hasOwnProperty(name)) {
            let table = SAVED_TABLES[name];
            table.rows().invalidate();
            $(table.column(2).header()).text(settings.main_currency.ticker_symbol + ' value');
            table.draw();
        }
    }
}

function create_or_reload_exchange(name) {
    change_location('exchange_' + name);
    if (!settings.page_exchange[name]) {
        console.log("At create/reload exchange, with a null page index");
        create_exchange_table(name);
    } else {
        console.log("At create/reload exchange, with a Populated page index");
        $('#page-wrapper').html(settings.page_exchange[name]);
    }
}

function init_exchanges_tables() {
    monitor_add_callback('query_exchange_balances', function (result) {
        populate_exchange_table(result['name'], result['balances']);
    });
}

module.exports = function() {
    this.create_or_reload_exchange = create_or_reload_exchange;
    this.init_exchanges_tables = init_exchanges_tables;
    this.reload_exchange_tables_if_existing = reload_exchange_tables_if_existing;
};
