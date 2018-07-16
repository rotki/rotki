var settings = require("./settings.js")();
require("./utils.js")();
require("./balances_table.js")();
require("./exchange.js")();
require("./user_settings.js")();

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
    reload_user_settings_tables_if_existing();
}

function reload_boxes_after_currency_change(currency) {
    // must only be called if we are at index
    for (let result of iterate_saved_balances()) {
        let location = result[0];
        let total = result[1];
        let number = format_currency_value(total);
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            $('#'+location+'_box div.huge').html(number);
            $('#'+location+'_box i#currencyicon').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
        } else {
            $('#'+location+'_box div.huge').html(number);
            $('#'+location+'_box i#currencyicon').removeClass().addClass('fa ' + currency.icon + ' fa-fw');
        }
    }
}

module.exports = function() {
    this.set_ui_main_currency = set_ui_main_currency;
};
