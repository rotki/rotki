var settings = require("./settings.js");
require("./utils.js")();

function create_something(name) {
    var str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">' + name + '</h1></div></div>';
    str += '<div class="row">DETAILS AND STUFF</div>';
    $('#page-wrapper').html(str);
}

function create_or_reload_exchange(name) {
    save_current_location();
    if (!settings.page_exchange[name]) {
        console.log("At create/reload exchange, with a null page index");
        create_something(name);
    } else {
        console.log("At create/reload exchange, with a Populated page index");
        $('#page-wrapper').html(settings.page_exchange[name]);
    }
}


module.exports = function() {
    this.create_or_reload_exchange = create_or_reload_exchange;
};
