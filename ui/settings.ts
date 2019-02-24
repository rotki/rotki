import {showError, showInfo} from './utils';
import {form_button, form_checkbox, form_entry, form_select, page_header, settings_panel} from './elements';
import * as fs from 'fs';
import * as path from 'path';
import {Currency} from './model/currency';
import {service} from './rotkehlchen_service';


export class Settings {
    user_logged = false;
    usd_to_fiat_exchange_rates: { [key: string]: number } = {};
    connected_exchanges: string[] = [];
    floating_precision = 2;
    historical_data_start = '01/08/2015';
    current_location?: string;
    datetime_format = 'd/m/Y G:i';
    has_premium = false;
    premium_should_sync = false;
    start_suggestion = 'inactive';
    eth_rpc_port = '8545';
    balance_save_frequency = 24;
    last_balance_save = 0;
    include_crypto2crypto = true;
    include_gas_costs = true;
    taxfree_after_period = 0;
    anonymized_logs = false;
    date_display_format = '%d/%m/%Y %H:%M:%S %Z';
    private exchanges = ['kraken', 'poloniex', 'bittrex', 'bitmex', 'binance'];
    private currencies = [
        new Currency('United States Dollar', 'fa-usd', 'USD', '$'),
        new Currency('Euro', 'fa-eur', 'EUR', '€'),
        new Currency('British Pound', 'fa-gbp', 'GBP', '£'),
        new Currency('Japanese Yen', 'fa-jpy', 'JPY', '¥'),
        new Currency('Chinese Yuan', 'fa-jpy', 'CNY', '¥'),
    ];
    public main_currency: Currency = this.currencies[0];
    private readonly icon_map: { [asset: string]: string };

    constructor() {
        this.reset();
        this.icon_map = this.get_icon_map();
    }

    public reset() {
        this.user_logged = false;
        this.floating_precision = 2;
        this.historical_data_start = '01/08/2015';
        this.current_location = '';
        this.datetime_format = 'd/m/Y G:i';
        this.has_premium = false;
        this.premium_should_sync = false;
        this.start_suggestion = 'inactive';
        this.eth_rpc_port = '8545';
        this.balance_save_frequency = 24;
        this.last_balance_save = 0;
        this.include_crypto2crypto = true;
        this.include_gas_costs = true;
        this.taxfree_after_period = 0;
        this.anonymized_logs = false;
        this.connected_exchanges = [];
        this.date_display_format = '%d/%m/%Y %H:%M:%S %Z';
    }

    get EXCHANGES(): string[] {
        return this.exchanges;
    }

    get CURRENCIES(): Currency[] {
        return this.currencies;
    }

    get default_currency(): Currency {
        return this.currencies[0];
    }

    public get ICON_MAP_LIST(): { [asset: string]: string } {
        return this.icon_map;
    }

    private get_icon_map(): { [asset: string]: string } {
        const root_dir = path.join(__dirname, '../../');
        const icon_dir = path.join(root_dir, 'node_modules/cryptocurrency-icons/svg/color/');
        const icon_map: { [asset: string]: string } = {};
        fs.readdirSync(icon_dir)
            .forEach(function(v) {
                icon_map[v.substr(0, v.indexOf('.'))] = icon_dir + v;
            });
        return icon_map;
    }
}

export const settings = new Settings();

export function assert_exchange_exists(name: string) {
    if (settings.EXCHANGES.indexOf(name) < 0) {
        throw new Error('Invalid exchange name: ' + name);
    }
}

export function get_value_in_main_currency(usd_value: string): number {
    const symbol = settings.main_currency.ticker_symbol;
    const usd_value_number = parseFloat(usd_value);
    if (symbol === 'USD') {
        return usd_value_number;
    }
    return usd_value_number * settings.usd_to_fiat_exchange_rates[symbol];
}

export function get_fiat_usd_value(currency: string, amount: string): number {
    const amount_number = parseFloat(amount);
    if (currency === 'USD') {
        return amount_number;
    }
    return amount_number / settings.usd_to_fiat_exchange_rates[currency];
}

/**
 * @param usd_value        The usd value to convert to main currency and format
 * @param asset [optional] The name of the asset whose value we want
 * @param amount [optional] If asset was provided then also provide its amount
 */
export function format_currency_value(usd_value: string, asset?: string, amount?: string): string {
    let value;
    // if it's already in main currency don't do any conversion
    if (asset === settings.main_currency.ticker_symbol) {
        if (!amount) {
            throw new Error('amount was supposed to have value but it did not have');
        }
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
    $('#settingssubmit').click(event => {
        event.preventDefault();
        settings.floating_precision = $('#floating_precision').val() as number;
        settings.historical_data_start = $('#historical_data_start').val() as string;
        const main_currency = $('#maincurrencyselector').val();
        for (let i = 0; i < settings.CURRENCIES.length; i++) {
            if (main_currency === settings.CURRENCIES[i].ticker_symbol) {
                settings.main_currency = settings.CURRENCIES[i];
            }
        }

        const anonymized_logs = $('#anonymized_logs_input').is(':checked');
        const eth_rpc_port = $('#eth_rpc_port').val() as number;

        if (eth_rpc_port < 1 || eth_rpc_port > 65535) {
            showError('Invalid port number', 'Please ensure that the specified port number is between 1 and 65535');
            return;
        }

        const balance_save_frequency = $('#balance_save_frequency').val();
        const date_display_format = $('#date_display_format').val();
        const send_payload = {
            'ui_floating_precision': settings.floating_precision,
            'historical_data_start': settings.historical_data_start,
            'main_currency': main_currency,
            'eth_rpc_port': eth_rpc_port,
            'balance_save_frequency': balance_save_frequency,
            'anonymized_logs': anonymized_logs,
            'date_display_format': date_display_format
        };
        // and now send the data to the python process

        service.set_settings(send_payload).then(result => {
            let message = 'Successfully modified settings.';
            if ('message' in result && result.message !== '') {
                message = ` ${message}${result.message}`;
            }
            showInfo('Success', message);
        }).catch((error: Error) => {
            showError('Settings Error', `Error at modifying settings: ${error.message}`);
        });
    });

    $('#historical_data_start').datetimepicker({
        timepicker: false,
        format: 'd/m/Y',
    });
}

export function create_settings_ui() {
    let str = page_header('Settings');
    str += settings_panel('General Settings', 'general_settings');
    $('#page-wrapper').html(str);

    str = form_entry('Floating Precision', 'floating_precision', settings.floating_precision.toString(), '', 'number');
    str += form_checkbox('anonymized_logs_input', 'Should logs by anonymized?', settings.anonymized_logs);
    str += form_entry('Date from when to count historical data', 'historical_data_start', settings.historical_data_start);
    str += form_select(
        'Select Main Currency',
        'maincurrencyselector',
        settings.CURRENCIES.map(x => x.ticker_symbol),
        settings.main_currency.ticker_symbol
    );
    str += form_entry('Eth RPC Port', 'eth_rpc_port', settings.eth_rpc_port, '', 'number');
    str += form_entry(
        'Balance data saving frequency in hours',
        'balance_save_frequency',
        settings.balance_save_frequency.toString(),
        '',
        'number'
    );

    str += form_entry(
        'Date display format',
        'date_display_format',
        settings.date_display_format
    );
    $(str).appendTo($('.panel-body'));

    str = form_button('Save', 'settingssubmit');
    str += '</form></div>';
    $(str).appendTo($('.panel-body'));
}

interface Pages {
    page_index?: string;
    page_settings?: string;
    page_otctrades?: string;
    page_user_settings?: string;
    page_accounting_settings?: string;
    page_taxreport?: string;
    page_exchange: { [name: string]: string };

    [key: string]: string | { [name: string]: string } | undefined;
}

export const pages: Pages = {
    page_exchange: {}
};

export function reset_pages() {
    pages.page_index = '';
    pages.page_settings = '';
    pages.page_otctrades = '';
    pages.page_user_settings = '';
    pages.page_accounting_settings = '';
    pages.page_taxreport = '';
    pages.page_exchange = {};
}
