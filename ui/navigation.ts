import { add_taxreport_listeners, create_taxreport_ui } from './taxreport';
import { create_or_reload_dashboard } from './dashboard';
import { add_user_settings_listeners, create_user_settings } from './user_settings';
import { add_otctrades_listeners, create_otctrades_ui } from './otctrades';
import { add_accounting_settings_listeners, create_accounting_settings } from './accounting_settings';
import { add_settings_listeners, assert_exchange_exists, create_settings_ui, pages, settings, reset_pages } from './settings';
import { service } from './rotkehlchen_service';

export function determine_location(url: string) {
    const split = url.split('#');
    if (split.length === 1 || split[1] === '') {
        return '';
    }
    return split[1];
}

function save_current_location() {
    if (!settings.current_location || settings.current_location === '') {
        return; // we are at the start of the program
    }

    if (settings.current_location === 'index') {
        console.log('Saving index ... ');
        pages.page_index = $('#page-wrapper').html();
    } else if (settings.current_location === 'otctrades') {
        console.log('Saving otc trades ... ');
        pages.page_otctrades = $('#page-wrapper').html();
    } else if (settings.current_location === 'settings') {
        console.log('Saving settings ... ');
        pages.settings = $('#page-wrapper').html();
    } else if (settings.current_location.startsWith('exchange_')) {
        const exchange_name = settings.current_location.substring(9);
        assert_exchange_exists(exchange_name);
        console.log(`Moving out of exchange ${exchange_name} without saving.`);
    } else if (settings.current_location === 'user_settings') {
        console.log('Saving user settings ...');
        pages.page_user_settings = $('#page-wrapper').html();
    } else if (settings.current_location === 'accounting_settings') {
        console.log('Saving accounting settings ...');
        pages.page_accounting_settings = $('#page-wrapper').html();
    } else if (settings.current_location === 'taxreport') {
        console.log('Saving tax report ...');
        pages.page_taxreport = $('#page-wrapper').html();
    } else {
        throw new Error('Invalid link location ' + settings.current_location);
    }
}

export function change_location(target: string) {
    save_current_location();
    console.log('Changing location to ' + target);
    settings.current_location = target;
}

function create_or_reload_page(name: string, create_callback: () => void, always_callback: () => void) {
    change_location(name);
    if (!pages['page_' + name]) {
        console.log(`At create/reload ${name} with a null page index`);
        create_callback();
    } else {
        console.log(`At create/reload ${name} with a populated page index`);
        $('#page-wrapper').html(pages['page_' + name] as string);
    }
    always_callback();
}

export function init_navigation() {
    $('#side-menu a').click(event => {
        event.preventDefault();
        const target = event.target as HTMLAnchorElement;
        const target_location = determine_location(target.href);

        if (target_location === 'otctrades') {
            create_or_reload_page('otctrades', create_otctrades_ui, add_otctrades_listeners);
        } else if (target_location === 'index') {
            create_or_reload_dashboard();
        } else if (target_location === 'taxreport') {
            create_or_reload_page('taxreport', create_taxreport_ui, add_taxreport_listeners);
        }
        // else do nothing -- no link
    });

    $('#settingsbutton a').click(event => {
        event.preventDefault();
        const target = event.target as HTMLAnchorElement;
        const target_location = determine_location(target.href);
        if (target_location !== 'settings') {
            throw new Error('Invalid link location ' + target_location);
        }
        create_or_reload_page('settings', create_settings_ui, add_settings_listeners);
    });

    $('#user_settings_button a').click(event => {
        event.preventDefault();
        const target = event.target as HTMLAnchorElement;
        const target_location = determine_location(target.href);
        if (target_location !== 'user_settings') {
            throw new Error('Invalid link location ' + target_location);
        }
        create_or_reload_page('user_settings', create_user_settings, add_user_settings_listeners);
    });

    $('#accounting_settings_button a').click(event => {
        event.preventDefault();
        const target = event.target as HTMLAnchorElement;
        const target_location = determine_location(target.href);
        if (target_location !== 'accounting_settings') {
            throw new Error('Invalid link location ' + target_location);
        }
        create_or_reload_page('accounting_settings', create_accounting_settings, add_accounting_settings_listeners);
    });

    $('#logout_button a').click(event => {
        event.preventDefault();
        const target = event.target as HTMLAnchorElement;
        const target_location = determine_location(target.href);
        if (target_location !== 'logout') {
            throw new Error('Invalid link location ' + target_location);
        }
        $.confirm({
            title: 'Confirmation Required',
            content: 'Are you sure you want to log out of your current rotkehlchen session?',
            buttons: {
                confirm: function() {
                    service.logout().then(() => {
                        $('#welcome_text').html('');
                        settings.reset();
                        reset_pages();
                        create_or_reload_dashboard();
                    }).catch((reason: Error) => {
                        console.log(`Error at logout`);
                        console.error(reason);
                    });
                },
                cancel: function() {
                }
            }
        });
    });
}
