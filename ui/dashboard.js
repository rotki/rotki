require("./zerorpc_client.js")();
var settings = require("./settings.js");
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



function showAlert(type, text) {
    var str = '<div class="alert '+ type +' alert-dismissable"><button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>'+ text +'</div>';
    $(str).prependTo($("#wrapper"));
}

function add_exchange_on_click() {
    $('.panel a').click(function(event) {
        event.preventDefault();
        var target_location = determine_location(this.href);
        if (target_location.startsWith('exchange_')) {
            exchange_name = target_location.substring(9);
            settings.assert_exchange_exists(exchange_name);
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
    if (exchange == 'poloniex') {
        css_class = 'exchange-icon';
    }
    // only show 2 decimal digits
    number = number.toFixed(2);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+exchange+'_box"><div class="row"><div class="col-xs-3"><i><img title="' + exchange + '" class="' + css_class + '" src="images/'+ exchange +'.png"  /></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#exchange_' + exchange +'"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    $(str).appendTo($('#leftest-column'));
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

    // only show 2 decimal digits
    number = number.toFixed(2);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+id+'"><div class="row"><div class="col-xs-3"><i title="' + id + '" class="fa '+ icon +'  fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    $(str).appendTo($('#leftest-column'));
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



function get_initial_settings() {
    client.invoke("get_initial_settings", (error, res) => {
        if (error || res == null) {
            var loading_wrapper = document.querySelector('.loadingwrapper');
            var loading_wrapper_text = document.querySelector('.loadingwrapper_text');
            console.log("get_initial_settings response was: " + res);
            console.error("get_initial_settings error was: " + error);
            loading_wrapper.style.background = "rgba( 255, 255, 255, .8 ) 50% 50% no-repeat";
            loading_wrapper_text.textContent = "ERROR: Failed to connect to the backend. Check Log";
        } else {
            // set main currency
            console.log("server is ready");
            settings.main_currency = res['main_currency'];
            for (var i = 0; i < settings.CURRENCIES.length; i ++) {
                if (settings.main_currency == settings.CURRENCIES[i].ticker_symbol) {
                    set_ui_main_currency(settings.CURRENCIES[i]);
                    settings.main_currency = settings.CURRENCIES[i];
                    break;
                }
            }
            // make separate queries for all registered exchanges
            let exchanges = res['exchanges'];
            for (var i = 0; i < exchanges.length; i++) {
                let exx = exchanges[i];
                client.invoke("query_exchange_total_async", exchanges[i], true, function (error, res) {
                    if (error || res == null) {
                        console.log("Error at first query of an exchange's balance: " + error);
                    } else {
                        create_task(res['task_id'], 'query_exchange_total', 'Query ' + exx + ' Exchange');
                    }
                });
            }
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
        get_initial_settings();
        get_blockchain_total();
        get_banks_total();
    } else {
        console.log("At create/reload, with a Populated page index");
        $('#page-wrapper').html(settings.page_index);
        add_exchange_on_click();
    }

    // also if there are any saved results apply them
    for (var i = 0; i < saved_results.length; i ++) {
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


