require("./zerorpc_client.js")();
var settings = require("./settings.js")();
require("./elements.js")();
require("./monitor.js")();
require("./utils.js")();

function verify_userpass(username, password) {
    if (!username) {
        $.alert('Please provide a user name');
        return false;
    }
    if (! /^[0-9a-zA-Z_.-]+$/.test(username)) {
        $.alert('A username must contain only alphanumeric characters and have no spaces');
        return false;
    }
    if (!password) {
        $.alert('Please provide a password');
        return false;
    }
    return true;
}

function ask_permission(msg, username, password, create_true, api_key, api_secret) {
    $.confirm({
        title: 'Sync Permission Required',
        content: msg,
        buttons: {
            yes: {
                text: 'Yes',
                btnClass: 'btn-blue',
                action: function () {unlock_async(username, password, create_true, 'yes', api_key, api_secret);}
            },
            no:  {
                text: 'No',
                btnClass: 'btn-red',
                action: function () {unlock_async(username, password, create_true, 'no', api_key, api_secret);}
            }
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
                action: function () {
                    let username = this.$content.find('#user_name_entry').val();
                    let password = this.$content.find('#password_entry').val();
                    let password2 = this.$content.find('#repeat_password_entry').val();
		    let api_key = this.$content.find('#api_key_entry').val();
		    let api_secret = this.$content.find('#api_secret_entry').val();
                    if (!verify_userpass(username, password)) {
                        return false;
                    }

                    if (password != password2) {
                        $.alert('The given passwords don\'t match');
                        return false;
                    }
                    unlock_user(username, password, true, 'unknown', api_key, api_secret);
                }
            },
            cancel: function () { prompt_sign_in();}
        },
        onContentReady: function () {
            // bind to events
            var jc = this;
            this.$content.find('form').on('submit', function (e) {
                // if the user submits the form by pressing enter in the field.
                e.preventDefault();
                jc.$$formSubmit.trigger('click'); // reference the button and click it
            });
        }
    });
}

function prompt_sign_in() {
    let content_str = '';
    content_str += form_entry('User Name', 'username_entry', '', '');
    content_str += form_entry('Password', 'password_entry', '', '', 'password');
    $.confirm({
        title: 'Sign In',
        content: content_str,
        buttons: {
            formSubmit: {
                text: 'Sign In',
                btnClass: 'btn-blue',
                action: function () {
                    let username = this.$content.find('#username_entry').val();
                    let password = this.$content.find('#password_entry').val();
                    if (!verify_userpass(username, password)) {
                        return false;
                    }
                    unlock_user(username, password, false, 'unknown', '', '');
                }
            },
            newAccount: {
                text: 'Create New Account',
                btnClass: 'btn-blue',
                action: function () {
                    prompt_new_account();
                }
            }
        },
        onContentReady: function () {
            // bind to events
            var jc = this;
            this.$content.find('form').on('submit', function (e) {
                // if the user submits the form by pressing enter in the field.
                e.preventDefault();
                jc.$$formSubmit.trigger('click'); // reference the button and click it
            });
        }
    });
}

var GLOBAL_UNLOCK_DEFERRED = null;
function unlock_async(username, password, create_true, sync_approval, api_key, api_secret) {
    var deferred;
    if (!GLOBAL_UNLOCK_DEFERRED) {
        console.log("At unlock_async start, creating new deferred object");
        deferred = $.Deferred();
        GLOBAL_UNLOCK_DEFERRED = deferred;
    } else {
        console.log("At unlock_async start, using global deferred object");
        deferred = GLOBAL_UNLOCK_DEFERRED;
    }
    client.invoke("unlock_user", username, password, create_true, sync_approval, api_key, api_secret, (error, res) => {
        if (error || res == null) {
            deferred.reject(error);
            return;
        }
        if (!res['result']) {
            if ('permission_needed' in res) {
                deferred.notify(res['message']);
            } else {
                deferred.reject(res['message']);
            }
            return;
        }
        deferred.resolve(res);
    });
    return deferred.promise();
}

function unlock_user(username, password, create_true, sync_approval, api_key, api_secret) {
    $.alert({
        content: function(){
            var self = this;
            return unlock_async(username, password, create_true, sync_approval, api_key, api_secret).done(
                function (response) {
                    self.setType('green');
                    self.setTitle('Succesfull Sign In');
                    self.setContentAppend(`<div>Welcome ${username}!</div>`);
                    $('#welcome_text').html(`Welcome ${username}!`);
                    let is_new_user = create_true && api_key == '';
                    load_dashboard_after_unlock(response['exchanges'], is_new_user);
                    settings.has_premium = response['premium'];
                    let db_settings = response['settings'];
                    if ('premium_should_sync' in db_settings) {
                        settings.premium_should_sync = db_settings['premium_should_sync'];
                    } else {
                        settings.premium_should_sync = false;
                    }
                    GLOBAL_UNLOCK_DEFERRED = null;
                }).progress(function(msg){
                    ask_permission(msg, username, password, create_true, api_key, api_secret);
                }).fail(function(error){
                    self.setType('red');
                    self.setTitle('Sign In Failed');
                    self.setContentAppend(`<div>${error}</div>`);
                    self.buttons.ok.action = function () {prompt_sign_in();};
                    GLOBAL_UNLOCK_DEFERRED = null;
                });
        }
    });
}

function load_dashboard_after_unlock(exchanges, is_new_user) {
    for (let i = 0; i < exchanges.length; i++) {
        let exx = exchanges[i];
        settings.connected_exchanges.push(exx);
        client.invoke("query_exchange_total_async", exx, true, function (error, res) {
            if (error || res == null) {
                console.log("Error at first query of an exchange's balance: " + error);
                return;
            }
            create_task(res['task_id'], 'query_exchange_total', 'Query ' + exx + ' Exchange');
        });
    }

    if (!is_new_user) {
        client.invoke("query_balances_async", function (error, res) {
            if (error || res == null) {
                console.log("Error at query balances async: " + error);
                return;
            }
            create_task(res['task_id'], 'query_balances', 'Query all balances');
        });

        get_blockchain_total();
        get_banks_total();
    } else {
        showInfo(
            'Welcome to Rotkehlchen!',
            'It appears this is your first time using the program. Follow the suggestions to integrate with some exchanges or manually input data.'
        );
        suggest_element('#user-dropdown', 'click_user_dropdown');
        $('#user-dropdown').click(function(event) {
            if (settings.start_suggestion == 'click_user_dropdown') {
                unsuggest_element('#user-dropdown');
                suggest_element('#usersettingsbutton', 'click_user_settings');
            }
        });
    }

}

function get_blockchain_total() {
    client.invoke("query_blockchain_total_async", (error, res) => {
        if (error || res == null) {
            console.log("Error at querying blockchain total: " + error);
        } else {
            console.log("Blockchain total returned task id " + res['task_id']);
            create_task(res['task_id'], 'query_blockchain_total', 'Query Blockchain Balances');
        }
    });
}

function get_banks_total() {
    client.invoke("query_fiat_total", (error, res) => {
        if (error || res == null) {
            console.log("Error at querying fiat total: " + error);
        } else {
            let fiat_total = parseFloat(res['total']);
            if (fiat_total != 0.0) {

                create_box(
                    'banks_balance',
                    'fa-university',
                    fiat_total,
                    settings.main_currency.icon
                );
            }
        }
    });
}

module.exports = function() {
    this.prompt_sign_in = prompt_sign_in;
};
