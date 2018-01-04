var settings = require("./settings.js");
var Tail = require('tail').Tail;


function setup_warnings_watcher(callback) {
    var options = { fromBeginning: true};
    var tail = new Tail("rotkelchen.log");

    var rePattern = new RegExp('.*WARNING:.*:(.*)');
    tail.on("line", function(data) {
	var matches = data.match(rePattern);
	if (matches != null) {
	    callback(matches[1], new Date().getTime() / 1000);
	    console.log(matches[1]);
	}
    });

    tail.on("error", function(error) {
	console.log('TAIL ERROR: ', error);
    });
}

function determine_location(url) {
    var split = url.split('#');
    if (split.length == 1 || split[1] == '') {
        return 'index';
    }
    return split[1];
}

function save_current_location() {
    console.log("---> " + window.location.href);
    var current_location = determine_location(window.location.href);
    if (current_location == 'index') {
        console.log("Saving index ... ");
        settings.page_index = $('#page-wrapper').html();
    } else if (current_location == 'external_trades') {
        console.log("Saving external trades ... ");
        settings.page_external_trades = $('#page-wrapper').html();
    } else if (current_location.startsWith('exchange_')) {
        exchange_name = current_location.substring(9);
        settings.assert_exchange_exists(exchange_name);
        console.log("Saving exchange " + exchange_name);
        settings.page_external_trades = $('#page-wrapper').html();
    } else {
        throw "Invalid link location " + current_location;
    }
}


module.exports = function() {
    this.setup_warnings_watcher = setup_warnings_watcher;
    this.save_current_location = save_current_location;
    this.determine_location = determine_location;
};
