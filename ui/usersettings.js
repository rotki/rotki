var settings = require("./settings.js")();
require("./elements.js")();
require("./asset_table.js")();

let FIAT_TABLE = null;
let FIAT_BALANCES = null;
// awesome idea of template string plus destructuring/mapping taken from:
// https://stackoverflow.com/a/39065147/110395
const ExchangeBadge = ({ name, css_class }) => `
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

function disable_exchange_entry(selector_text, value) {
    $(selector_text).parent().removeClass().addClass('form-group input-group has-success');
    $(selector_text).attr('disabled', true);
    $(selector_text).val(value);
}

function enable_exchange_entry(selector_text) {
    $(selector_text).parent().removeClass().addClass('form-group input-group');
    $(selector_text).attr('disabled', false);
    $(selector_text).val('');
}

function disable_exchange_entries(val) {
    disable_exchange_entry('#api_key_entry', val + ' API Key is already registered');
    disable_exchange_entry('#api_secret_entry', val + ' API Secret is already registered');
    $('#setup_exchange_button').html('Remove');
}

function enable_exchange_entries() {
    enable_exchange_entry('#api_key_entry');
    enable_exchange_entry('#api_secret_entry');
    $('#setup_exchange_button').html('Setup');
}

function setup_exchange_callback(event) {
    event.preventDefault();
    let button_type = $('#setup_exchange_button').html();
    var exchange_name = $('#setup_exchange').val();
    if (button_type == 'Remove') {
        $.confirm({
            title: 'Confirmation Required',
            content: 'Are you sure you want to delete the API key and secret from rotkehlchen? This action is not undoable and you will need to obtain the key and secret again from the exchange.',
            buttons: {
                confirm: function () {
                    client.invoke(
                        "remove_exchange",
                        exchange_name,
                        (error, res) => {
                            if (error || res == null) {
                                showAlert('alert-danger', 'Error at removing ' + exchange_name + ' exchange: ' + error);
                                return;
                            }
                            // else
                            if (!res['result']) {
                                showAlert('alert-danger', 'Error at removing ' + exchange_name + ' exchange: ' + res['message']);
                                return;
                            }
                            // Exchange removal from backend succesfull
                            enable_exchange_entries();
                            $('#'+exchange_name+'_badge').remove();
                            var index = settings.connected_exchanges.indexOf(exchange_name);
                            if (index == -1) {
                                throw "Exchange " + exchange_name + "was not in connected_exchanges when trying to remove";
                            }
                            settings.connected_exchanges.splice(index, 1);

                        });
                },
                cancel: function () {}
            }
        });
        return;
    }
    // else simply add it
    let api_key = $('#api_key_entry').val();
    let api_secret = $('#api_secret_entry').val();
    client.invoke(
        "setup_exchange",
        exchange_name,
        api_key,
        api_secret,
        (error, res) => {
            if (error || res == null) {
                showAlert('alert-danger', 'Error at setup of ' + exchange_name + ': ' + error);
                return;
            }
            // else
            if (!res['result']) {
                showAlert('alert-danger', 'Error at setup of ' + exchange_name + ': ' + res['message']);
                return;
            }
            // Exchange setup in the backend was succesfull
            disable_exchange_entries(exchange_name);
            settings.connected_exchanges.push(exchange_name);
            let str = ExchangeBadge({name: exchange_name, css_class: 'exchange-icon'});
            $(str).appendTo($('#exchange_badges'));

        }
    );
}

function fiat_selection_callback(event) {
    if (!FIAT_BALANCES) {
        return;
    }

    if (FIAT_BALANCES.hasOwnProperty(this.value)) {
        $('#fiat_value_entry').val(FIAT_BALANCES[this.value]['amount']);
        $('#modify_fiat_button').html('Modify Balance');
    } else {
        $('#fiat_value_entry').val('');
        $('#modify_fiat_button').html('Add Balance');
    }
}

function fiat_modify_callback(event) {
    event.preventDefault();
    let button_type = $('#modify_fiat_button').html();
    let currency = $('#fiat_type_entry').val();
    let balance = $('#fiat_value_entry').val();

    client.invoke(
        "set_fiat_balance",
        currency,
        balance,
        (error, result) => {
            if (error || !result) {
                showAlert('alert-danger', 'Error at modifying ' + currency + ' balance: ' + error);
                return;
            }
            if (!result['result']) {
                showAlert('alert-danger', 'Error at modifying ' + currency + ' balance: ' + result['message']);
                return;
            }
            if (balance == '') {
                delete FIAT_BALANCES[currency];
            } else {
                FIAT_BALANCES[currency] = {'amount': balance, 'usd_value': get_fiat_usd_value(currency, balance)};
            }
            // simply add the new data to the table
            FIAT_TABLE.clear();
            let data = format_table_data(FIAT_BALANCES);
            FIAT_TABLE.rows.add(data);
            FIAT_TABLE.draw();
        });
}

function add_listeners() {
    $('#setup_exchange').change(function (event) {
        if (settings.connected_exchanges.indexOf(this.value) > -1) {
            disable_exchange_entries(this.value);
        } else {
            enable_exchange_entries();
        }
    });
    $('#setup_exchange_button').click(setup_exchange_callback);
    $('#fiat_type_entry').change(fiat_selection_callback);
    $('#modify_fiat_button').click(fiat_modify_callback);
}

function create_user_settings() {
    var str = page_header('User Settings');
    str += settings_panel('Exchange Settings', 'exchange');
    str += settings_panel('Fiat Balances', 'fiat_balances');
    $('#page-wrapper').html(str);

    let badge_input = settings.connected_exchanges.map(x => ({name: x, css_class: 'exchange-icon'}));
    str = '<div id="exchange_badges" class="row">';
    str += badge_input.map(ExchangeBadge).join('');
    str += '</div>';

    str += form_select('Setup Exchange', 'setup_exchange', settings.EXCHANGES, '');
    str += form_entry('Api Key', 'api_key_entry', '', '');
    str += form_entry('Api Secret', 'api_secret_entry', '', '');
    str += form_button('Setup', 'setup_exchange_button');

    $(str).appendTo($('#exchange_panel_body'));

    // essentially call the on-select for the first choice
    let first_value = settings.EXCHANGES[0];
    if (settings.connected_exchanges.indexOf(first_value) > -1) {
        disable_exchange_entries(first_value);
    }

    str = form_select('Modify Balance', 'fiat_type_entry', settings.CURRENCIES.map(x=>x.ticker_symbol), settings.main_currency.ticker_symbol);
    str += form_entry('Balance', 'fiat_value_entry', '', '');
    str += form_button('Modify', 'modify_fiat_button');

    $(str).appendTo($('#fiat_balances_panel_body'));
    create_fiat_table();
}

function create_fiat_table() {
    client.invoke('query_fiat_balances', (error, result) => {
        if (error || result == null) {
            console.log("Error at querying fiat balances:" + error);
            return;
        }
        FIAT_BALANCES = result;
        let str = '<h4 class="centered-title">Owned Fiat Currency Balances</h4>';
        $(str).appendTo($('#fiat_balances_panel_body'));
        FIAT_TABLE = create_asset_table('fiat_balances', 'fiat_balances_panel_body', result);
    });
}

function reload_fiat_table_if_existing() {
    reload_asset_table(FIAT_TABLE);
}

function create_or_reload_usersettings() {
    change_location('usersettings');
    if (!settings.page_usersettings) {
        console.log("At create/reload usersettings, with a null page index");
        create_user_settings();
    } else {
        console.log("At create/reload usersettings, with a Populated page index");
        $('#page-wrapper').html(settings.page_usersettings);
    }
    add_listeners();
}

module.exports = function() {
    this.create_or_reload_usersettings = create_or_reload_usersettings;
    this.reload_fiat_table_if_existing = reload_fiat_table_if_existing;
};
