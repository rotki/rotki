var settings = require("./settings.js")();

function determine_location(url) {
    var split = url.split('#');
    if (split.length == 1 || split[1] == '') {
        return 'index';
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

function init_navigation() {
    $('#side-menu a').click(function(event) {
        event.preventDefault();
        var target_location = determine_location(this.href);

        if (target_location == 'otctrades') {
            create_or_reload_otctrades();
        } else if (target_location == 'index') {
            create_or_reload_dashboard();
        } else {
            throw "Invalid link target location " + target_location;
        }
    });
}

module.exports = function() {
    this.init_navigation = init_navigation;
    this.change_location = change_location;
    this.determine_location = determine_location;
};
