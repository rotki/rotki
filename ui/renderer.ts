import client from './zerorpc_client';
import { settings } from './settings';
import { add_currency_dropdown, create_or_reload_dashboard, init_dashboard } from './dashboard';
import { init_monitor } from './monitor';
import { init_user_settings } from './user_settings';
import { init_navigation } from './navigation';
import { init_taxreport } from './taxreport';
client.connect('tcp://127.0.0.1:4242');

function create_page_header(title: string) {
    return '<div class="row"><div class="col-lg-12"><h1 class=page-header">' + title + '</h1></div></div>';
}


function create_currency_dropdown(fa_default_icon: any) {
    let str = '<li class="dropdown"><a class="dropdown-toggle" data-toggle="dropdown" href="#"><i id="current-main-currency" class="fa ' + fa_default_icon + ' fa-fw"></i> <i class="fa fa-caret-down"></i></a><ul class="dropdown-menu currency-dropdown"></ul></li>';
    $(str).appendTo($('.navbar-right'));
}

create_currency_dropdown(settings.default_currency.icon);
for (let i = 0; i < settings.CURRENCIES.length; i++) {
    add_currency_dropdown(settings.CURRENCIES[i]);
}


init_navigation();
init_monitor();
init_dashboard();
init_user_settings();
init_taxreport();
create_or_reload_dashboard();
