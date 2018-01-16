require("./zerorpc_client.js")();
var settings = require("./settings.js")();
require("./monitor.js")();
require("./utils.js")();
require("./exchange.js")();


let saved_results = [];



function Result (result_type, number, name, icon) {
    this.type = result_type;
    this.number = number;
    this.name = name;
    this.icon = icon;
}

$('#settingsbutton a').click(function(event) {
    event.preventDefault();
    var target_location = determine_location(this.href);
    if (target_location != "settings") {
        throw "Invalid link location " + target_location;
    }
    console.log("Going to settings!");
    create_or_reload_settings();
});

function add_exchange_on_click() {
    $('.panel a').click(function(event) {
        event.preventDefault();
        var target_location = determine_location(this.href);
        if (target_location.startsWith('exchange_')) {
            exchange_name = target_location.substring(9);
            assert_exchange_exists(exchange_name);
            console.log("Going to exchange " + exchange_name);
            create_or_reload_exchange(exchange_name);
        } else {
            throw "Invalid link location " + target_location;
        }
    });
}

function create_exchange_box(exchange, number, currency_icon) {
    let current_location = settings.current_location;
    if (current_location != 'index') {
        let result = new Result('exchange', number, exchange);
        saved_results.push(result);
        return;
    }

    if($("#" + exchange+'box').length != 0) {
        //already exists
        return;
    }

    var css_class = 'exchange-icon-inverted';
    if (['poloniex', 'binance'].indexOf(exchange) > -1) {
        css_class = 'exchange-icon';
    }
    // only show 2 decimal digits
    number = number.toFixed(settings.floating_precision);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+exchange+'_box"><div class="row"><div class="col-xs-3"><i><img title="' + exchange + '" class="' + css_class + '" src="images/'+ exchange +'.png"  /></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#exchange_' + exchange +'"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    $(str).prependTo($('#dashboard-contents'));
    add_exchange_on_click();
    // finally save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function create_box (id, icon, number, currency_icon) {
    let current_location = settings.current_location;
    if (current_location != 'index') {
        let result = new Result('box', number, id, icon);
        saved_results.push(result);
        return;
    }
    if($("#" + id).length != 0) {
        //already exists
        return;
    }
    number = number.toFixed(settings.floating_precision);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+id+'"><div class="row"><div class="col-xs-3"><i title="' + id + '" class="fa '+ icon +'  fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    $(str).prependTo($('#dashboard-contents'));
    // also save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function set_ui_main_currency(currency) {
    $('#current-main-currency').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
}


var alert_id = 0;
function add_alert_dropdown(alert_text, alert_time) {
    var str='<li class="warning'+alert_id+'"><a href="#"><div><p>'+alert_text+'<span class="pull-right text-muted"><i class="fa fa-times warningremover'+alert_id+'"></i></span></p></div></a></li><li class="divider warning'+alert_id+'"></li>';
    $(str).appendTo($(".dropdown-alerts"));
    let current_alert_id = alert_id;
    $(".warningremover" + current_alert_id).click(function(){console.log("remove callback called for " +current_alert_id);$('.warning'+current_alert_id).remove();});
    alert_id += 1;
}

function add_currency_dropdown(currency) {
    var str = '<li><a id="change-to-'+ currency.ticker_symbol.toLowerCase() +'" href="#"><div><i class="fa '+ currency.icon +' fa-fw"></i> Set '+ currency.name +' as the main currency</div></a></li><li class="divider"></li>';
    $(str).appendTo($(".currency-dropdown"));

    $('#change-to-'+ currency.ticker_symbol.toLowerCase()).bind('click', function() {
        client.invoke("set_main_currency", currency.ticker_symbol, (error, res) => {
            if(error) {
                showAlert('alert-danger', error);
            } else {
                set_ui_main_currency(currency);
            }
        });
    });
}

function add_balances_table(result) {
    var str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">All Balances</h1></div></div>';
    str += '<div class="row"><table id="table_balances_total"><thead><tr><th>Asset</th><th>Amount</th><th>USD Value</th><th>% of net value</th></tr/></thead><tfoot><tr><th></th><th></th><th></th><th></th></tr></tfoot><tbody id="table_balances_total_body"></tbody></table></div>';
    $(str).appendTo($('#dashboard-contents'));
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
            let str = '<tr><td>'+asset+'</td><td>'+amount+'</td/><td>'+value+'</td><td>'+percentage+'</td></tr>';
            $(str).appendTo($('#table_balances_total_body'));
        }
    }
    $('#table_balances_total').DataTable({
        'initComplete': function (settings, json){
            this.api().column(2).every(function(){
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

                $(column.footer()).html('Total Sum: ' + sum.toFixed(2));
            });
        }
    });
    // also save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function get_settings() {
    client.invoke("get_settings", (error, res) => {
        if (error || res == null) {
            startup_error(
                "get_settings response was: " + res + " and error: " + error,
                "get_settings RPC failed"
            );
        } else {
            // set main currency
            console.log("server is ready");
            settings.main_currency = res['main_currency'];
            for (let i = 0; i < settings.CURRENCIES.length; i ++) {
                if (settings.main_currency == settings.CURRENCIES[i].ticker_symbol) {
                    set_ui_main_currency(settings.CURRENCIES[i]);
                    settings.main_currency = settings.CURRENCIES[i];
                    break;
                }
            }
            // set the other settings
            settings.floating_precision = res['ui_floating_precision'];
            settings.historical_data_start_date = res['historical_data_start_date'];

            // make separate queries for all registered exchanges
            let exchanges = res['exchanges'];
            for (let i = 0; i < exchanges.length; i++) {
                let exx = exchanges[i];
                client.invoke("query_exchange_total_async", exx, true, function (error, res) {
                    if (error || res == null) {
                        console.log("Error at first query of an exchange's balance: " + error);
                        return;
                    }
                    create_task(res['task_id'], 'query_exchange_total', 'Query ' + exx + ' Exchange');
                });
            }

            client.invoke("query_balances_async", function (error, res) {
                if (error || res == null) {
                    console.log("Error at query balances async: " + error);
                    return;
                }
                create_task(res['task_id'], 'query_balances', 'Query all balances');
            });
            $("body").removeClass("loading");
        }
    });
}

function get_blockchain_total() {
    client.invoke("query_blockchain_total_async", (error, res) => {
        if (error || res == null) {
            console.log("Error at querying blockchain total: " + error);
        } else {
            console.log("Blockchain total returned task id " + res['task_id']);
            create_task(res['task_id'], 'query_blockchain_total', 'Query Blockchain Balances');
        }
    });
}

function get_banks_total() {
    // does not really need to be async at the moment as it's just a file read
    // but trying to be future proof
    client.invoke("query_banks_total_async", (error, res) => {
        if (error || res == null) {
            console.log("Error at querying bank total: " + error);
        } else {
            console.log("Query banks returned task id " + res['task_id']);
            create_task(res['task_id'], 'query_banks_total', 'Query Bank Balances');
        }
    });
}

function create_or_reload_dashboard() {
    change_location('index');

    if (!settings.page_index) {
        $("body").addClass("loading");
        console.log("At create/reload, with a null page index");

        get_settings();
        get_blockchain_total();
        get_banks_total();
    } else {
        console.log("At create/reload, with a Populated page index");
        $('#page-wrapper').html(settings.page_index);
        add_exchange_on_click();
    }

    // also if there are any saved results apply them
    for (let i = 0; i < saved_results.length; i ++) {
        let result = saved_results[i];
        console.log("Applying saved result " + result.name + " for dashboard");
        if (result.type == 'exchange') {
            create_exchange_box(
                result.name,
                result.number,
                settings.main_currency.icon
            );
        } else if (result.type == 'box') {
            create_box(
                result.name,
                result.icon,
                result.number,
                settings.main_currency.icon
            );
        } else {
            throw "Invalid result type " + result.type;
        }
    }
    saved_results = [];
}


const ipc = require('electron').ipcRenderer;
ipc.on('failed', (event, message) => {
    // get notified if the python subprocess dies
    startup_error(
        "The python process died before the UI startup.",
        "The python process died before the UI startup."
    );
    // send ack to main.js
    ipc.send('ack', 1);
});


function init_dashboard() {
    // add callbacks for dashboard to the monitor
    monitor_add_callback('query_exchange_total', function (result) {
        create_exchange_box(
            result['name'],
            parseFloat(result['total']),
            settings.main_currency.icon
        );
    });
    monitor_add_callback('query_blockchain_total', function (result) {
        create_box(
            'blockchain balance',
            'fa-hdd-o',
            parseFloat(result['total']),
            settings.main_currency.icon
        );
    });
    monitor_add_callback('query_banks_total', function (result) {
        create_box(
            'banks balance',
            'fa-university',
            parseFloat(result['total']),
            settings.main_currency.icon
        );
    });
    monitor_add_callback('query_balances', function (result) {
        add_balances_table(result);
    });
    setup_log_watcher(add_alert_dropdown);
}

module.exports = function() {
    this.create_exchange_box = create_exchange_box;
    this.create_box = create_box;
    this.set_ui_main_currency = set_ui_main_currency;
    this.add_currency_dropdown = add_currency_dropdown;
    this.create_or_reload_dashboard = create_or_reload_dashboard;
    this.init_dashboard = init_dashboard;
};


