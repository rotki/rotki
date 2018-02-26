require("./elements.js")();

var settings = null;
function Currency(name, icon, ticker_symbol, unicode_symbol) {
    this.name = name;
    this.icon = icon;
    this.ticker_symbol = ticker_symbol;
    this.unicode_symbol = unicode_symbol;
}

function assert_exchange_exists(name) {
    if (settings.EXCHANGES.indexOf(name) < 0) {
        throw "Invalid exchange name: " + name;
    }
}

let exchanges = ['kraken', 'poloniex', 'bittrex', 'binance'];
let currencies = [
    new Currency("United States Dollar", "fa-usd", "USD", "$"),
    new Currency("Euro", "fa-eur", "EUR", "€"),
    new Currency("British Pound", "fa-gbp", "GBP", "£"),
    new Currency("Japanese Yen", "fa-jpy", "JPY", "¥"),
    new Currency("Chinese Yuan", "fa-jpy", "CNY", "¥"),
];

function get_value_in_main_currency(usd_value) {
    let symbol = settings.main_currency.ticker_symbol;
    usd_value = parseFloat(usd_value);
    if (symbol == 'USD') {
        return usd_value;
    }
    return usd_value * settings.usd_to_fiat_exchange_rates[symbol];
}

function get_fiat_usd_value(currency, amount) {
    amount = parseFloat(amount);
    if (currency == 'USD') {
        return amount;
    }
    return amount / settings.usd_to_fiat_exchange_rates[currency];
}

function format_currency_value(number) {
    // turn it into the requested currency
    number = get_value_in_main_currency(number);
    // only show 2 decimal digits
    number = number.toFixed(settings.floating_precision);
    return number;
}

function add_settings_listeners() {
    $('#settingssubmit').click(function(event) {
        event.preventDefault();
        settings.floating_precision = $('#floating_precision').val();
        settings.historical_data_start_date = $('#historical_data_start_date').val();
        let main_currency = $('#maincurrencyselector').val();
        for (let i = 0; i < settings.CURRENCIES.length; i++) {
            if (main_currency == settings.CURRENCIES[i].ticker_symbol) {
                settings.main_currency = settings.CURRENCIES[i];
            }
        }

        let send_payload = {
                "ui_floating_precision": settings.floating_precision,
                "historical_data_start_date": settings.historical_data_start_date,
                "main_currency": main_currency

        };
        // and now send the data to the python process
        client.invoke(
            "set_settings",
            send_payload,
            (error, res) => {
                if (error || res == null) {
                    console.log("Error at setting settings: " + error);
                } else {
                    console.log("Set settings returned " + res);
                }
        });
    });

    $('#historical_data_start_date').datetimepicker({timepicker:false});
}

function create_settings_ui() {
    var str = page_header('Settings');
    str += settings_panel('General Settings', 'general_settings');
    $('#page-wrapper').html(str);

    str = form_entry('Floating Precision', 'floating_precision', settings.floating_precision, '');
    str += form_entry('Date', 'historical_data_start_date', settings.historical_data_start_date, '');
    str += form_select('Select Main Currency', 'maincurrencyselector', settings.CURRENCIES.map(x => x.ticker_symbol), settings.main_currency.ticker_symbol);
    $(str).appendTo($('.panel-body'));

    str = form_button('Save', 'settingssubmit');
    str += '</form></div>';
    $(str).appendTo($('.panel-body'));
}

module.exports = function() {
    if (!settings) {
        settings = {};
        settings.usd_to_fiat_exchange_rates = {};
        settings.EXCHANGES = exchanges;
        settings.connected_exchanges = [];
        settings.CURRENCIES = currencies;
        settings.default_currency = currencies[0];
        settings.main_currency = currencies[0];
        settings.floating_precision = 2;
        settings.historical_data_start_date = "01/08/2015";
        settings.current_location = null;
        settings.page_index = null;
        settings.page_settings = null;
        settings.page_otctrades = null;
        settings.page_usersettings = null;
        settings.page_taxreport = null;
        settings.page_exchange = {};
        settings.datetime_format = 'd/m/Y G:i';
        settings.has_premium = false;
        settings.premium_should_sync = false;
    }
    this.get_value_in_main_currency = get_value_in_main_currency;
    this.assert_exchange_exists = assert_exchange_exists;
    this.create_settings_ui = create_settings_ui;
    this.add_settings_listeners = add_settings_listeners;
    this.format_currency_value = format_currency_value;
    this.get_fiat_usd_value = get_fiat_usd_value;

    return settings;
};
