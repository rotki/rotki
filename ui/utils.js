var fs = require('fs');
var Tail = require('tail').Tail;
var settings = require("./settings.js")();

function utc_now() {
    return Math.floor(Date.now() / 1000);
}

function timestamp_to_date(ts) {
    let date = new Date(ts * 1000);
    return (
        ("0" + date.getUTCDate()).slice(-2)+ '/' +
        ("0" + (date.getUTCMonth() + 1)).slice(-2) + '/' +
        date.getUTCFullYear() + ' ' +
        ("0" + date.getUTCHours()).slice(-2) + ':' +
        ("0" + date.getUTCMinutes()).slice(-2)
    );
}

function startup_error(text, reason) {
    let loading_wrapper = document.querySelector('.loadingwrapper');
    let loading_wrapper_text = document.querySelector('.loadingwrapper_text');
    loading_wrapper.style.background = "rgba( 255, 255, 255, .8 ) 50% 50% no-repeat";
    console.log(text);
    loading_wrapper_text.textContent = "ERROR: Failed to connect to the backend. Reason: " + reason + " Check Log for more details.";
}

var log_searcher = null;

function _setup_log_watcher(callback) {
    if (log_searcher) {
        if (!fs.existsSync("rotkehlchen.log")) {
            return;
        }
        clearInterval(log_searcher);
    }

    var options = { fromBeginning: true};
    var tail = new Tail("rotkehlchen.log");

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

// Show an error with TITLE and CONTENT
// If CALLBACK is given then it should be a callback
// to call when close is pressed
function showError(title, content, callback) {
    if (!callback) {
        callback = function() {};
    }
    $.confirm({
        title: title,
        content: content,
        type: 'red',
        typeAnimated: true,
        buttons: {
            close: callback
        }
    });
}

// Show an Info message with TITLE and CONTENT
function showInfo(title, content) {
    $.confirm({
        title: title,
        content: content,
        type: 'green',
        typeAnimated: true,
        buttons: {
            close: function() {}
        }
    });
}

// TODO: Remove this/replace with something else. In the case of a huge log hangs the entire app
function setup_log_watcher(callback) {
    // if the log file is not found keep trying until it is
    if (!fs.existsSync("rotkehlchen.log")) {
        log_searcher = setInterval(function() {_setup_log_watcher(callback);}, 5000);
        return;
    }
    _setup_log_watcher(callback);
}


function reload_table_currency_val(table, colnum) {
    table.rows().invalidate();
    $(table.column(colnum).header()).text(settings.main_currency.ticker_symbol + ' value');
    table.draw();
}

function reload_table_currency_val_if_existing(table, colnum) {
    if (table) {
        reload_table_currency_val(table, colnum);
    }
}

function string_capitalize(s) {
    return s && s[0].toUpperCase() + s.slice(1);
}

function throw_with_trace(str) {
    let err = new Error();
    throw str + "\n" + err.stack;
}

function date_text_to_utc_ts(txt) {
    // for now assuming YYY/MM/DD HH:MM
    if (settings.datetime_format != 'd/m/Y G:i') {
        throw "Invalid datetime format";
    }
    let m = txt.match(/\d+/g);
    let day = parseInt(m[0]);
    let month = parseInt(m[1]) - 1;
    let year = parseInt(m[2]);
    let hours = parseInt(m[3]);
    let seconds = parseInt(m[4]);
    return (new Date(Date.UTC(year, month, day, hours, seconds))).getTime() / 1000;
}

function dt_edit_drawcallback(id, edit_fn, delete_fn) {
    return function (settings) {
        let dt_api = this;
        let ctx_menu_items = {};
        if (edit_fn) {
            ctx_menu_items['edit'] = {name: "Edit", icon: "fa-edit"};
        }
        if (delete_fn) {
            ctx_menu_items['delete'] = {name: "Delete", icon: "fa-trash"};
        }
        ctx_menu_items['sep1'] = "---------";
        ctx_menu_items['quit'] =  {name: "Quit", icon: "fa-sign-out"};

        // idea taken from: https://stackoverflow.com/questions/43161236/how-to-show-edit-and-delete-buttons-on-datatables-when-right-click-to-rows
        $.contextMenu({
            selector: '#' + id + '_body tr td',
            callback: function(key, options) {
                var tr = $(this).closest('tr');
                var row = $('#'+id).DataTable().row(tr);
                // TODO: When move to SQL instead of files, simply use the primary key/id to select
                switch (key) {
                case 'delete' :
                    if (delete_fn) {
                        delete_fn(row);
                    }
                    break;
                case 'edit' :
                    if (edit_fn) {
                        edit_fn(row);
                    }
                    break;
                case 'quit':
                    break;
                }
            },
            items: ctx_menu_items
        });
    };
}


function unsuggest_element(selector) {
    $(selector).pulsate('destroy');
    $(selector).removeAttr('style');
}

function suggest_element(selector, state_to_set) {
    settings.start_suggestion = state_to_set;
    $(selector).pulsate({
        // color: $(this).css("background-color"), // set the color of the pulse
        color: "#e45325", // set the color of the pulse
        reach: 20,                              // how far the pulse goes in px
        speed: 1000,                            // how long one pulse takes in ms
        pause: 0,                               // how long the pause between pulses is in ms
        glow: true,                             // if the glow should be shown too
        repeat: true,                           // will repeat forever if true, if given a number will repeat for that many times
        onHover: false                          // if true only pulsate if user hovers over the element
    });
}

function suggest_element_until_click(selector, state_to_set) {
    suggest_element(selector, state_to_set);
    $(selector).click(function(event) {
        unsuggest_element(selector);
    });
}

function get_total_asssets_value(asset_dict) {
    var value = 0;
    for (var asset in asset_dict) {
        if (asset_dict.hasOwnProperty(asset)) {
            value += parseFloat(asset_dict[asset]['usd_value']);
        }
    }
    return value;
}

module.exports = function() {
    this.utc_now = utc_now;
    this.timestamp_to_date = timestamp_to_date;
    this.string_capitalize = string_capitalize;
    this.setup_log_watcher = setup_log_watcher;
    this.startup_error = startup_error;
    this.showError = showError;
    this.showInfo = showInfo;
    this.date_text_to_utc_ts = date_text_to_utc_ts;
    this.reload_table_currency_val = reload_table_currency_val;
    this.reload_table_currency_val_if_existing = reload_table_currency_val_if_existing;
    this.get_total_asssets_value = get_total_asssets_value;
    this.throw_with_trace = throw_with_trace;
    this.dt_edit_drawcallback = dt_edit_drawcallback;
    this.suggest_element = suggest_element;
    this.unsuggest_element = unsuggest_element;
    this.suggest_element_until_click = suggest_element_until_click;
};
