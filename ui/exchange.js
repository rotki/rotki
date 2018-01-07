var settings = require("./settings.js")();
require("./monitor.js");
require("./utils.js")();
var dt = require( 'datatables.net' )();

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

    for (var asset in result) {
        if(result.hasOwnProperty(asset)) {
            let str = '<tr><td>'+asset+'</td><td>'+result[asset]['amount']+'</td/><td>'+result[asset]['usd_value']+'</td></tr>';
            $(str).appendTo($('#table_'+name+'_body'));
        }
    }
    $('#table_'+name).DataTable();
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
};
