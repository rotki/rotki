import {showError, showInfo} from './utils';
import {form_button, form_entry, form_radio, form_select, page_header, settings_panel} from './elements';
import {settings} from './settings';
import {service} from './rotkehlchen_service';

function populate_ignored_assets() {
    service.get_ignored_assets().then(assets => {
        $('#ignored_assets_selection').append($('<option>', {
            value: '',
            text: 'Click to see all ignored assets and select one for removal'
        }));

        $.each(assets, (_, asset) => {
            $('#ignored_assets_selection').append($('<option>', {
                value: asset,
                text: asset
            }));
        });
    }).catch(() => {
        showError('Error getting ignored assets');
    });
}

function ignored_asset_modify_callback(event: JQuery.Event) {
    event.preventDefault();
    const button_type = $('#modify_ignored_asset_button').html();
    const asset = $('#ignored_asset_entry').val() as string;

    let add = true;
    if (button_type === 'Remove') {
        add = false;
    }

    service.modify_asset(add, asset).then(() => {
        if (add) {
            $('#ignored_assets_selection').append($('<option>', {
                value: asset,
                text: asset,
                selected: true
            }));
        } else {
            $(`#ignored_assets_selection option[value='${asset}']`).remove();
            $('#modify_ignored_asset_button').html('Add');
            $('#ignored_asset_entry').val('');
        }
    }).catch((reason: Error) => {
        showError(
            'Ignored Asset Modification Error',
            `Error at modifying ignored asset ${asset} (${reason.message})`
        );
    });
}

function ignored_asset_selection_callback(event: JQuery.Event) {
    const asset = $(event.target).val() as string;
    $('#ignored_asset_entry').val(asset);
    if (asset !== '') {
        $('#modify_ignored_asset_button').html('Remove');
    } else {
        $('#modify_ignored_asset_button').html('Add');
    }
}

function crypto2crypto_callback(event: JQuery.Event) {
    const element = $(event.target);
    const name = element.val();
    const is_checked = element.prop('checked');

    // return if a deselect triggered the event (may be unnecessary)
    if (!is_checked) {
        return;
    }

    // change class of div-box according to checked radio-box
    let value = false;
    if (name === 'Yes') {
        value = true;
    }
    service.set_settings({'include_crypto2crypto': value}).then(() => {
        showInfo('Success', 'Succesfully set crypto to crypto consideration value');
    }).catch(reason => {
        showError('Error setting crypto to crypto', reason.message);
    });
}

function include_gas_costs_callback(event: JQuery.Event) {
    const element = $(event.target);
    const name = element.val();
    const is_checked = element.prop('checked');

    // return if a deselect triggered the event (may be unnecessary)
    if (!is_checked) {
        return;
    }

    // change class of div-box according to checked radio-box
    let value = false;
    if (name === 'Yes') {
        value = true;
    }
    service.set_settings({'include_gas_costs': value}).then(() => {
        showInfo('Success', 'Succesfully set Ethereum gas costs value');
    }).catch(reason => {
        showError('Error setting Ethereum gas costs: ', reason.message);
    });
}

function modify_trade_settings_callback() {
    const element = $('input[name=taxfree_period_exists]');
    const is_checked = element.prop('checked');

    // return if a deselect triggered the event (may be unnecessary)
    let value = null;
    if (is_checked) {
        value = parseInt($('#taxfree_period_entry').val() as string, 10);
    }

    service.set_settings({'taxfree_after_period': value}).then(() => {
        showInfo('Success', 'Succesfully set trade settings');
    }).catch((reason: Error) => {
        showError('Error setting trade settings', reason.message);
    });
}

export function add_accounting_settings_listeners() {
    $('#modify_ignored_asset_button').click(ignored_asset_modify_callback);
    $('#ignored_assets_selection').change(ignored_asset_selection_callback);
    $('input[name=crypto2crypto]').change(crypto2crypto_callback);
    $('input[name=include_gas_costs]').change(include_gas_costs_callback);
    $('#modify_trade_settings').click(modify_trade_settings_callback);
}

export function create_accounting_settings() {
    let str = page_header('Accounting Settings');
    str += settings_panel('Trade Settings', 'trades');
    str += settings_panel('Asset Settings', 'assets');
    $('#page-wrapper').html(str);

    let starting_c2c = 'Yes';
    if (!settings.include_crypto2crypto) {
        starting_c2c = 'No';
    }

    let starting_include_gas_costs = 'Yes';
    if (!settings.include_gas_costs) {
        starting_include_gas_costs = 'No';
    }

    let starting_taxfree_after_period_choice = 'Yes';
    let starting_taxfree_after_period = '';
    if (!settings.taxfree_after_period) {
        starting_taxfree_after_period_choice = 'No';
    } else {
        // get number of days of the setting
        starting_taxfree_after_period = (settings.taxfree_after_period / 86400).toString();
    }
    str = form_radio('Take into account crypto to crypto trades', 'crypto2crypto', ['Yes', 'No'], starting_c2c);
    str += form_radio('Take into account Ethereum gas costs', 'include_gas_costs', ['Yes', 'No'], starting_include_gas_costs);
    str += form_radio('Is there a tax free period?', 'taxfree_period_exists', ['Yes', 'No'], starting_taxfree_after_period_choice);
    str += form_entry('Tax free after how many days', 'taxfree_period_entry', starting_taxfree_after_period, '');
    str += form_button('Set', 'modify_trade_settings');
    $(str).appendTo($('#trades_panel_body'));

    str = form_entry('Asset To Ignore', 'ignored_asset_entry', '', 'Assets to ignore during all accounting calculations');
    str += form_select('Ignored Assets', 'ignored_assets_selection', [], '');
    str += form_button('Add', 'modify_ignored_asset_button');
    $(str).appendTo($('#assets_panel_body'));
    populate_ignored_assets();
}
