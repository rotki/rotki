require("./zerorpc_client.js")();
require("./dashboard.js")();
require("./exchange.js")();
require("./utils.js")();
var settings = require("./settings.js");
client.connect("tcp://127.0.0.1:4242");

function create_page_header(title) {
    return '<div class="row"><div class="col-lg-12"><h1 class=page-header">' + title + '</h1></div></div>';
}

function load_or_create_external_trades() {
    var str;
    change_location('external_trades');
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
    } else if (target_location == 'index') {
        create_or_reload_dashboard();
    } else {
        throw "Invalid link target location " + target_location;
    }
});
