import {AssetTable} from './asset_table';
import {total_table_modify_balance_for_asset, total_table_modify_all_balances_for_location} from './balances_table';
import {create_task, monitor_add_callback} from './monitor';
import {
    dt_edit_drawcallback,
    format_asset_title_for_ui,
    reload_table_currency_val_if_existing,
    showError,
    showInfo,
    suggest_element_until_click,
    unsuggest_element
} from './utils';
import {
    form_button,
    form_checkbox,
    form_entry,
    form_multiselect,
    form_select,
    invisible_anchor,
    loading_placeholder,
    page_header,
    settings_panel,
    table_html
} from './elements';
import {format_currency_value, get_fiat_usd_value, settings} from './settings';
import {query_exchange_balances_async} from './exchange';
import {PlacementType} from './enums/PlacementType';
import {ActionResult} from './model/action-result';
import {AssetBalance} from './model/asset-balance';

import {BlockchainBalances} from './model/blockchain-balances';
import {NoPremiumCredentials, NoResponseError, service} from './rotkehlchen_service';
import Api = DataTables.Api;

let populate_eth_tokens_called = false;
let FIAT_TABLE: AssetTable;
let FIAT_BALANCES: { [currency: string]: AssetBalance };
let OWNED_TOKENS: string[] = [];
let BB_PER_ASSET_TABLE: AssetTable;
let BB_PER_ACCOUNT_TABLES: { [asset: string]: AssetTable | DataTables.Api } = {};
// The following are the data saved in the front end so that when reloading
// the user settings we don't need to query the back-end again
let BB_ETH_ACCOUNT_DATA: { [account: string]: AssetBalance };
let BB_BTC_ACCOUNT_DATA: { [account: string]: AssetBalance };
let BB_PER_ASSET_DATA: { [asset: string]: AssetBalance };
// awesome idea of template string plus destructuring/mapping taken from:
// https://stackoverflow.com/a/39065147/110395
const ExchangeBadge = ({name, css_class}: { name: string, css_class: string }) => `
<div id="${name}_badge" class="col-sm-6 col-lg-3">
  <div style="margin-top: 5px;" class="row">
    <div class="col-xs-3"><i><img title="${name}" class="${css_class}" src="images/${name}.png" /></i>
    </div>
    <div class="col-xs-offset-1"></div>
    <div style="margin-left:5px;" class="col-xs-2">
      <div style="font-size:28px;">${name}</div>
    </div>
  </div>
</div>
`;

export function reset_user_settings() {
    FIAT_BALANCES = {};
    OWNED_TOKENS = [];
    BB_PER_ACCOUNT_TABLES = {};
    populate_eth_tokens_called = false;
    BB_PER_ASSET_DATA = {};
    BB_ETH_ACCOUNT_DATA = {};
    BB_BTC_ACCOUNT_DATA = {};
}

function show_loading(selector?: string) {
    $('html').addClass('wait');
    if (selector) {
        $(selector).attr('disabled', 'disabled');
    }
}

function stop_show_loading(selector?: string) {
    $('html').removeClass('wait');
    if (selector) {
        $(selector).removeAttr('disabled');
    }
}

function disable_api_entry(selector_text: string, value: string) {
    const element = $(selector_text);
    element.parent().removeClass().addClass('form-group input-group has-success');
    element.attr('disabled', 'true');
    element.val(value);
}

function enable_api_entry(selector_text: string) {
    const element = $(selector_text);
    element.parent().removeClass().addClass('form-group input-group');
    element.removeAttr('disabled');
    element.val('');
}

function enable_key_entries(prefix: string, button_name: string) {
    enable_api_entry(`#${prefix}api_key_entry`);
    enable_api_entry(`#${prefix}api_secret_entry`);
    $(`#setup_${button_name}_button`).html('Setup');
}

function disable_key_entries(prefix: string, button_name: string, val: string) {
    disable_api_entry(`#${prefix}api_key_entry`, `${val} API Key is already registered`);
    disable_api_entry(`#${prefix}api_secret_entry`, `${val} API Secret is already registered`);
    $(`#setup_${button_name}_button`).html('Remove');
}

function setup_premium_callback(event: JQuery.Event) {
    event.preventDefault();
    const button_type = $('#setup_premium_button').html();
    if (button_type === 'Remove') {
        enable_key_entries('premium_', 'premium');
        return;
    }

    // else
    const api_key = $('#premium_api_key_entry').val() as string;
    const api_secret = $('#premium_api_secret_entry').val() as string;

    service.set_premium_credentials(api_key, api_secret)
        .then(() => {
            showInfo('Premium Credentials', 'Successfully set Premium Credentials');
            disable_key_entries('premium_', 'premium', '');
            settings.has_premium = true;
            add_premium_settings();
        }).catch((reason: Error) => {
            if (reason instanceof NoResponseError) {
                showError('Premium Credentials Error', 'Error at adding credentials for premium subscription');
            } else if (reason instanceof NoPremiumCredentials) {
                showError('Premium Credentials Error', reason.message);
            } else {
                showError('Premium Credentials Error', reason.message);
            }
        });
}

function change_premiumsettings_callback(event: JQuery.Event) {
    event.preventDefault();
    const should_sync = $('#premium_sync_entry').is(':checked');
    service.set_premium_option_sync(should_sync).then(() => {
    }).catch(() => {
        showError('Premium Settings Error', 'Error at changing premium settings');
    });
}

function add_premium_settings() {
    if ($('#premium_sync_entry').length) {
        // do not add if they already exist
        return;
    }
    let str = form_checkbox('premium_sync_entry', 'Allow data sync with Rotkehlchen Server', settings.premium_should_sync);
    str += form_button('Change Settings', 'change_premiumsettings_button');
    $(str).insertAfter('#setup_premium_button');
}

function setup_exchange_callback(event: JQuery.Event) {
    event.preventDefault();
    const button_type = $('#setup_exchange_button').html();
    const exchange_name = $('#setup_exchange').val() as string;
    if (button_type === 'Remove') {
        $.confirm({
            title: 'Confirmation Required',
            content: 'Are you sure you want to delete the API key and secret from rotkehlchen? ' +
                'This action is not undoable and you will need to obtain the key and secret again from the exchange.',
            buttons: {
                confirm: function() {
                    service.remove_exchange(exchange_name).then(() => {
                        // Exchange removal from backend successful
                        enable_key_entries('', 'exchange');
                        $(`#${exchange_name}_badge`).remove();
                        const index = settings.connected_exchanges.indexOf(exchange_name);
                        if (index === -1) {
                            throw new Error(`Exchange ${exchange_name} was not in connected_exchanges when trying to remove`);
                        }
                        settings.connected_exchanges.splice(index, 1);
                    }).catch((reason: Error) => {
                        showError('Exchange Removal Error', `Error at removing ${exchange_name} exchange: ${reason.message}`);
                    });
                },
                cancel: function() {
                }
            }
        });
        return;
    }
    // else simply add it
    show_loading('#setup_exchange_button');
    const api_key = $('#api_key_entry').val() as string;
    const api_secret = $('#api_secret_entry').val() as string;
    service.setup_exchange(exchange_name, api_key, api_secret).then(() => {
        // Exchange setup in the backend was successful
        disable_key_entries('', 'exchange', exchange_name);
        settings.connected_exchanges.push(exchange_name);
        const str = ExchangeBadge({name: exchange_name, css_class: 'exchange-icon'});
        $(str).appendTo($('#exchange_badges'));
        stop_show_loading('#setup_exchange_button');
        // also query the balances to have them handy to be shown if needed
        query_exchange_balances_async(exchange_name, false);
    }).catch((reason: Error) => {
        showError('Exchange Setup Error', `Error at setup of ${exchange_name}: ${reason.message}`);
        stop_show_loading('#setup_exchange_button');
    });
}

function fiat_selection_callback(event: JQuery.TriggeredEvent) {
    if (!FIAT_BALANCES) {
        return;
    }

    const value = $(event.target).val() as string;

    if (FIAT_BALANCES.hasOwnProperty(value)) {
        $('#fiat_value_entry').val(FIAT_BALANCES[value]['amount']);
        $('#modify_fiat_button').html('Modify Balance');
    } else {
        $('#fiat_value_entry').val('');
        $('#modify_fiat_button').html('Add Balance');
    }
}

function fiat_modify_callback(event: JQuery.Event) {
    event.preventDefault();
    const currency = $('#fiat_type_entry').val() as string;
    const balance = $('#fiat_value_entry').val() as string;

    service.set_fiat_balance(currency, balance).then(() => {
        if (balance === '') {
            delete FIAT_BALANCES[currency];
        } else {
            FIAT_BALANCES[currency] = {amount: balance, usd_value: get_fiat_usd_value(currency, balance)};
        }

        if (FIAT_TABLE) {
            FIAT_TABLE.update_format(FIAT_BALANCES);
        }
    }).catch((reason: Error) => {
        showError('Balance Modification Error', `Error at modifying ${currency} balance: ${reason.message}`);
    });
}

function add_user_settings_listeners() {
    $('#setup_exchange').change((event) => {
        const value = $(event.target).val() as string;
        if (settings.connected_exchanges.indexOf(value) > -1) {
            disable_key_entries('', 'exchange', value);
        } else {
            enable_key_entries('', 'exchange');
        }
    });
    if (settings.has_premium) {
        disable_key_entries('premium_', 'premium', '');
    }
    $('#setup_premium_button').click(setup_premium_callback);
    $('#change_premiumsettings_button').click(change_premiumsettings_callback);
    $('#setup_exchange_button').click(setup_exchange_callback);
    $('#fiat_type_entry').change(fiat_selection_callback);
    $('#modify_fiat_button').click(fiat_modify_callback);
    $('#add_account_button').click(add_blockchain_account);
    populate_eth_tokens_called = false;
    populate_eth_tokens();
}

function create_user_settings() {
    let str = page_header('User Settings');
    str += settings_panel('Premium Settings', 'premium');
    str += settings_panel('Exchange Settings', 'exchange');
    str += settings_panel('Fiat Balances', 'fiat_balances');
    str += settings_panel('Blockchain Balances', 'blockchain_balances');
    $('#page-wrapper').html(str);

    str = form_entry('Rotkehlchen API Key', 'premium_api_key_entry', '', '');
    str += form_entry('Rotkehlchen API Secret', 'premium_api_secret_entry', '', '');

    str += form_button('Setup', 'setup_premium_button');
    $(str).appendTo($('#premium_panel_body'));
    if (settings.has_premium) {
        add_premium_settings();
    }

    const badge_input = settings.connected_exchanges.map(x => ({name: x, css_class: 'exchange-icon'}));
    str = '<div id="exchange_badges" class="row">';
    str += badge_input.map(ExchangeBadge).join('');
    str += '</div>';

    str += form_select('Setup Exchange', 'setup_exchange', settings.EXCHANGES, '');
    str += form_entry('Api Key', 'api_key_entry', '', '');
    str += form_entry('Api Secret', 'api_secret_entry', '', '');
    str += form_button('Setup', 'setup_exchange_button');

    $(str).appendTo($('#exchange_panel_body'));

    // essentially call the on-select for the first choice
    const first_value = settings.EXCHANGES[0];
    if (settings.connected_exchanges.indexOf(first_value) > -1) {
        disable_key_entries('', 'exchange', first_value);
    }

    const fiat_prompt_option = 'Click to Select Fiat Balance to Modify';
    str = form_select(
        'Modify Balance',
        'fiat_type_entry',
        [fiat_prompt_option].concat(settings.CURRENCIES.map(x => x.ticker_symbol)),
        fiat_prompt_option,
    );
    str += form_entry('Balance', 'fiat_value_entry', '', '');
    str += form_button('Modify', 'modify_fiat_button');

    $(str).appendTo($('#fiat_balances_panel_body'));
    create_fiat_table();

    str += '<h4 class="centered-title">Add New Accounts to track</h4>';
    str = form_select('Choose Blockchain', 'crypto_type_entry', ['ETH', 'BTC'], '');
    str += form_entry('Account', 'account_entry', '', '');
    str += form_button('Add', 'add_account_button');
    str += form_multiselect('Select ETH tokens to track', 'eth_tokens_select', []);
    $(str).appendTo($('#blockchain_balances_panel_body'));

    str = '<h4 class="centered-title">Blockchain Balances Per Asset</h4>';
    str += loading_placeholder('blockchain_per_asset_placeholder');
    str += invisible_anchor('blockchain_per_asset_anchor');
    str += '<h4 class="centered-title">Blockchain Balances Per Account</h4>';
    str += loading_placeholder('blockchain_per_account_placeholder');
    str += invisible_anchor('ethchain_per_account_anchor');
    str += invisible_anchor('btcchain_per_account_anchor');
    $(str).appendTo($('#blockchain_balances_panel_body'));

    // If this is the first time user settings are loaded, query blockchain balances
    if (!BB_PER_ASSET_TABLE) {
        service.query_blockchain_balances_async().then(value => {
            create_task(value.task_id, 'user_settings_query_blockchain_balances', 'Query blockchain balances', false, true);
        }).catch((reason: Error) => {
            console.log(`Error at querying blockchain balances async: ${reason.message}`);
        });
    } else {
        // reloading user settings page from the saved data
        $('#blockchain_per_asset_placeholder').remove();
        $('#blockchain_per_account_placeholder').remove();
        if (BB_PER_ASSET_TABLE) {
            BB_PER_ASSET_TABLE.repopulate(BB_PER_ASSET_DATA);
            BB_PER_ASSET_TABLE.reload();
        }

        if (BB_PER_ACCOUNT_TABLES['ETH']) {
            recreate_ethchain_per_account_table(BB_ETH_ACCOUNT_DATA);
        }

        const btc_table = BB_PER_ACCOUNT_TABLES['BTC'] as AssetTable;
        if (btc_table) {
            btc_table.repopulate(BB_BTC_ACCOUNT_DATA);
            btc_table.reload();
        }
    }

    // pulsate element if first time we open and user follows guide
    if (settings.start_suggestion === 'click_user_settings') {
        unsuggest_element('#user_settings_button');
        suggest_element_until_click('#fiat_value_entry', 'inactive');
        suggest_element_until_click('#api_key_entry', 'inactive');
        suggest_element_until_click('#api_secret_entry', 'inactive');
        suggest_element_until_click('#account_entry', 'inactive');

        // also show some first time info
        showInfo(
            'Add your settings',
            'Here you can add exchange api keys and pull data from exchanges, add blockchain accounts, or keep track of your fiat balances'
        );
    }
}

export function create_or_reload_usersettings() {
    create_user_settings();
    add_user_settings_listeners();
}

function add_blockchain_account(event: JQuery.Event) {
    event.preventDefault();
    const blockchain = $('#crypto_type_entry').val() as string;
    const account = $('#account_entry').val() as string;
    show_loading('#account_entry');

    service.add_blockchain_account(blockchain, account).then(result => {
        if (blockchain === 'ETH') {
            // save the data from the call
            BB_ETH_ACCOUNT_DATA = result.per_account['ETH'];
            // update the table with the data
            recreate_ethchain_per_account_table(BB_ETH_ACCOUNT_DATA);
            // also update the data of the dashboard's totals table
            total_table_modify_all_balances_for_location('blockchain', result.totals);
        } else if (blockchain === 'BTC') {
            const btcTable = BB_PER_ACCOUNT_TABLES['BTC'] as AssetTable;
            // save the data from the call
            BB_BTC_ACCOUNT_DATA = result.per_account['BTC'];
            // update the table with the data
            if (!btcTable) {
                create_btcchain_per_account_table(BB_BTC_ACCOUNT_DATA);
            } else {
                btcTable.update_format(BB_BTC_ACCOUNT_DATA);
            }
            // also update the data of the dashboard's totals table
            total_table_modify_balance_for_asset('blockchain', 'BTC', result.totals['BTC']);
        }
        if (BB_PER_ASSET_TABLE == null) {
            throw new Error('Table was not supposed to be null');
        }
        // also reload the asset total tables by saving its data
        BB_PER_ASSET_DATA = result['totals'];
        // and then updating the table with it
        BB_PER_ASSET_TABLE.update_format(BB_PER_ASSET_DATA);

        stop_show_loading('#account_entry');
    }).catch((reason: Error) => {
        showError(
            'Account Error',
            `Error at adding new ${blockchain} account: ${reason.message}`
        );
        stop_show_loading('#account_entry');
    });
}

const table_data_shortener = function(cutoff_start: number, keep_length: number) {
    const esc = function(t: string) {
        return t
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    };

    return function(d: number | string, type: string) {
        // Order, search and type get the original data
        if (type !== 'display') {
            return d;
        }

        if (typeof d !== 'number' && typeof d !== 'string') {
            return d;
        }

        d = d.toString(); // cast numbers

        if (d.length < cutoff_start + keep_length) {
            return d;
        }

        const shortened = d.substr(cutoff_start, cutoff_start + keep_length - 1);
        return `<span class="ellipsis" title="${esc(d)}">${shortened}&#8230;</span>`;
    };
};

interface EthChainRowData {
    readonly account: string;
    readonly ETH: string;
    readonly total_usd_value: string;

    [key: string]: string | number;
}

function format_ethchain_per_account_data(eth_accounts: { [account: string]: AssetBalance }) {
    const data: EthChainRowData[] = [];
    for (const account in eth_accounts) {
        if (!eth_accounts.hasOwnProperty(account)) {
            continue;
        }

        const account_data = eth_accounts[account];
        const eth_amount = parseFloat(account_data['ETH'] as string);
        const eth_amount_str = eth_amount.toFixed(settings.floating_precision);
        const total_usd_value = parseFloat(account_data['usd_value'] as string);
        const total_usd_value_str = total_usd_value.toFixed(settings.floating_precision);
        const row: EthChainRowData = {'account': account, 'ETH': eth_amount_str, 'total_usd_value': total_usd_value_str};
        for (let i = 0; i < OWNED_TOKENS.length; i++) {
            if (!account_data[OWNED_TOKENS[i]]) {
                row[OWNED_TOKENS[i]] = 0;
                continue;
            }
            const token_amount = parseFloat(account_data[OWNED_TOKENS[i]] as string);
            row[OWNED_TOKENS[i]] = token_amount.toFixed(settings.floating_precision);
        }
        data.push(row);
    }
    const column_data: {
        data: string,
        title: string,
        render?: any
    }[] = [
            {'data': 'account', 'title': 'Account'},
            {'data': 'ETH', 'title': format_asset_title_for_ui('ETH')}
        ];
    // if user has a lot of ETH tokens shorten the table by shortening the display of accounts
    if (OWNED_TOKENS.length > 4) {
        column_data[0]['render'] = table_data_shortener(2, 6);
    }
    for (let i = 0; i < OWNED_TOKENS.length; i++) {
        column_data.push({'data': OWNED_TOKENS[i], 'title': format_asset_title_for_ui(OWNED_TOKENS[i])});
    }

    column_data.push({
        'data': 'total_usd_value',
        'title': `Total ${settings.main_currency.ticker_symbol} Value`,
        'render': (usd_value: string) => format_currency_value(usd_value)
    });

    return [data, column_data];
}

function recreate_ethchain_per_account_table(eth_accounts: { [account: string]: AssetBalance }) {
    $('#ethchain_per_account_header').remove();
    // to add a column we have to recreate the table
    const ethTable: DataTables.Api = BB_PER_ACCOUNT_TABLES['ETH'] as Api;
    if (ethTable) {
        ethTable.destroy(true);
    }
    $('ethchain_per_account_table').empty();
    create_ethchain_per_account_table(eth_accounts);
}

function delete_blockchain_account_row(blockchain: string, row: DataTables.RowMethods) {
    const data: EthChainRowData = row.data() as EthChainRowData;
    const account = data['account'];
    show_loading();
    service.remove_blockchain_account(blockchain, account).then(value => {
        // @ts-ignore
        row.remove().draw();
        // save the returned data
        BB_PER_ASSET_DATA = value.totals;
        // and update the table with it
        BB_PER_ASSET_TABLE.update_format(BB_PER_ASSET_DATA);
        // and finally also update the dashboard table
        total_table_modify_all_balances_for_location('blockchain', value.totals);
        stop_show_loading();
    }).catch((reason: Error) => {
        showError('Account Deletion Error', `Error at deleting ${blockchain} account ${account}: ${reason.message}`);
        stop_show_loading();
    });
}

function delete_btc_account_row(row: DataTables.RowMethods) {
    return delete_blockchain_account_row('BTC', row);
}

function delete_eth_account_row(row: DataTables.RowMethods) {
    return delete_blockchain_account_row('ETH', row);
}

function create_ethchain_per_account_table(eth_accounts: { [account: string]: AssetBalance }) {
    let str = '<h3 id="ethchain_per_account_header">ETH accounts</h3>';
    // columns are: one for each token amount, one for ETH, one for account, one for total usd value
    str += table_html(OWNED_TOKENS.length + 3, 'ethchain_per_account');
    $(str).insertAfter('#ethchain_per_account_anchor');
    const [data, column_data] = format_ethchain_per_account_data(eth_accounts);
    // now we have the data so create the table
    // @ts-ignore
    BB_PER_ACCOUNT_TABLES['ETH'] = $('#ethchain_per_account_table').DataTable({
        'data': data,
        'columns': column_data,
        'order': [[column_data.length - 1, 'desc']],
        drawCallback: dt_edit_drawcallback('ethchain_per_account_table', null, delete_eth_account_row)
    });
}

function create_btcchain_per_account_table(btc_accounts: { [asset: string]: AssetBalance }) {
    BB_PER_ACCOUNT_TABLES['BTC'] = new AssetTable(
        'account',
        'btcchain_per_account',
        PlacementType.insertAfter,
        'btcchain_per_account_anchor',
        btc_accounts,
        'BTC Accounts',
        'btcchain_per_account_header',
        dt_edit_drawcallback('btcchain_per_account_table', null, delete_btc_account_row)
    );
}

function create_blockchain_balances_tables(result: BlockchainBalances) {

    $('#blockchain_per_asset_placeholder').remove();
    // save the data
    BB_PER_ASSET_DATA = result.totals;
    // create the table with it
    BB_PER_ASSET_TABLE = new AssetTable(
        'asset',
        'blockchain_per_asset',
        PlacementType.insertAfter,
        'blockchain_per_asset_anchor',
        result.totals
    );

    // now the per accounts tables
    $('#blockchain_per_account_placeholder').remove();
    // save the data
    BB_ETH_ACCOUNT_DATA = result['per_account']['ETH'];
    // create the table with it
    if (BB_ETH_ACCOUNT_DATA) {
        create_ethchain_per_account_table(BB_ETH_ACCOUNT_DATA);
    }

    // save the data
    BB_BTC_ACCOUNT_DATA = result['per_account']['BTC'];
    // create the table with it
    if (BB_BTC_ACCOUNT_DATA) {
        create_btcchain_per_account_table(BB_BTC_ACCOUNT_DATA);
    }

    // the multiselect must have been disabled from populate_eth_tokens()
    // and now that the blockchain balances table has been created we re-enable it
    enable_multiselect();
}

function populate_eth_tokens() {
    service.get_eth_tokens().then(result => {
        $('#eth_tokens_select').multiSelect({
            selectableHeader: '<div class=\'custom-header\'>All ETH Tokens</div>',
            selectionHeader: '<div class=\'custom-header\'>My ETH Tokens</div>',
            afterSelect: (values: string[]) => {
                // TODO: Super ugly pattern. Any way to do this better and set the
                // afterSelect callback after populating the initial selections?
                if (!populate_eth_tokens_called) {
                    return;
                }
                add_new_eth_tokens(values);

            },
            afterDeselect: (values: string[]) => remove_eth_tokens(values),
            afterInit: () => {
                // TODO: Also super ugly hack. I think that perhaps this multiselect is kind of flawed due to
                // the afterInit firing after a `refresh` and also requiring a refresh in order to display
                // the disabled state of the widget.
                if (populate_eth_tokens_called) {
                    return;
                }
                const all_tokens = result.all_eth_tokens;
                OWNED_TOKENS = result.owned_eth_tokens;
                for (let i = 0; i < all_tokens.length; i++) {
                    const symbol = all_tokens[i].symbol;
                    $('#eth_tokens_select').multiSelect('addOption', {value: symbol, text: symbol});

                }
                $('#eth_tokens_select').multiSelect('select', OWNED_TOKENS);
                // has to come after the setting of the selections
                populate_eth_tokens_called = true;

                if (!BB_PER_ASSET_TABLE) {
                    // even though the multiselect is created, disable it until
                    // the blockchain balances table is first loaded so that any
                    // changes to the multiselect are reflected in the table.
                    disable_multiselect();
                }
            }
        });
    }).catch((reason: Error) => {
        console.log('Error at getting ETH tokens:' + reason.message);
    });

}

function disable_multiselect() {
    const $ethTokensSelect = $('#eth_tokens_select');
    $ethTokensSelect.attr('disabled', 'disabled');
    $ethTokensSelect.multiSelect('refresh');
}

function enable_multiselect() {
    const $ethTokensSelect = $('#eth_tokens_select');
    $ethTokensSelect.removeAttr('disabled');
    $ethTokensSelect.multiSelect('refresh');
}


function add_new_eth_tokens(tokens: string[]) {
    // disable selection until the entire call is done
    disable_multiselect();
    show_loading('#eth_tokens_select');
    service.add_owned_eth_tokens(tokens).then(result => {
        for (let i = 0; i < tokens.length; i++) {
            OWNED_TOKENS.push(tokens[i]);
        }

        // save the data
        BB_ETH_ACCOUNT_DATA = result['per_account']['ETH'];
        // update the table with it
        recreate_ethchain_per_account_table(BB_ETH_ACCOUNT_DATA);
        // also reload the asset total tables by saving the data
        BB_PER_ASSET_DATA = result['totals'];
        // and updating the table with it
        BB_PER_ASSET_TABLE.update_format(BB_PER_ASSET_DATA);
        enable_multiselect();
        stop_show_loading('#eth_tokens_select');
    }).catch(reason => {
        showError('Token Addition Error', reason.message);
        stop_show_loading('#eth_tokens_select');
    });
}

function remove_eth_tokens(tokens: string[]) {
    // disable selection until the entire call is done
    disable_multiselect();
    show_loading('#eth_tokens_select');
    service.remove_owned_eth_tokens(tokens).then(result => {
        for (let i = 0; i < tokens.length; i++) {
            const index = OWNED_TOKENS.indexOf(tokens[i]);
            if (index === -1) {
                throw new Error(`Token ${tokens[i]} could not be found from the javascript side. Unexpected error.`);
            }
            OWNED_TOKENS.splice(index, 1);
        }

        // save the data
        BB_ETH_ACCOUNT_DATA = result['per_account']['ETH'];
        // update the table with it
        recreate_ethchain_per_account_table(BB_ETH_ACCOUNT_DATA);
        // also reload the asset total tables by saving the data
        BB_PER_ASSET_DATA = result.totals;
        // and updating the table with it
        BB_PER_ASSET_TABLE.update_format(BB_PER_ASSET_DATA);
        enable_multiselect();
        stop_show_loading('#eth_tokens_select');
    }).catch(reason => {
        showError('Token Removal Error', (reason as Error).message);
        stop_show_loading('#eth_tokens_select');
    });
}

function create_fiat_table() {
    service.query_fiat_balances().then(value => {
        FIAT_BALANCES = value;
        const str = '<h4 class="centered-title">Owned Fiat Currency Balances</h4>';
        $(str).appendTo($('#fiat_balances_panel_body'));
        FIAT_TABLE = new AssetTable('currency', 'fiat_balances', PlacementType.appendTo, 'fiat_balances_panel_body', value);
    }).catch(reason => {
        console.log(`Error at querying fiat balances: ${reason}`);
    });
}

export function reload_user_settings_tables_if_existing() {
    if (FIAT_TABLE) {
        FIAT_TABLE.reload();
    }
    if (BB_PER_ASSET_TABLE) {
        BB_PER_ASSET_TABLE.reload();
    }
    for (const currency in BB_PER_ACCOUNT_TABLES) {
        if (!BB_PER_ACCOUNT_TABLES.hasOwnProperty(currency)) {
            continue;
        }

        const table = BB_PER_ACCOUNT_TABLES[currency];

        if (table instanceof AssetTable) {
            table.reload();
        } else {
            reload_table_currency_val_if_existing(table as DataTables.Api, 2);
        }
    }
}

export function init_user_settings() {
    monitor_add_callback('user_settings_query_blockchain_balances', (result: ActionResult<BlockchainBalances>) => {
        let msg = 'Querying blockchain balances for user settings failed';
        if (result == null || result.message !== '') {
            if (result.message !== '') {
                msg = result.message;
            }
            showError('Querying Blockchain Balances Error', msg);
            return;
        }
        create_blockchain_balances_tables(result.result);
    });
}
