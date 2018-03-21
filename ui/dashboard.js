require("./zerorpc_client.js")();
var settings = require("./settings.js")();
require("./usersettings.js")();
require("./monitor.js")();
require("./utils.js")();
require("./exchange.js")();
require("./balances_table.js")();
require("./navigation.js")();
require("./userunlock.js")();

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


function create_dashboard_header() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class="page-header">Dashboard</h1></div></div><div class="row"><div id="dashboard-contents" class="col-lg-12"></div></div>';
    $(str).appendTo($('#page-wrapper'));
}

function create_exchange_box(exchange, number, currency_icon) {
    let current_location = settings.current_location;
    if (current_location != 'index') {
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
    number = format_currency_value(number);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+exchange+'_box"><div class="row"><div class="col-xs-3"><i><img title="' + exchange + '" class="' + css_class + '" src="images/'+ exchange +'.png"  /></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i id="currencyicon" class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#exchange_' + exchange +'"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    $(str).prependTo($('#dashboard-contents'));
    add_exchange_on_click();
    // finally save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function create_box (id, icon, number, currency_icon) {
    let current_location = settings.current_location;
    if (current_location != 'index') {
        return;
    }
    if($("#" + id).length != 0) {
        //already exists
        return;
    }
    number = format_currency_value(number);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+id+'"><div class="row"><div class="col-xs-3"><i title="' + id + '" class="fa '+ icon +'  fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i id="currencyicon" class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div>';
    if (id == 'foo') {
        str += '<a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>';
        str += '<div class="clearfix"></div></div></a></div>';

    } else {
        str += '<div class="panel-footer">';
        str += '<div class="clearfix"></div></div></div>';
    }

    $(str).prependTo($('#dashboard-contents'));
    // also save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

function set_ui_main_currency(currency_ticker_symbol) {
    var currency = null;
    for (let i = 0; i < settings.CURRENCIES.length; i ++) {
        if (currency_ticker_symbol == settings.CURRENCIES[i].ticker_symbol) {
            currency = settings.CURRENCIES[i];
            break;
        }
    }

    if (!currency) {
        throw "Invalid currency " + currency_ticker_symbol + " requested at set_ui_main_currency";
    }

    $('#current-main-currency').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
    settings.main_currency = currency;

    reload_boxes_after_currency_change(currency);
    // also adjust tables if they exist
    reload_balance_table_if_existing();
    reload_exchange_tables_if_existing();
    reload_usersettings_tables_if_existing();
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
        if (currency.ticker_symbol == settings.main_currency.ticker_symbol) {
            // nothing to do
            return;
        }
        client.invoke("set_main_currency", currency.ticker_symbol, (error, res) => {
            if(error) {
                showError('Error', 'Error at setting main currency: ' + error);
            } else {
                set_ui_main_currency(currency.ticker_symbol);
            }
        });
    });
}

function get_fiat_exchange_rates(currencies) {
    client.invoke("get_fiat_exchange_rates", currencies, (error, res) => {
        if (error || res == null) {
            showError('Connectivity Error', 'Failed to acquire fiat to USD exchange rates: ' + error);
            return;
        }
        console.log("get_fiat_exchange_rates for " + currencies + " returned okay");
        let rates = res['exchange_rates'];
        for (let asset in rates) {
            if(rates.hasOwnProperty(asset)) {
                settings.usd_to_fiat_exchange_rates[asset] = parseFloat(rates[asset]);
            }
        }

        // something noticed is that if a zero rpc call from node to python happens
        // within very close proximity to another one with the same function then
        // it's very possible one will timeout with heartbear error. That is why
        // we call the full exchange rate update here after we get the main
        // currency exchange rate
        if (currencies) {
            get_fiat_exchange_rates(); // for all currencies
        }
    });
}

function get_settings() {
    client.invoke("get_settings", (error, res) => {
        if (error || res == null) {
            startup_error(
                "get_settings response was: " + res + " and error: " + error,
                "get_settings RPC failed"
            );
        } else {
            console.log("server is ready");
            // even though we called to get rates at start we need to make at
            // least 1 call for only the main currency usd rate to be ready asap
            get_fiat_exchange_rates([res['main_currency']]);
            set_ui_main_currency(res['main_currency']);
            // set the other settings
            settings.floating_precision = res['ui_floating_precision'];
            settings.historical_data_start_date = res['historical_data_start_date'];

            $("body").removeClass("loading");
            prompt_sign_in();
        }
    });
}

function create_or_reload_dashboard() {
    change_location('index');
    if (!settings.page_index) {
        $("body").addClass("loading");
        console.log("At create/reload, with a null page index");
        get_settings();
    } else {
        console.log("At create/reload, with a Populated page index");
        $('#page-wrapper').html('');
        create_dashboard_header();
        create_dashboard_from_saved_balances();
        total_table_recreate();
        add_exchange_on_click();
    }
}

function* iterate_saved_balances() {
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

function create_dashboard_from_saved_balances() {
    // must only be called if we are at index
    for (let result of iterate_saved_balances()) {
        let location = result[0];
        let total = result[1];
        let icon = result[2];
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            create_exchange_box(
                location,
                total,
                settings.main_currency.icon
            );
        } else {
            create_box(
                location,
                icon,
                total,
                settings.main_currency.icon
            );
        }
    }
}

function reload_boxes_after_currency_change(currency) {
    // must only be called if we are at index
    for (let result of iterate_saved_balances()) {
        let location = result[0];
        let total = result[1];
        let icon = result[2];
        let number = format_currency_value(total);
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            $('#'+location+'_box div.huge').html(number);
            $('#'+location+'_box i#currencyicon').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
        } else {
            $('#'+location+' div.huge').html(number);
            $('#'+location+' div.huge').html(number);
            $('#'+location+' i#currencyicon').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
        }
    }
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
    monitor_add_callback('query_exchange_balances', function (result) {
        if ('error' in result) {
            showError(
                'Exchange Query Error',
                'Querying an exchange died because of: ' + result['error'] + '. ' +
                    'Check the logs for more details.'
            );
            return;
        }
        let total = get_total_asssets_value(result['balances']);
        create_exchange_box(
            result['name'],
            total,
            settings.main_currency.icon
        );
        total_table_add_balances(result['name'], result['balances']);
    });
    monitor_add_callback('query_blockchain_balances', function (result) {
        if ('error' in result) {
            showError(
                'Blockchain Query Error',
                'Querying blockchain balances died because of: ' + result['error'] + '. ' +
                    'Check the logs for more details.'
            );
            return;
        }
        let total = get_total_asssets_value(result['totals']);
        if (total != 0.0) {
            create_box(
                'blockchain_balance',
                'fa-hdd-o',
                total,
                settings.main_currency.icon
            );
            total_table_add_balances('blockchain', result['totals']);
        }
    });
    setup_log_watcher(add_alert_dropdown);
}

module.exports = function() {
    this.create_exchange_box = create_exchange_box;
    this.create_box = create_box;
    this.add_currency_dropdown = add_currency_dropdown;
    this.create_or_reload_dashboard = create_or_reload_dashboard;
    this.init_dashboard = init_dashboard;
};


