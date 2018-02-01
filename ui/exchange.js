var settings = require("./settings.js")();
var dt = require( 'datatables.net' )();
require("./monitor.js");
require("./utils.js")();
require("./asset_table.js")();
require("./navigation.js")();

let SAVED_TABLES = {};

function create_exchange_table(name) {
    var str = page_header(name);
    $('#page-wrapper').html(str);
    client.invoke("query_exchange_balances_async", name, (error, res) => {
        if (error || res == null) {
            console.log("Error at exchange " + name + " balances: " + error);
            return;
        }
        console.log("Query "+ name + "  returned task id " + res['task_id']);
        create_task(
            res['task_id'],
            'query_exchange_balances',
            'Query '+ name + ' Balances'
        );
    });
}

function reload_exchange_tables_if_existing() {
    for (var name in SAVED_TABLES) {
        if(SAVED_TABLES.hasOwnProperty(name)) {
            let table = SAVED_TABLES[name];
            table.reload();
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
        let name = result['name'];
        let data = result['balances'];
        SAVED_TABLES[name] = new AssetTable('asset', name, 'appendTo', 'page-wrapper', data);
        // also save the exchange page
        settings.page_exchange[name] = $('#page-wrapper').html();
    });
}

module.exports = function() {
    this.create_or_reload_exchange = create_or_reload_exchange;
    this.init_exchanges_tables = init_exchanges_tables;
    this.reload_exchange_tables_if_existing = reload_exchange_tables_if_existing;
};
