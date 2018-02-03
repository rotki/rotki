var settings = require("./settings.js")();

function determine_location(url) {
    var split = url.split('#');
    if (split.length == 1 || split[1] == '') {
        return '';
    }
    return split[1];
}

function save_current_location() {
    if (!settings.current_location) {
        return; //we are at the start of the program
    }

    if (settings.current_location == 'index') {
        console.log("Saving index ... ");
        settings.page_index = $('#page-wrapper').html();
    } else if (settings.current_location == 'otctrades') {
        console.log("Saving otc trades ... ");
        settings.page_otctrades = $('#page-wrapper').html();
    } else if (settings.current_location == 'settings') {
        console.log("Saving settings ... ");
        settings.settings = $('#page-wrapper').html();
    } else if (settings.current_location.startsWith('exchange_')) {
        let exchange_name = settings.current_location.substring(9);
        assert_exchange_exists(exchange_name);
        console.log("Saving exchange " + exchange_name);
        settings.page_exchange[exchange_name] = $('#page-wrapper').html();
    } else if (settings.current_location == 'usersettings') {
        console.log("Saving user settings ...");
        settings.page_usersettings = $('#page-wrapper').html();
    } else {
        throw "Invalid link location " + settings.current_location;
    }
}

function change_location(target) {
    save_current_location();
    console.log("Changing location to " + target);
    settings.current_location = target;
}

function create_or_reload_page(name, create_callback, always_callback) {
    change_location(name);
    if (!settings['page_'+name]) {
        console.log(`At create/reload ${name} with a null page index`);
        create_callback();
    } else {
        console.log(`At create/reload ${name} with a populated page index`);
        $('#page-wrapper').html(settings['page_'+name]);
    }
    always_callback();
}

function init_navigation() {
    $('#side-menu a').click(function(event) {
        event.preventDefault();
        var target_location = determine_location(this.href);

        if (target_location == 'otctrades') {
            create_or_reload_page('otctrades', create_otctrades_ui, add_otctrades_listeners);
        } else if (target_location == 'index') {
            create_or_reload_dashboard();
        }
        // else do nothing -- no link
    });

    $('#settingsbutton a').click(function(event) {
        event.preventDefault();
        var target_location = determine_location(this.href);
        if (target_location != "settings") {
            throw "Invalid link location " + target_location;
        }
        create_or_reload_page('settings', create_settings_ui, add_settings_listeners);
    });

    $('#usersettingsbutton a').click(function(event) {
        event.preventDefault();
        var target_location = determine_location(this.href);
        if (target_location != "usersettings") {
            throw "Invalid link location " + target_location;
        }
        create_or_reload_page('usersettings', create_user_settings, add_usersettings_listeners);
    });
}

module.exports = function() {
    this.init_navigation = init_navigation;
    this.change_location = change_location;
    this.determine_location = determine_location;
};
