import { form_button, form_entry, form_select, page_header, settings_panel } from './elements';
import { showError, showInfo } from './utils';
import client from './zerorpc_client';

export let settings = {} as Settings;
export class Currency {
    name: string;
    icon: string;
    ticker_symbol: string;
    unicode_symbol: string;
    constructor(name: string, icon: string, ticker_symbol: string, unicode_symbol: string) {
        this.name = name;
        this.icon = icon;
        this.ticker_symbol = ticker_symbol;
        this.unicode_symbol = unicode_symbol;
    }
} 

export function assert_exchange_exists(name: string) {
    if (settings.EXCHANGES.indexOf(name) < 0) {
        throw new Error('Invalid exchange name: ' + name);
    }
}

let exchanges = ['kraken', 'poloniex', 'bittrex', 'binance'];
let currencies = [
    new Currency('United States Dollar', 'fa-usd', 'USD', '$'),
    new Currency('Euro', 'fa-eur', 'EUR', '€'),
    new Currency('British Pound', 'fa-gbp', 'GBP', '£'),
    new Currency('Japanese Yen', 'fa-jpy', 'JPY', '¥'),
    new Currency('Chinese Yuan', 'fa-jpy', 'CNY', '¥'),
];

export function get_value_in_main_currency(usd_value: string | number) {
    const symbol = settings.main_currency.ticker_symbol;
    const f_usd_value: number = parseFloat(usd_value.toString());
    if (symbol === 'USD') {
        return f_usd_value;
    }
    return f_usd_value * settings.usd_to_fiat_exchange_rates[symbol];
}

export function get_fiat_usd_value(currency: string, amount: string) {
    const f_amount: number = parseFloat(amount.toString());
    if (currency === 'USD') {
        return f_amount;
    }
    return f_amount / settings.usd_to_fiat_exchange_rates[currency];
}

/**
 * @param usd_value        The usd value to convert to main currency and format
 * @param asset [optional] The name of the asset whose value we want
 * @param amount [optional] If asset was provided then also provide its amount
 */
export function format_currency_value(
    usd_value: string | number, 
    asset?: string, 
    amount?: string
) {
    let value;
    // if it's already in main currency don't do any conversion
    if (asset === settings.main_currency.ticker_symbol) {
        value = parseFloat(amount);
    } else {
        // turn it into the requested currency
        value = get_value_in_main_currency(usd_value);
    }
    // only show 2 decimal digits
    value = value.toFixed(settings.floating_precision);
    return value;
}

export function add_settings_listeners() {
    $('#settingssubmit').click(function(event: JQuery.Event<HTMLElement, null>) {
        event.preventDefault();
        settings.floating_precision = parseInt($('#floating_precision').val().toString());
        settings.historical_data_start = $('#historical_data_start').val().toString();
        let main_currency = $('#maincurrencyselector').val();
        for (let i = 0; i < settings.CURRENCIES.length; i++) {
            if (main_currency === settings.CURRENCIES[i].ticker_symbol) {
                settings.main_currency = settings.CURRENCIES[i];
            }
        }

        let eth_rpc_port = $('#eth_rpc_port').val();
        let balance_save_frequency = $('#balance_save_frequency').val();
        let send_payload = {
            'ui_floating_precision': settings.floating_precision,
            'historical_data_start': settings.historical_data_start,
            'main_currency': main_currency,
            'eth_rpc_port': eth_rpc_port,
            'balance_save_frequency': balance_save_frequency
        };
        // and now send the data to the python process
        client.invoke(
            'set_settings',
            send_payload,
            (error, res) => {
                if (error || res == null) {
                    showError('Settings Error', 'Error at modifying settings: ' + error);
                    return;
                }
                if (!res.result) {
                    showError('Settings Error', 'Error at modifying settings: ' + res.message);
                    return;
                }

                let message = 'Succesfully modified settings.';
                if ('message' in res && res.message !== '') {
                    message = ' ' + message + res.message;
                }
                showInfo('Success', message);
        });
    });

    $('#historical_data_start').datetimepicker({timepicker: false});
}

export function create_settings_ui() {
    let str = page_header('Settings');
    str += settings_panel('General Settings', 'general_settings');
    $('#page-wrapper').html(str);

    str = form_entry(
        'Floating Precision', 
        'floating_precision', 
        settings.floating_precision, ''
    );
    str += form_entry(
        'Date from when to count historical data', 
        'historical_data_start', 
        settings.historical_data_start, ''
    );
    str += form_select(
        'Select Main Currency', 'maincurrencyselector', 
        settings.CURRENCIES.map(x => x.ticker_symbol), settings.main_currency.ticker_symbol
    );
    str += form_entry(
        'Eth RPC Port', 
        'eth_rpc_port', 
        settings.eth_rpc_port, 
        ''
    );
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

interface Settings {
    usd_to_fiat_exchange_rates: any;
    EXCHANGES: Array<string>;
    connected_exchanges: Array<string>;
    CURRENCIES: Array<Currency>;
    default_currency: Currency;
    main_currency: Currency;
    floating_precision: number;
    historical_data_start: string;
    current_location: string;
    page_index: string;
    page_settings: string;
    page_otctrades: string;
    page_user_settings: string;
    page_accounting_settings: string;
    page_taxreport: string;
    page_exchange: any;
    datetime_format: string;
    has_premium: boolean;
    premium_should_sync: boolean;
    start_suggestion: string;
    eth_rpc_port: string;
    balance_save_frequency: number;
    include_crypto2crypto: boolean;
    taxfree_after_period: number;
    last_balance_save: number;
}

settings.usd_to_fiat_exchange_rates = {};
settings.EXCHANGES = exchanges;
settings.connected_exchanges = [];
settings.CURRENCIES = currencies;
settings.default_currency = currencies[0];
settings.main_currency = currencies[0];
settings.floating_precision = 2;
settings.historical_data_start = '01/08/2015';
settings.current_location = null;
settings.page_index = null;
settings.page_settings = null;
settings.page_otctrades = null;
settings.page_user_settings = null;
settings.page_accounting_settings = null;
settings.page_taxreport = null;
settings.last_balance_save = 0;
settings.page_exchange = {};
settings.datetime_format = 'd/m/Y G:i';
settings.has_premium = false;
settings.premium_should_sync = false;
settings.start_suggestion = 'inactive';
settings.eth_rpc_port = '8545';
settings.balance_save_frequency = 24;
settings.include_crypto2crypto = false;
settings.taxfree_after_period = 0;

