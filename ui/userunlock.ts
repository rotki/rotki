import {form_entry} from './elements';
import {setup_client_auditor, showError, showInfo, suggest_element, unsuggest_element} from './utils';
import {set_ui_main_currency} from './topmenu';
import {get_total_assets_value, total_table_add_balances} from './balances_table';
import {create_box, create_or_reload_dashboard} from './dashboard';
import {create_task} from './monitor';
import {query_exchange_balances_async} from './exchange';
import {settings} from './settings';
import {UnlockResult} from './model/action-result';
import {service} from './rotkehlchen_service';

function verify_userpass(username: string, password: string) {
    if (!username) {
        $.alert('Please provide a user name');
        return false;
    }
    if (!/^[0-9a-zA-Z_.-]+$/.test(username)) {
        $.alert('A username must contain only alphanumeric characters and have no spaces');
        return false;
    }
    if (!password) {
        $.alert('Please provide a password');
        return false;
    }
    return true;
}

function ask_permission(msg: string, username: string, password: string, create_true: boolean, api_key: string, api_secret: string) {
    $.confirm({
        title: 'Sync Permission Required',
        content: msg,
        buttons: {
            yes: {
                text: 'Yes',
                btnClass: 'btn-blue',
                action: function() {
                    unlock_async(username, password, create_true, 'yes', api_key, api_secret);
                }
            },
            no: {
                text: 'No',
                btnClass: 'btn-red',
                action: function() {
                    unlock_async(username, password, create_true, 'no', api_key, api_secret);
                }
            }
        }
    });
}

/**
 * Registers a handler for pressing Enter Key on form entry buttons
 *
 * @param content JquerySelectorResult A JQuery selector with the content of the form
 * @param id string                    The id of the form entry field at which pressing enter should work
 * @param button_text string           The text of the form submit button to activate
*/
function register_enter_keypress(content: JQuery.PlainObject, id: string, button_text: string) {
    $(`#${id}`).on('keypress', function(e: JQuery.Event) {
        // if the user submits the form by pressing enter in the last field.
        if (e.keyCode === 13 || e.which === 13) {
            e.preventDefault();
            content.find(`button:contains("${button_text}")`).trigger('click'); // reference the button and click it
        }
    });
}

function prompt_new_account() {
    let content_str = '';
    content_str += form_entry('User Name', 'user_name_entry', '', 'A name for your user -- only used locally');
    content_str += form_entry('Password', 'password_entry', '', 'Password to encrypt your data with', 'password');
    content_str += form_entry('Repeat Password', 'repeat_password_entry', '', 'Repeat Password', 'password');
    content_str += form_entry('API KEY', 'api_key_entry', '', 'Optional: Only for premium users', '');
    content_str += form_entry('API SECRET', 'api_secret_entry', '', 'Optional: Only for premium users', '');
    $.confirm({
        title: 'Create New Account',
        content: content_str,
        buttons: {
            formSubmit: {
                text: 'Create',
                btnClass: 'btn-blue',
                action: () => {
                    const $content = $(document);
                    const username = $content.find('#user_name_entry').val() as string;
                    const password = $content.find('#password_entry').val() as string;
                    const password2 = $content.find('#repeat_password_entry').val() as string;
                    const api_key = $content.find('#api_key_entry').val() as string;
                    const api_secret = $content.find('#api_secret_entry').val() as string;
                    if (!verify_userpass(username, password)) {
                        return false;
                    }

                    if (password !== password2) {
                        $.alert('The given passwords don\'t match');
                        return false;
                    }
                    unlock_user(username, password, true, 'unknown', api_key, api_secret);
                    return true;
                }
            },
            cancel: function() {
                prompt_sign_in();
            }
        },
        onContentReady: function() {
            const $content = $(document);
            $content.find('form').on('submit', (e: JQuery.Event) => {
                // if the user submits the form by pressing enter in the field.
                e.preventDefault();
                $(e.target).trigger('click'); // reference the button and click it
            });
            register_enter_keypress($content, 'repeat_password_entry', 'Create');
            register_enter_keypress($content, 'api_secret_entry', 'Create');
        }
    });
}

export function prompt_sign_in() {
    let content_str = '';
    content_str += form_entry('User Name', 'username_entry');
    content_str += form_entry('Password', 'password_entry', '', '', 'password');
    $.confirm({
        title: 'Sign In',
        content: content_str,
        buttons: {
            formSubmit: {
                text: 'Sign In',
                btnClass: 'btn-blue',
                action: () => {
                    const $content = $(document);
                    const username = $content.find('#username_entry').val() as string;
                    const password = $content.find('#password_entry').val() as string;
                    if (!verify_userpass(username, password)) {
                        return false;
                    }
                    unlock_user(username, password, false, 'unknown');
                    return true;
                }
            },
            newAccount: {
                text: 'Create New Account',
                btnClass: 'btn-blue',
                action: () => {
                    prompt_new_account();
                }
            }
        },
        onContentReady: () => {
            const $content = $(document);
            $content.find('form').on('submit', function(e: JQuery.Event) {
                e.preventDefault();
                $(e.target).trigger('click'); // reference the button and click it
            });
            register_enter_keypress($content, 'password_entry', 'Sign In');
        }
    });
}

let GLOBAL_UNLOCK_DEFERRED: JQuery.Deferred<any> | null = null;

function unlock_async(
    username: string,
    password: string,
    create_true: boolean,
    sync_approval: string,
    api_key: string,
    api_secret: string
): JQuery.Promise<UnlockResult> {
    let deferred: JQuery.Deferred<UnlockResult>;
    if (!GLOBAL_UNLOCK_DEFERRED) {
        console.log('At unlock_async start, creating new deferred object');
        deferred = $.Deferred();
        GLOBAL_UNLOCK_DEFERRED = deferred;
    } else {
        console.log('At unlock_async start, using global deferred object');
        deferred = GLOBAL_UNLOCK_DEFERRED;
    }

    service.unlock_user(username, password, create_true, sync_approval, api_key, api_secret).then(res => {
        if (!res.result) {
            if (res.permission_needed) {
                deferred.notify(res.message);
            } else {
                deferred.reject(res.message);
            }
            return;
        }
        deferred.resolve(res);
    }).catch((reason: Error) => {
        deferred.reject(reason);
    });

    return deferred.promise();
}

function unlock_user(
    username: string,
    password: string,
    create_true: boolean,
    sync_approval: string,
    api_key: string = '',
    api_secret: string = ''
) {
    $.alert({
        content: function() {
            const self = this as Alert;
            return unlock_async(username, password, create_true, sync_approval, api_key, api_secret).done(
                (response: UnlockResult) => {
                    const db_settings = response.settings;
                    if (!db_settings) {
                        self.setType('red');
                        self.setTitle('Sign In Failed');
                        self.setContentAppend('<div>main_currency not returned from db_settings</div>');
                        GLOBAL_UNLOCK_DEFERRED = null;
                        return;
                    }

                    self.setType('green');
                    self.setTitle('Successful Sign In');
                    self.setContentAppend(`<div>Welcome ${username}!</div>`);
                    (self.buttons.ok as ConfirmButton).keys = ['enter'];
                    $('#welcome_text').html(`Welcome ${username}!`);

                    setup_client_auditor();
                    settings.user_logged = true;
                    settings.has_premium = response.premium;
                    if (db_settings.premium_should_sync) {
                        settings.premium_should_sync = db_settings.premium_should_sync;
                    } else {
                        settings.premium_should_sync = false;
                    }

                    const new_main = db_settings.main_currency;
                    // Before any other calls happen let's make sure we got the
                    // exchange rates so that everything can be shown to the user
                    // in their desired currency. Empty list argument means to
                    // query all fiat currency pairs

                    service.get_fiat_exchange_rates().then(result => {
                        const rates = result.exchange_rates;
                        for (const asset in rates) {
                            if (!rates.hasOwnProperty(asset)) {
                                continue;
                            }
                            settings.usd_to_fiat_exchange_rates[asset] = parseFloat(rates[asset]);
                        }
                        set_ui_main_currency(new_main);

                        settings.floating_precision = db_settings.ui_floating_precision;
                        settings.historical_data_start = db_settings.historical_data_start;
                        settings.eth_rpc_port = db_settings.eth_rpc_port;
                        settings.include_crypto2crypto = db_settings.include_crypto2crypto;
                        settings.include_gas_costs = db_settings.include_gas_costs;
                        settings.taxfree_after_period = db_settings.taxfree_after_period;
                        settings.balance_save_frequency = db_settings.balance_save_frequency;
                        settings.last_balance_save = db_settings.last_balance_save;
                        settings.anonymized_logs = db_settings.anonymized_logs;

                        const is_new_user = create_true && api_key === '';
                        const exchanges = response.exchanges;
                        if (!exchanges) {
                            return;
                        }
                        load_dashboard_after_unlock(exchanges, is_new_user);
                    }).catch((reason: Error) => {
                        showError('Connectivity Error', `Failed to acquire fiat to USD exchange rates: ${reason.message}`);
                    });

                    GLOBAL_UNLOCK_DEFERRED = null;
                }).progress((msg: string) => {
                    ask_permission(msg, username, password, create_true, api_key, api_secret);
                }).fail((error: Error) => {
                    self.setType('red');
                    self.setTitle('Sign In Failed');
                    self.setContentAppend(`<div>${error}</div>`);
                    // @ts-ignore
                    self.buttons.ok.action = () => prompt_sign_in();
                    GLOBAL_UNLOCK_DEFERRED = null;
                });
        }
    });
}

function load_dashboard_after_unlock(exchanges: string[], is_new_user: boolean) {
    for (let i = 0; i < exchanges.length; i++) {
        const exx = exchanges[i];
        settings.connected_exchanges.push(exx);
        query_exchange_balances_async(exx, true);
    }

    if (!is_new_user) {
        get_blockchain_total();
        get_banks_total();
    } else {
        showInfo(
            'Welcome to Rotkehlchen!',
            'It appears this is your first time using the program. ' +
            'Follow the suggestions to integrate with some exchanges or manually input data.'
        );
        suggest_element('#user-dropdown', 'click_user_dropdown');
        $('#user-dropdown').click(() => {
            if (settings.start_suggestion === 'click_user_dropdown') {
                unsuggest_element('#user-dropdown');
                suggest_element('#user_settings_button', 'click_user_settings');
            }
        });
    }
    create_or_reload_dashboard();

}

function get_blockchain_total() {
    service.query_blockchain_balances_async().then(result => {
        console.log(`Blockchain balances returned task id ${result.task_id}`);
        create_task(result.task_id, 'query_blockchain_balances_async', 'Query Blockchain Balances', true, true);
    }).catch((reason: Error) => {
        console.log(`Error at querying blockchain balances: ${reason}`);
    });
}

function get_banks_total() {
    service.query_fiat_balances().then(result => {
        const fiat_total = get_total_assets_value(result);
        console.log(`query fiat balances result is: ${JSON.stringify(result, null, 4)}`);
        console.log(`Fiat total is: ${fiat_total}`);
        if (fiat_total !== 0.0) {
            create_box(
                'banks_box',
                'fa-university',
                fiat_total,
                settings.main_currency.icon
            );
            total_table_add_balances('banks', result);
        }
    }).catch((reason: Error) => {
        console.log(`Error at querying fiat balances`);
        console.error(reason);
    });
}
