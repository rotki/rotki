var settings = require("./settings.js")();


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

function add_listeners() {
    $('#setup_exchange').change(function (event) {
        if (settings.connected_exchanges.indexOf(this.value) > -1) {
            disable_exchange_entries(this.value);
        } else {
            enable_exchange_entries();
        }
    });
    $('#setup_exchange_button').click(setup_exchange_callback);
}

function create_user_settings() {
    var str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">User Settings</h1></div></div>';
    str += '<div class="row"><div class="col-lg-12"><div class="panel panel-default"><div class="panel-heading">Exchange Settings</div><div class="panel-body"></div></div></div></div>';
    $('#page-wrapper').html(str);


    // awesome idea of template string plus destructuring/mapping taken from:
    // https://stackoverflow.com/a/39065147/110395
    let badge_input = settings.connected_exchanges.map(x => ({name: x, css_class: 'exchange-icon'}));
    str = '<div id="exchange_badges" class="row">';
    str += badge_input.map(ExchangeBadge).join('');
    str += '</div>';

    str += '<div class="row">';
    str += form_select('Setup Exchange', 'setup_exchange', settings.EXCHANGES);
    str += form_entry('Api Key', 'api_key_entry', '', '');
    str += form_entry('Api Secret', 'api_secret_entry', '', '');
    str += form_button('Setup', 'setup_exchange_button');
    str += '</div>';

    $(str).appendTo($('.panel-body'));

    // essentially call the on-select for the first choice
    let first_value = settings.EXCHANGES[0];
    if (settings.connected_exchanges.indexOf(first_value) > -1) {
        disable_exchange_entries(first_value);
    }
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
};
