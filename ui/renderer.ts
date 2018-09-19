import { init_navigation } from './navigation';
import { add_currency_dropdown, create_or_reload_dashboard, init_dashboard } from './dashboard';
import { init_monitor } from './monitor';
import { init_user_settings } from './user_settings';
import { init_taxreport } from './taxreport';
import { settings } from './settings';
import { service } from './rotkehlchen_service';

service.connect();

function create_currency_dropdown(fa_default_icon: string) {
    const str = `<li class="dropdown">
    <a class="dropdown-toggle" data-toggle="dropdown" href="#">
        <i id="current-main-currency" class="fa ${fa_default_icon} fa-fw"></i>
        <i class="fa fa-caret-down"></i>
    </a>
    <ul class="dropdown-menu currency-dropdown"></ul>
</li>`;
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
