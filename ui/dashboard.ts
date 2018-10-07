import {change_location} from './navigation';
import {set_ui_main_currency} from './topmenu';
import {get_total_assets_value, iterate_saved_balances, total_table_add_balances, total_table_recreate} from './balances_table';
import {assert_exchange_exists, format_currency_value, pages, settings} from './settings';
import {setup_client_auditor, setup_log_watcher, showError} from './utils';
import {create_or_reload_exchange} from './exchange';
import {monitor_add_callback} from './monitor';
import {prompt_sign_in} from './userunlock';
import {ActionResult} from './model/action-result';
import {ExchangeBalanceResult} from './model/exchange-balance-result';
import {BlockchainBalances} from './model/blockchain-balances';
import {ipcRenderer, remote} from 'electron';
import {service} from './rotkehlchen_service';
import {Currency} from './model/currency';

function add_exchange_on_click(name: string) {
    const selector = $(`a#exchange_${name}_details`);
    selector.click((event: JQuery.Event) => {
        event.preventDefault();
        assert_exchange_exists(name);
        console.log(`Going to exchange ${name}`);
        create_or_reload_exchange(name);
    });
}


function create_dashboard_header() {
    const str = `<div class="row">
    <div class="col-lg-12"><h1 class="page-header">Dashboard</h1></div>
</div>
<div class="row">
    <div id="dashboard-contents" class="col-lg-12"></div>
</div>`;
    $(str).appendTo($('#page-wrapper'));
}

export function create_exchange_box(exchange: string, number: any, currency_icon: string) {
    const current_location = settings.current_location;
    if (current_location !== 'index') {
        return;
    }

    if ($(`#${exchange}box`).length !== 0) {
        // already exists
        return;
    }

    let css_class = 'exchange-icon-inverted';
    if (['poloniex', 'binance', 'bitmex'].indexOf(exchange) > -1) {
        css_class = 'exchange-icon';
    }
    number = format_currency_value(number);
    const str = `<div class="panel panel-primary">
    <div class="panel-heading" id="${exchange}_box">
        <div class="row">
            <div class="col-xs-3"><i><img title="${exchange}" class="${css_class}"
                                          src="images/${exchange}.png"/></i></div>
            <div class="col-xs-9 text-right">
                <div class="huge">${number}</div>
                <div id="status_box_text"><i id="currencyicon" class="fa ${currency_icon} fa-fw"></i></div>
            </div>
        </div>
    </div>
    <a id="exchange_${exchange}_details" href="#exchange_${exchange}">
        <div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i
                class="fa fa-arrow-circle-right"></i></span>
            <div class="clearfix"></div>
        </div>
    </a></div>`;
    $(str).prependTo($('#dashboard-contents'));
    add_exchange_on_click(exchange);
    // finally save the dashboard page
    pages.page_index = $('#page-wrapper').html();
}

export function create_box(id: string, icon: string, number: number, currency_icon: string) {
    const current_location = settings.current_location;
    if (current_location !== 'index') {
        return;
    }
    if ($(`#${id}`).length !== 0) {
        // already exists
        return;
    }
    const formattedValue = format_currency_value(number.toString());
    let str = `<div class="panel panel-primary">
    <div class="panel-heading" id="${id}">
        <div class="row">
            <div class="col-xs-3"><i title="${id}" class="fa ${icon}  fa-5x"></i></div>
            <div class="col-xs-9 text-right">
                <div class="huge">${formattedValue}</div>
                <div id="status_box_text"><i id="currencyicon" class="fa ${currency_icon} fa-fw"></i></div>
            </div>
        </div>
    </div>`;
    if (id === 'foo') {
        str += `<a href="#">
    <div class="panel-footer"><span class="pull-left">View Details</span><span class="pull-right"><i
            class="fa fa-arrow-circle-right"></i></span>`;
        str += '<div class="clearfix"></div></div></a></div>';

    } else {
        str += '<div class="panel-footer">';
        str += '<div class="clearfix"></div></div></div>';
    }

    $(str).prependTo($('#dashboard-contents'));
    // also save the dashboard page
    pages.page_index = $('#page-wrapper').html();
}

const nodeConnectionStatus = ({iconClass, message}: { iconClass: string, message: string }) => `
<a class="eth-node-status-link" href="#">
    <i class="fa ${iconClass} fa-fw"></i>
</a>
<ul class="dropdown-menu dropdown-eth-status">
    <p>${message}</p>
</ul>
`;

function update_eth_node_connection_status_ui(is_local_eth: boolean) {
    let str: string;
    if (!is_local_eth) {
        str = nodeConnectionStatus({
            iconClass: 'fa-unlink',
            message: 'Not connected to a local ethereum node'
        });
    } else {
        str = nodeConnectionStatus({
            iconClass: 'fa-link',
            message: 'Connected to a local ethereum node'
        });
    }
    $('.eth-node-status').html(str);
}

let alert_id = 0;

function add_alert_dropdown(alert_text: string, _alert_time: number) {
    const connection_fail = alert_text.indexOf('Could not connect to a local ethereum node') >= 0;
    const no_sync = alert_text.indexOf('Could not transact with/call contract function') >= 0;
    if (connection_fail || no_sync) {
        update_eth_node_connection_status_ui(false);
    } else {
        update_eth_node_connection_status_ui(true);
    }
    const str = `<li class="warning${alert_id}">
    <a href="#">
        <div>
            <p>${alert_text}
                <span class="pull-right text-muted"><i class="fa fa-times warningremover${alert_id}"></i></span>
            </p>
        </div>
    </a>
    </li>
    <li class="divider warning${alert_id}"></li>`;
    $(str).appendTo($('.dropdown-alerts'));
    const current_alert_id = alert_id;
    $(`.warningremover${current_alert_id}`).click(() => {
        console.log(`remove callback called for ${current_alert_id}`);
        $(`.warning${current_alert_id}`).remove();
    });
    alert_id += 1;
}

export function add_currency_dropdown(currency: Currency) {
    const str = `<li><a id="change-to-${currency.ticker_symbol.toLowerCase()}" href="#">
    <div><i class="fa ${currency.icon} fa-fw"></i> Set ${currency.name} as the main currency</div>
</a></li>
<li class="divider"></li>`;
    $(str).appendTo($('.currency-dropdown'));

    $(`#change-to-${currency.ticker_symbol.toLowerCase()}`).bind('click', () => {
        if (currency.ticker_symbol === settings.main_currency.ticker_symbol) {
            // nothing to do
            return;
        }

        service.set_main_currency(currency).then(value => {
            set_ui_main_currency(value.ticker_symbol);
        }).catch((reason: Error) => {
            showError('Error', `Error at setting main currency: ${reason.message}`);
        });
    });
}

export function create_or_reload_dashboard() {
    change_location('index');
    if (!pages.page_index) {
        const body = $('body');
        body.addClass('loading');
        console.log('At create/reload, with a null page index');
        body.removeClass('loading');
        prompt_sign_in();
    } else {
        console.log('At create/reload, with a Populated page index');
        $('#page-wrapper').html('');
        create_dashboard_header();
        create_dashboard_from_saved_balances();
        total_table_recreate();
    }
}


function create_dashboard_from_saved_balances() {
    // must only be called if we are at index
    for (const result of iterate_saved_balances()) {
        const location = result[0] as string;
        const total = result[1] as number;
        const icon = result[2] as string;
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

ipcRenderer.on('failed', () => {
    // get notified if the python subprocess dies
    showError(
        'Startup Error',
        'The Python backend crushed. Check rotkehlchen.log or open an issue in Github.',
        function () {
            remote.getCurrentWindow().close();
        }
    );
    // send ack to main.js
    ipcRenderer.send('ack', 1);
});

export function init_dashboard() {
    // add callbacks for dashboard to the monitor
    monitor_add_callback('query_exchange_balances_async', (result: ExchangeBalanceResult) => {
        if (result.error) {
            showError(
                'Exchange Query Error',
                `Querying ${result.name} died because of: ${result.error}. Check the logs for more details.`
            );
            return;
        }
        const balances = result.balances;
        if (!balances) {
            throw Error('Expected balances to have a value');
        }
        const total = get_total_assets_value(balances);
        create_exchange_box(
            result.name,
            total,
            settings.main_currency.icon
        );
        total_table_add_balances(result.name, balances);
    });
    monitor_add_callback('query_blockchain_balances_async', (result: ActionResult<BlockchainBalances>) => {
        if (result.message !== '') {
            showError(
                'Blockchain Query Error',
                `Querying blockchain balances died because of: ${result.message}. Check the logs for more details.`
            );
            return;
        }
        const data = result.result;
        const total = get_total_assets_value(data.totals);
        if (total !== 0.0) {
            create_box(
                'blockchain_box',
                'fa-hdd-o',
                total,
                settings.main_currency.icon
            );
            total_table_add_balances('blockchain', data.totals);
        }
    });
    setup_log_watcher(add_alert_dropdown);
    setup_client_auditor();
}
