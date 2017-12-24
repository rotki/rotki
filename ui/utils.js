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


module.exports = function() {
    this.setup_warnings_watcher = setup_warnings_watcher;
};
