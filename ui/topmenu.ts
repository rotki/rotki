

import { Currency, format_currency_value, settings } from './settings';
import { iterate_saved_balances } from './utils';
import { reload_balance_table_if_existing } from './balances_table';
import { reload_exchange_tables_if_existing } from './exchange';
import { reload_user_settings_tables_if_existing } from './user_settings';

export function set_ui_main_currency(currency_ticker_symbol: string) {
    let currency = null as Currency;
    for (let i = 0; i < settings.CURRENCIES.length; i ++) {
        if (currency_ticker_symbol === settings.CURRENCIES[i].ticker_symbol) {
            currency = settings.CURRENCIES[i];
            break;
        }
    }

    if (!currency) {
        throw new Error('Invalid currency ' + currency_ticker_symbol + ' requested at set_ui_main_currency');
    }

    $('#current-main-currency').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
    settings.main_currency = currency;

    reload_boxes_after_currency_change(currency);
    // also adjust tables if they exist
    reload_balance_table_if_existing();
    reload_exchange_tables_if_existing();
    reload_user_settings_tables_if_existing();
}

function reload_boxes_after_currency_change(currency: Currency) {
    // must only be called if we are at index
    for (let result of iterate_saved_balances()) {
        let location = result[0];
        let total = result[1];
        let number = format_currency_value(total);
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            $('#' + location + '_box div.huge').html(number);
            $('#' + location + '_box i#currencyicon').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
        } else {
            $('#' + location + '_box div.huge').html(number);
            $('#' + location + '_box i#currencyicon').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
        }
    }
}