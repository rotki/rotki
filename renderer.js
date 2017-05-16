const zerorpc = require("zerorpc");
let client = new zerorpc.Client();

function Currency(name, icon, ticker_symbol) {
    this.name = name;
    this.icon = icon;
    this.ticker_symbol = ticker_symbol;
}

let currencies = [
    new Currency("United States Dollar", "fa-usd", "USD"),
    new Currency("Euro", "fa-eur", "EUR"),
    new Currency("British Pound", "fa-gbp", "GBP"),
    new Currency("Japanese Yen", "fa-jpy", "JPY"),
    new Currency("Chinese Yuan", "fa-jpy", "CNY"),
];
let default_currency = currencies[0];

client.connect("tcp://127.0.0.1:4242");


let body = $("body");
body.addClass("loading");

function create_box(id, icon, number, text) {
    var str = '<div class="panel panel-primary"><div class="panel-heading" id="'+id+'"><div class="row"><div class="col-xs-3"><i class="fa '+ icon +'  fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">'+number+'</div><div id="status_box_text">'+text+'</div></div></div></div><a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
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

function add_currency_dropdown(currency) {
    var str = '<li><a id="change-to-'+ currency.ticker_symbol.toLowerCase() +'" href="#"><div><i class="fa '+ currency.icon +' fa-fw"></i> Set '+ currency.name +' as the main currency</div></a></li><li class="divider"></li>';
    $(str).appendTo($(".currency-dropdown"));

    $('#change-to-'+ currency.ticker_symbol.toLowerCase()).bind('click', function() {
	client.invoke("set_main_currency", currency.ticker_symbol, (error, res) => {
	    if(error) {
		showAlert('alert-danger', error);
	    } else {
		$('#current-main-currency').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
	    }
	});
    });

}

client.invoke("echo", "server ready", (error, res) => {
    if(error || res !== 'server ready') {
	var loading_wrapper = document.querySelector('.loadingwrapper');
	var loading_wrapper_text = document.querySelector('.loadingwrapper_text');
	console.log("Response was: " + res);
	console.error(error);
	loading_wrapper.style.background = "rgba( 255, 255, 255, .8 ) 50% 50% no-repeat";
	loading_wrapper_text.textContent = "ERROR: Failed to connect to the backend. Check Log";
  } else {
      body.removeClass("loading");
      console.log("server is ready");
  }
});


a = create_box("status_box", "fa-plug", "1", "TEXT1");
a.appendTo($('#leftest-column'));
create_box("status_box", "fa-money", "2", "TEXT2").appendTo($('#leftest-column'));

create_currency_dropdown(default_currency.icon);
for (var i = 0; i < currencies.length; i++) {
    add_currency_dropdown(currencies[i]);
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
