const zerorpc = require("zerorpc");
// max timeout is now 25 seconds
let client = new zerorpc.Client({timeout:25, heartbeatInterval: 10000});

function Currency(name, icon, ticker_symbol) {
    this.name = name;
    this.icon = icon;
    this.ticker_symbol = ticker_symbol;
}

let EXCHANGES = ['kraken', 'poloniex', 'bittrex'];

let CURRENCIES = [
    new Currency("United States Dollar", "fa-usd", "USD"),
    new Currency("Euro", "fa-eur", "EUR"),
    new Currency("British Pound", "fa-gbp", "GBP"),
    new Currency("Japanese Yen", "fa-jpy", "JPY"),
    new Currency("Chinese Yuan", "fa-jpy", "CNY"),
];
let default_currency = CURRENCIES[0];
let main_currency = default_currency;
let jobs = ['false', 'false'];
client.connect("tcp://127.0.0.1:4242");



let body = $("body");
body.addClass("loading");

function create_box(id, icon, number, currency_icon) {
    // only show 2 decimal digits
    number = number.toFixed(2);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+id+'"><div class="row"><div class="col-xs-3"><i title="' + id + '" class="fa '+ icon +'  fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    return $(str);
}

function create_exchange_box(exchange, number, currency_icon) {
    css_class = 'exchange-icon-inverted';
    if (exchange == 'poloniex') {
	css_class = 'exchange-icon';
    }
    // only show 2 decimal digits
    number = number.toFixed(2);
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+exchange+'_box"><div class="row"><div class="col-xs-3"><i><img title="' + exchange + '" class="' + css_class + '" src="ui/images/'+ exchange +'.png"  /></i></div><div class="col-xs-9 text-right"><div class="huge">'+ number +'</div><div id="status_box_text"><i class="fa '+ currency_icon + ' fa-fw"></i></div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    return $(str);
}

function showAlert(type, text) {
    var str = '<div class="alert '+ type +' alert-dismissable"><button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>'+ text +'</div>';
    $(str).prependTo($("#wrapper"));
}

function create_currency_dropdown(fa_default_icon) {
    var str = '<li class="dropdown"><a class="dropdown-toggle" data-toggle="dropdown" href="#"><i id="current-main-currency" class="fa '+ fa_default_icon + ' fa-fw"></i> <i class="fa fa-caret-down"></i></a><ul class="dropdown-menu dropdown-alerts currency-dropdown"></ul></li>';
    $(str).appendTo($(".navbar-right"));
}

function set_ui_main_currency(currency) {
    $('#current-main-currency').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
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

function finish_job() {
    var finished_one = false;
    for (var i = 0; i < jobs.length; i ++) {
	if (jobs[i] == false) {
	    if (!finished_one) {
		jobs[i] = true;
		finished_one = true;
		continue;
	    } else {
		return;
	    }
	}
    }

    // if we get here it means we finished all jobs
    $('#top-loading-icon').removeClass().addClass('fa fa-check-circle fa-fw');
}

client.invoke("get_initial_settings", (error, res) => {
    if (error || res == null) {
	var loading_wrapper = document.querySelector('.loadingwrapper');
	var loading_wrapper_text = document.querySelector('.loadingwrapper_text');
	console.log("Response was: " + res);
	console.error(error);
	loading_wrapper.style.background = "rgba( 255, 255, 255, .8 ) 50% 50% no-repeat";
	loading_wrapper_text.textContent = "ERROR: Failed to connect to the backend. Check Log";
    } else {
	// set main currency
	console.log("server is ready");
	main_currency = res['main_currency'];
	for (var i = 0; i < CURRENCIES.length; i ++) {
	    if (main_currency == CURRENCIES[i].ticker_symbol) {
		set_ui_main_currency(CURRENCIES[i]);
		main_currency = CURRENCIES[i];
		break;
	    }
	}
	// make separate queries for all registered exchanges
	let exchanges = res['exchanges'];
	for (var i = 0; i < exchanges.length; i++) {
	    jobs.push(false);
	}
	for (var i = 0; i < exchanges.length; i++) {
	    client.invoke("query_exchange_total", exchanges[i], true, function (error, res) {
		if (error || res == null) {
		    console.log("Error at first query of an exchange's balance: " + error);
		} else {
		    create_exchange_box(res['name'], res['total'], main_currency.icon).appendTo($('#leftest-column'));
		    finish_job();
		}
	    });
	}
	body.removeClass("loading");
    }
});

client.invoke("query_blockchain_total", (error, res) => {
    if (error || res == null) {
	console.log("Error at querying blockchain total: " + error);
    } else {
	create_box('blockchain balance', 'fa-hdd-o', res['total'], main_currency.icon).appendTo($('#leftest-column'));
	finish_job();
    }
});
client.invoke("query_banks_total", (error, res) => {
    if (error || res == null) {
	console.log("Error at querying bank total: " + error);
    } else {
	create_box('banks balance', 'fa-university', res['total'], main_currency.icon).appendTo($('#leftest-column'));
	finish_job();
    }
});


create_currency_dropdown(default_currency.icon);
for (var i = 0; i < CURRENCIES.length; i++) {
    add_currency_dropdown(CURRENCIES[i]);
}



// let result = document.querySelector('#result');
// formula.addEventListener('input', () => {
//   client.invoke("calc", formula.value, (error, res) => {
//     if(error) {
// 	console.error(error);
//     } else {
// 	result.textContent = res;
//     }
//   });
// });

// formula.dispatchEvent(new Event('input'));
