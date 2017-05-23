require("./zerorpc_client.js")();
require("./dashboard.js")();
var settings = require("./settings.js");
client.connect("tcp://127.0.0.1:4242");

function determine_location(url) {
    var split = url.split('#');
    if (split.length == 1 || split[1] == '') {
        return 'index';
    }
    return split[1];
}

function save_current_location() {
    console.log("---> " + window.location.href);
    var current_location = determine_location(window.location.href);
    if (current_location == 'index') {
        console.log("Saving index ... ");
        settings.page_index = $('#page-wrapper').html();
    } else if (current_location == 'external_trades') {
        console.log("Saving external trades ... ");
        settings.page_external_trades = $('#page-wrapper').html();
    } else {
        throw "Invalid link location " + current_location;
    }
}

function create_page_header(title) {
    return '<div class="row"><div class="col-lg-12"><h1 class=page-header">' + title + '</h1></div></div>';
}

function load_or_create_external_trades() {
    save_current_location();
    var str;
    if (!settings.page_external_trades) {
        str = create_page_header('External Trades');
        str += '<div class="row">TRADE STUFF</div>';
    } else {
        str = settings.page_external_trades;
    }
    $('#page-wrapper').html(str);
}


function create_currency_dropdown(fa_default_icon) {
    var str = '<li class="dropdown"><a class="dropdown-toggle" data-toggle="dropdown" href="#"><i id="current-main-currency" class="fa '+ fa_default_icon + ' fa-fw"></i> <i class="fa fa-caret-down"></i></a><ul class="dropdown-menu dropdown-alerts currency-dropdown"></ul></li>';
    $(str).appendTo($(".navbar-right"));
}

create_currency_dropdown(settings.default_currency.icon);
for (var i = 0; i < settings.CURRENCIES.length; i++) {
    add_currency_dropdown(settings.CURRENCIES[i]);
}
create_or_reload_dashboard();


$('#side-menu a').click(function(event) {
    event.preventDefault();
    var target_location = determine_location(this.href);

    if (target_location == 'external_trades') {
        load_or_create_external_trades();
    } else if( target_location == 'index') {
        create_or_reload_dashboard();
    }
});


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
