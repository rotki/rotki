var fs = require('fs');
var Tail = require('tail').Tail;
var settings = require("./settings.js");


var log_searcher = null;

function _setup_log_watcher(callback) {

    if (log_searcher) {
        if (!fs.existsSync("rotkelchen.log")) {
            return;
        }
        clearInterval(log_searcher);
    }

    var options = { fromBeginning: true};
    var tail = new Tail("rotkelchen.log");

    var rePattern = new RegExp('.*(WARNING|ERROR):.*:(.*)');
    tail.on("line", function(data) {
        var matches = data.match(rePattern);
        if (matches != null) {
            callback(matches[2], new Date().getTime() / 1000);
            console.log(matches[2]);
        }
    });

    tail.on("error", function(error) {
        console.log('TAIL ERROR: ', error);
    });
}

function setup_log_watcher(callback) {

    // if the log file is not found keep trying until it is
    if (!fs.existsSync("rotkelchen.log")) {
        log_searcher = setInterval(function() {_setup_log_watcher(callback);}, 5000);
        return;
    }
    _setup_log_watcher(callback);
}

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
    } else if (settings.current_location == 'external_trades') {
        console.log("Saving external trades ... ");
        settings.page_external_trades = $('#page-wrapper').html();
    } else if (settings.current_location.startsWith('exchange_')) {
        let exchange_name = settings.current_location.substring(9);
        settings.assert_exchange_exists(exchange_name);
        console.log("Saving exchange " + exchange_name);
        settings.page_exchange[exchange_name] = $('#page-wrapper').html();
    } else {
        throw "Invalid link location " + settings.current_location;
    }
}

function change_location(target) {
    save_current_location();
    console.log("Changing location to " + target);
    settings.current_location = target;
}


module.exports = function() {
    this.setup_log_watcher = setup_log_watcher;
    this.change_location = change_location;
    this.determine_location = determine_location;
};
