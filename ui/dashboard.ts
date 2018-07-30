import { assert_exchange_exists, Currency, format_currency_value, settings } from './settings';
import { create_or_reload_exchange } from './exchange';
import { change_location, determine_location } from './navigation';
import client from './zerorpc_client';
import { get_total_asssets_value, iterate_saved_balances, setup_log_watcher, showError, setup_client_auditor } from './utils';
import { set_ui_main_currency } from './topmenu';
import { prompt_sign_in } from './userunlock';
import { total_table_add_balances, total_table_recreate } from './balances_table';
import { monitor_add_callback } from './monitor';

function add_exchange_on_click() {
    $('.panel a').click(function(event: any) {
        event.preventDefault();
        let target_location = determine_location(this.getAttribute('href'));
        if (target_location.startsWith('exchange_')) {
            let exchange_name = target_location.substring(9);
            assert_exchange_exists(exchange_name);
            console.log('Going to exchange ' + exchange_name);
            create_or_reload_exchange(exchange_name);
        } else {
            throw new Error('Invalid link location ' + target_location);
        }
    });
}


function create_dashboard_header() {
    let str = '<div class="row"><div class="col-lg-12"><h1 class="page-header">Dashboard</h1></div></div><div class="row"><div id="dashboard-contents" class="col-lg-12"></div></div>';
    $(str).appendTo($('#page-wrapper'));
}

function create_exchange_box(exchange: string, number: string | number, currency_icon: string) {
    let current_location = settings.current_location;
    if (current_location !== 'index') {
        return;
    }

    if ($('#' + exchange + 'box').length !== 0) {
        // already exists
        return;
    }

    let css_class = 'exchange-icon-inverted';
    if (['poloniex', 'binance'].indexOf(exchange) > -1) {
        css_class = 'exchange-icon';
    }
    number = format_currency_value(number);
    let str = '<div class="panel panel-primary"><div class="panel-heading" id="' + exchange + '_box"><div class="row"><div class="col-xs-3"><i><img title="' + exchange + '" class="' + css_class + '" src="images/' + exchange + '.png"  /></i></div><div class="col-xs-9 text-right"><div class="huge">' + number + '</div><div id="status_box_text"><i id="currencyicon" class="fa ' + currency_icon + ' fa-fw"></i></div></div></div></div><a href="#exchange_' + exchange + '"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span><div class="clearfix"></div></div></a></div>';
    $(str).prependTo($('#dashboard-contents'));
    add_exchange_on_click();
    // finally save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}

export function create_box (id: string, icon: string, number: string | number, currency_icon: string) {
    let current_location = settings.current_location;
    if (current_location !== 'index') {
        return;
    }
    if ($('#' + id).length !== 0) {
        // already exists
        return;
    }
    number = format_currency_value(number);
    let str = '<div class="panel panel-primary"><div class="panel-heading" id="' + id + '"><div class="row"><div class="col-xs-3"><i title="' + id + '" class="fa ' + icon + '  fa-5x"></i></div><div class="col-xs-9 text-right"><div class="huge">' + number + '</div><div id="status_box_text"><i id="currencyicon" class="fa ' + currency_icon + ' fa-fw"></i></div></div></div></div>';
    if (id === 'foo') {
        str += '<a href="#"><div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i class="fa fa-arrow-circle-right"></i></span>';
        str += '<div class="clearfix"></div></div></a></div>';

    } else {
        str += '<div class="panel-footer">';
        str += '<div class="clearfix"></div></div></div>';
    }

    $(str).prependTo($('#dashboard-contents'));
    // also save the dashboard page
    settings.page_index = $('#page-wrapper').html();
}



let alert_id = 0;
function add_alert_dropdown(alert_text: string) {
    let str = '<li class="warning' + alert_id + '"><a href="#"><div><p>' + alert_text + '<span class="pull-right text-muted"><i class="fa fa-times warningremover' + alert_id + '"></i></span></p></div></a></li><li class="divider warning' + alert_id + '"></li>';
    $(str).appendTo($('.dropdown-alerts'));
    let current_alert_id = alert_id;
    $('.warningremover' + current_alert_id).click(function() {console.log('remove callback called for ' + current_alert_id); $('.warning' + current_alert_id).remove(); });
    alert_id += 1;
}

export function add_currency_dropdown(currency: Currency) {
    let str = '<li><a id="change-to-' + currency.ticker_symbol.toLowerCase() + '" href="#"><div><i class="fa ' + currency.icon + ' fa-fw"></i> Set ' + currency.name + ' as the main currency</div></a></li><li class="divider"></li>';
    $(str).appendTo($('.currency-dropdown'));

    $('#change-to-' + currency.ticker_symbol.toLowerCase()).bind('click', function() {
        if (currency.ticker_symbol === settings.main_currency.ticker_symbol) {
            // nothing to do
            return;
        }
        client.invoke('set_main_currency', currency.ticker_symbol, (error, res) => {
            if (error) {
                showError('Error', 'Error at setting main currency: ' + error);
            } else {
                set_ui_main_currency(currency.ticker_symbol);
            }
        });
    });
}

export function create_or_reload_dashboard() {
    change_location('index');
    if (!settings.page_index) {
        $('body').addClass('loading');
        console.log('At create/reload, with a null page index');
        $('body').removeClass('loading');
        prompt_sign_in();
    } else {
        console.log('At create/reload, with a Populated page index');
        $('#page-wrapper').html('');
        create_dashboard_header();
        create_dashboard_from_saved_balances();
        total_table_recreate();
        add_exchange_on_click();
    }
}


function create_dashboard_from_saved_balances() {
    // must only be called if we are at index
    for (let result of iterate_saved_balances()) {
        let location = result[0];
        let total = result[1];
        let icon = result[2];
        if (settings.EXCHANGES.indexOf(location) >= 0) {
            create_exchange_box(
                location,
                total,
                settings.main_currency.icon
            );
        } else {
            create_box(
                location,
                icon,
                total,
                settings.main_currency.icon
            );
        }
    }
}

const ipc = require('electron').ipcRenderer;
const remote = require('electron').remote;
ipc.on('failed', (event, message) => {
    // get notified if the python subprocess dies
    showError(
        'Startup Error',
        'The Python backend crushed. Check rotkehlchen.log or open an issue in Github.',
        function () {remote.getCurrentWindow().close(); }
    );
    // send ack to main.js
    ipc.send('ack', 1);
});


export function init_dashboard() {
    // add callbacks for dashboard to the monitor
    monitor_add_callback('query_exchange_balances', function (result: any) {
        if ('error' in result) {
            showError(
                'Exchange Query Error',
                'Querying ' + result['name'] + ' died because of: ' + result['error'] + '. ' +
                    'Check the logs for more details.'
            );
            return;
        }
        let total = get_total_asssets_value(result['balances']);
        create_exchange_box(
            result['name'],
            total,
            settings.main_currency.icon
        );
        total_table_add_balances(result['name'], result['balances']);
    });
    monitor_add_callback('query_blockchain_balances', function (result: any) {
        if (result['message'] !== '') {
            showError(
                'Blockchain Query Error',
                'Querying blockchain balances died because of: ' + result['message'] + '. ' +
                    'Check the logs for more details.'
            );
            return;
        }
        result = result['result'];
        let total = get_total_asssets_value(result['totals']);
        if (total !== 0.0) {
            create_box(
                'blockchain_box',
                'fa-hdd-o',
                total,
                settings.main_currency.icon
            );
            total_table_add_balances('blockchain', result['totals']);
        }
    });
    setup_log_watcher(add_alert_dropdown);
    setup_client_auditor();
}



