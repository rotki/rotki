require("./elements.js")();
require("./utils.js")();

function populate_ignored_assets() {
    client.invoke('get_ignored_assets', (error, result) => {
        if (error || result == null) {
            showError('Error getting ignored assets');
            return;
        }

        $('#ignored_assets_selection').append($('<option>', {
            value: '',
            text: 'Click to see all ignored assets and select one for removal'
        }));
        let assets = result['ignored_assets'];
        $.each(assets, function (i, asset) {
            $('#ignored_assets_selection').append($('<option>', {
                value: asset,
                text : asset
            }));
        });
    });
}

function ignored_asset_modify_callback(event) {
    event.preventDefault();
    let button_type = $('#modify_ignored_asset_button').html();
    let asset = $('#ignored_asset_entry').val();

    let command = 'add_ignored_asset';
    if (button_type == 'Remove') {
        command = 'remove_ignored_asset';
    }

    client.invoke(
        command,
        asset,
        (error, result) => {
            if (error || !result) {
                showError(
                    'Ignored Asset Modification Error',
                    'Error at modifying ignored asset ' + asset
                );
                return;
            }
            if (!result['result']) {
                showError(
                    'Ignored Asset Modification Error',
                    'Error at modifying ignored asset: ' + result['message']
                );
                return;
            }

            if (command == 'add_ignored_asset') {
                $('#ignored_assets_selection').append($('<option>', {
                    value: asset,
                    text: asset,
                    selected: true
                }));
            } else {
                $("#ignored_assets_selection option[value='"+asset+"']").remove();
                $('#modify_ignored_asset_button').html('Add');
                $('#ignored_asset_entry').val('');
            }
        });
}

function ignored_asset_selection_callback(event) {
    let asset = this.value;
    $('#ignored_asset_entry').val(asset);
    if (asset != '') {
        $('#modify_ignored_asset_button').html('Remove');
    } else {
        $('#modify_ignored_asset_button').html('Add');
    }
}

function add_accounting_settings_listeners() {
    $('#modify_ignored_asset_button').click(ignored_asset_modify_callback);
    $('#ignored_assets_selection').change(ignored_asset_selection_callback);
}

function create_accounting_settings() {
    var str = page_header('Accounting Settings');
    str += settings_panel('Asset Settings', 'assets');
    $('#page-wrapper').html(str);


    str = form_entry('Asset To Ignore', 'ignored_asset_entry', '', 'Assets to ignore during all accounting calculations');
    str += form_select('Ignored Assets', 'ignored_assets_selection', [], '');
    str += form_button('Add', 'modify_ignored_asset_button');
    $(str).appendTo($('#assets_panel_body'));
    populate_ignored_assets();
}

module.exports = function() {
    this.add_accounting_settings_listeners = add_accounting_settings_listeners;
    this.create_accounting_settings = create_accounting_settings;
};
