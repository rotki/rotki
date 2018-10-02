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

let exchanges = ['kraken', 'poloniex', 'bittrex', 'bitmex', 'binance'];
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

/**
 * @param usd_value        The usd value to convert to main currency and format
 * @param asset [optional] The name of the asset whose value we want
 * @param amount [optional] If asset was provided then also provide its amount
 */
function format_currency_value(usd_value, asset, amount) {
    let value;
    // if it's already in main currency don't do any conversion
    if (asset == settings.main_currency.ticker_symbol) {
        value = parseFloat(amount);
    } else {
        // turn it into the requested currency
        value = get_value_in_main_currency(usd_value);
    }
    // only show 2 decimal digits
    value = value.toFixed(settings.floating_precision);
    return value;
}

function add_settings_listeners() {
    $('#settingssubmit').click(function(event) {
        event.preventDefault();
        settings.floating_precision = $('#floating_precision').val();
        settings.historical_data_start = $('#historical_data_start').val();
        let main_currency = $('#maincurrencyselector').val();
        for (let i = 0; i < settings.CURRENCIES.length; i++) {
            if (main_currency == settings.CURRENCIES[i].ticker_symbol) {
                settings.main_currency = settings.CURRENCIES[i];
            }
        }

        let anonymized_logs = $('#anonymized_logs_input').is(":checked");
        let eth_rpc_port = $('#eth_rpc_port').val();
        let balance_save_frequency = $('#balance_save_frequency').val();
        let send_payload = {
            'ui_floating_precision': settings.floating_precision,
            'historical_data_start': settings.historical_data_start,
            'main_currency': main_currency,
            'eth_rpc_port': eth_rpc_port,
            'balance_save_frequency': balance_save_frequency,
            'anonymized_logs': anonymized_logs
        };
        // and now send the data to the python process
        client.invoke(
            "set_settings",
            send_payload,
            (error, res) => {
                if (error || res == null) {
                    showError('Settings Error', 'Error at modifying settings: ' + error);
                    return;
                }
                if (!res['result']) {
                    showError('Settings Error', 'Error at modifying settings: ' + res['message']);
                    return;
                }

                let message = 'Succesfully modified settings.';
                if ('message' in res && res['message'] != '') {
                    message = ' ' + message + res['message'];
                }
                showInfo('Success', message);
        });
    });

    $('#historical_data_start').datetimepicker({timepicker:false});
}

function create_settings_ui() {
    var str = page_header('Settings');
    str += settings_panel('General Settings', 'general_settings');
    $('#page-wrapper').html(str);

    str = form_entry('Floating Precision', 'floating_precision', settings.floating_precision, '');
    str += form_checkbox('anonymized_logs_input', 'Should logs by anonymized?', settings.anonymized_logs);
    str += form_entry('Date from when to count historical data', 'historical_data_start', settings.historical_data_start, '');
    str += form_select('Select Main Currency', 'maincurrencyselector', settings.CURRENCIES.map(x => x.ticker_symbol), settings.main_currency.ticker_symbol);
    str += form_entry('Eth RPC Port', 'eth_rpc_port', settings.eth_rpc_port, '');
    str += form_entry(
        'Balance data saving frequency in hours',
        'balance_save_frequency',
        settings.balance_save_frequency,
        ''
    );
    $(str).appendTo($('.panel-body'));

    str = form_button('Save', 'settingssubmit');
    str += '</form></div>';
    $(str).appendTo($('.panel-body'));
}

function get_icon_map() {
    let fs = require('fs');
    let icon_dir = 'node_modules/cryptocurrency-icons/svg/color/';
    
    let icon_map = {};
    fs.readdirSync(icon_dir)
        .forEach(function(v) {
            icon_map[v.substr(0,v.indexOf('.'))] = icon_dir + v;
    });
    return icon_map;
}

let icon_map_list = get_icon_map();

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
        settings.historical_data_start = "01/08/2015";
        settings.current_location = null;
        settings.page_index = null;
        settings.page_settings = null;
        settings.page_otctrades = null;
        settings.page_user_settings = null;
        settings.page_accounting_settings = null;
        settings.page_taxreport = null;
        settings.page_exchange = {};
        settings.datetime_format = 'd/m/Y G:i';
        settings.has_premium = false;
        settings.premium_should_sync = false;
        settings.start_suggestion = 'inactive';
        settings.eth_rpc_port = '8545';
        settings.balance_save_frequency = 24;
        settings.last_balance_save = 0;
        settings.ICON_MAP_LIST = get_icon_map();
        settings.anonymized_logs = false;
    }
    this.get_value_in_main_currency = get_value_in_main_currency;
    this.assert_exchange_exists = assert_exchange_exists;
    this.create_settings_ui = create_settings_ui;
    this.add_settings_listeners = add_settings_listeners;
    this.format_currency_value = format_currency_value;
    this.get_fiat_usd_value = get_fiat_usd_value;

    return settings;
};
