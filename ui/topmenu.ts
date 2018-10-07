import {iterate_saved_balances, reload_balance_table_if_existing} from './balances_table';
import {reload_user_settings_tables_if_existing} from './user_settings';
import {reload_exchange_table_if_existing} from './exchange';
import {format_currency_value, settings} from './settings';
import {Currency} from './model/currency';

export function set_ui_main_currency(currency_ticker_symbol: string) {
    let currency = null;
    for (let i = 0; i < settings.CURRENCIES.length; i++) {
        if (currency_ticker_symbol === settings.CURRENCIES[i].ticker_symbol) {
            currency = settings.CURRENCIES[i];
            break;
        }
    }

    if (!currency) {
        throw new Error(`Invalid currency ${currency_ticker_symbol} requested at set_ui_main_currency`);
    }

    $('#current-main-currency').removeClass().addClass(`fa ${currency.icon} fa-fw`);
    settings.main_currency = currency;

    reload_boxes_after_currency_change(currency);
    // also adjust tables if they exist
    reload_balance_table_if_existing();
    if (settings.current_location && settings.current_location.startsWith('exchange_')) {
        const exchange_name = settings.current_location.substring(9);
        reload_exchange_table_if_existing(exchange_name);
    }
    reload_user_settings_tables_if_existing();
}

function reload_boxes_after_currency_change(currency: Currency) {
    // must only be called if we are at index
    for (const result of iterate_saved_balances()) {
        const location = result[0] as string;
        const total = result[1] as number;
        const number = format_currency_value(total.toString());
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            $(`#${location}_box div.huge`).html(number);
            $(`#${location}_box i#currencyicon`).removeClass().addClass(`fa ${currency.icon} fa-fw`);
        } else {
            $(`#${location}_box div.huge`).html(number);
            $(`#${location}_box i#currencyicon`).removeClass().addClass(`fa ${currency.icon} fa-fw`);
        }
    }
}
