import { add_settings_listeners, assert_exchange_exists, create_settings_ui, settings } from './settings';
import { add_accounting_settings_listeners, create_accounting_settings } from './accounting_settings';
import { add_taxreport_listeners, create_taxreport_ui } from './taxreport';
import { add_otctrades_listeners, create_otctrades_ui } from './otctrades';
import { create_or_reload_dashboard } from './dashboard';
import { add_user_settings_listeners, create_user_settings } from './user_settings';

export function determine_location(url: any) {
    let split = url.split('#');
    if (split.length === 1 || split[1] === '') {
        return '';
    }
    return split[1];
}

function save_current_location() {
    if (!settings.current_location) {
        return; // we are at the start of the program
    }

    if (settings.current_location === 'index') {
        console.log('Saving index ... ');
        settings.page_index = $('#page-wrapper').html();
    } else if (settings.current_location === 'otctrades') {
        console.log('Saving otc trades ... ');
        settings.page_otctrades = $('#page-wrapper').html();
    } else if (settings.current_location === 'settings') {
        console.log('Saving settings ... ');
        settings.page_settings = $('#page-wrapper').html();
    } else if (settings.current_location.startsWith('exchange_')) {
        let exchange_name = settings.current_location.substring(9);
        assert_exchange_exists(exchange_name);
        console.log('Saving exchange ' + exchange_name);
        settings.page_exchange[exchange_name] = $('#page-wrapper').html();
    } else if (settings.current_location === 'user_settings') {
        console.log('Saving user settings ...');
        settings.page_user_settings = $('#page-wrapper').html();
    } else if (settings.current_location === 'accounting_settings') {
        console.log('Saving accounting settings ...');
        settings.page_accounting_settings = $('#page-wrapper').html();
    } else if (settings.current_location === 'taxreport') {
        console.log('Saving tax report ...');
        settings.page_taxreport = $('#page-wrapper').html();
    } else {
        throw new Error('Invalid link location ' + settings.current_location);
    }
}

export function change_location(target: any) {
    save_current_location();
    console.log('Changing location to ' + target);
    settings.current_location = target;
}

export function create_or_reload_page(name: string, create_callback: any, always_callback: any) {
    change_location(name);
    if (!settings['page_' + name]) {
        console.log(`At create/reload ${name} with a null page index`);
        create_callback();
    } else {
        console.log(`At create/reload ${name} with a populated page index`);
        $('#page-wrapper').html(settings['page_' + name]);
    }
    always_callback();
}

export function init_navigation() {
    $('#side-menu a').click(function(event: any) {
       // event.preventDefault();
        let target_location = determine_location(this.getAttribute('href'));

        if (target_location === 'otctrades') {
            create_or_reload_page('otctrades', create_otctrades_ui, add_otctrades_listeners);
        } else if (target_location === 'index') {
            create_or_reload_dashboard();
        } else if (target_location === 'taxreport') {
            create_or_reload_page('taxreport', create_taxreport_ui, add_taxreport_listeners);
        }
        // else do nothing -- no link
    });

    $('#settingsbutton a').click(function(event: any) {
        event.preventDefault();
        let target_location = determine_location(this.getAttribute('href'));
        if (target_location !== 'settings') {
            throw new Error('Invalid link location ' + target_location);
        }
        create_or_reload_page('settings', create_settings_ui, add_settings_listeners);
    });

    $('#user_settings_button a').click(function(event: any) {
        event.preventDefault();
        let target_location = determine_location(this.getAttribute('href'));
        if (target_location !== 'user_settings') {
            throw new Error('Invalid link location ' + target_location);
        }
        create_or_reload_page('user_settings', create_user_settings, add_user_settings_listeners);
    });

    $('#accounting_settings_button a').click(function(event: any) {
        event.preventDefault();
        let target_location = determine_location(this.getAttribute('href'));
        if (target_location !== 'accounting_settings') {
            throw new Error('Invalid link location ' + target_location);
        }
        create_or_reload_page('accounting_settings', create_accounting_settings, add_accounting_settings_listeners);
    });
}

