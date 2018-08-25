import { settings } from './settings';
import client from './zerorpc_client';
import { showError, showInfo } from './utils';
import { form_button, form_entry, form_radio, form_select, page_header, settings_panel } from './elements';

function populate_ignored_assets(): void {
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
        $.each(assets, function (i: any, asset: any) {
            $('#ignored_assets_selection').append($('<option>', {
                value: asset,
                text : asset
            }));
        });
    });
}

function ignored_asset_modify_callback(event: any): void {
    event.preventDefault();
    let button_type = $('#modify_ignored_asset_button').html();
    let asset = $('#ignored_asset_entry').val();

    let command = 'add_ignored_asset';
    if (button_type === 'Remove') {
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

            if (command === 'add_ignored_asset') {
                $('#ignored_assets_selection').append($('<option>', {
                    value: asset,
                    text: asset,
                    selected: true
                }));
            } else {
                $('#ignored_assets_selection option[value=\'' + asset + PageTransitionEvent
            ).remove();
                $('#modify_ignored_asset_button').html('Add');
                $('#ignored_asset_entry').val('');
            }
        });
}

function ignored_asset_selection_callback(event: any): void {
    let asset = this.value;
    $('#ignored_asset_entry').val(asset);
    if (asset !== '') {
        $('#modify_ignored_asset_button').html('Remove');
    } else {
        $('#modify_ignored_asset_button').html('Add');
    }
}

function crypto2crypto_callback(): void {
    let element = $(this);
    let name = element.val();
    let is_checked = element.prop('checked');

    // return if a deselect triggered the event (may be unnecessary)
    if (!is_checked) {
        return;
    }

    // change class of div-box according to checked radio-box
    let value = false;
    if  (name === 'Yes') {
        value = true;
    }
    client.invoke('set_settings', {'include_crypto2crypto': value}, (error, result) => {
        if (error || result == null) {
            showError('Error setting crypto to crypto', error);
            return;
        }
        if (!result['result']) {
            showError('Error setting crypto to crypto', result['message']);
            return;
        }

        showInfo('Success', 'Succesfully set crypto to crypto consideration value');
    });
}

function modify_trade_settings_callback(): void {
    let element = $('input[name=taxfree_period_exists]');
    let is_checked = element.prop('checked');

    // return if a deselect triggered the event (may be unnecessary)
    let value: number = null;
    if (is_checked) {
        value = parseInt($('#taxfree_period_entry').val().toString());
    }

    client.invoke('set_settings', {'taxfree_after_period': value}, (error, result) => {
        if (error || result == null) {
            showError('Error setting trade settings', error);
            return;
        }
        if (!result['result']) {
            showError('Error setting trade settings', result['message']);
            return;
        }

        showInfo('Success', 'Succesfully set trade settings');
    });
}

export function add_accounting_settings_listeners(): void {
    $('#modify_ignored_asset_button').click(ignored_asset_modify_callback);
    $('#ignored_assets_selection').change(ignored_asset_selection_callback);
    $('input[name=crypto2crypto]').change(crypto2crypto_callback);
    $('#modify_trade_settings').click(modify_trade_settings_callback);
}

export function create_accounting_settings(): void {
    let str = page_header('Accounting Settings');
    str += settings_panel('Trade Settings', 'trades');
    str += settings_panel('Asset Settings', 'assets');
    $('#page-wrapper').html(str);


    let starting_c2c = 'Yes';
    if (!settings.include_crypto2crypto) {
        starting_c2c = 'No';
    }
    let starting_taxfree_after_period_choice = 'Yes';
    let starting_taxfree_after_period = '';
    if (settings.taxfree_after_period === 0) {
        starting_taxfree_after_period_choice = 'No';
    } else {
        // get number of days of the setting
        starting_taxfree_after_period = (settings.taxfree_after_period / 86400).toString();
    }
    str = form_radio('Take into account crypto to crypto trades', 'crypto2crypto', ['Yes', 'No'], starting_c2c);
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

