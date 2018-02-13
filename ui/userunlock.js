require("./zerorpc_client.js")();
var settings = require("./settings.js")();
require("./elements.js")();
require("./monitor.js")();

function prompt_new_account() {
    let content_str = '';
    content_str += form_entry('User Name', 'user_name_entry', '', '');
    content_str += form_entry('Password', 'password_entry', '', '', 'password');
    content_str += form_entry('Repeat Password', 'repeat_password_entry', '', '', 'password');
    $.confirm({
        title: 'Create New Account',
        content: content_str,
        buttons: {
            formSubmit: {
                text: 'Create',
                btnClass: 'btn-blue',
                action: function () {
                    var name = this.$content.find('.name').val();
                    if(!name){
                        $.alert('provide a valid name');
                        return false;
                    }
                    $.alert('Your name is ' + name);
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
                    if (!username) {
                        $.alert('Please provide a user name');
                        return false;
                    }
                    if (!password) {
                        $.alert('Please provide a password');
                        return false;
                    }
                    unlock_user(username, password);
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

function unlock_async(username, password) {
    var deferred = $.Deferred();
    client.invoke("unlock_user", username, password, (error, res) => {
        if (error || res == null) {
            deferred.reject(error);
            return;
        }
        if (!res['result']) {
            deferred.reject(res['message']);
            return;
        }
        deferred.resolve(res);
    });
    return deferred.promise();
}

function unlock_user(username, password) {
    $.alert({
        content: function(){
            var self = this;
            return unlock_async(username, password).done(
                function (response) {
                    self.setType('green');
                    self.setTitle('Succesfull Sign In');
                    self.setContentAppend(`<div>Welcome ${username}!</div>`);
                    load_dashboard_after_unlock(response['exchanges']);
                }).fail(function(error){
                    self.setType('red');
                    self.setTitle('Sign In Failed');
                    self.setContentAppend(`<div>${error}</div>`);
                    self.buttons.ok.action = function () {prompt_sign_in();};
                });
        }
    });
}

function load_dashboard_after_unlock(exchanges) {
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

    client.invoke("query_balances_async", function (error, res) {
        if (error || res == null) {
            console.log("Error at query balances async: " + error);
            return;
        }
        create_task(res['task_id'], 'query_balances', 'Query all balances');
    });

    get_blockchain_total();
    get_banks_total();
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
            create_box(
                'banks_balance',
                'fa-university',
                parseFloat(res['total']),
                settings.main_currency.icon
            );
        }
    });
}

module.exports = function() {
    this.prompt_sign_in = prompt_sign_in;
};
