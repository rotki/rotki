var fs = require('fs');
var Tail = require('tail').Tail;
var settings = require("./settings.js")();

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

function showAlert(type, text) {
    // TODO: Change this with nicer pop ups from jquery confirm
    var str = '<div class="alert '+ type +' alert-dismissable"><button type="button" class="close" data-dismiss="alert">&times;</button>'+ text +'</div>';
    console.log("ALERT: " +text);
    $(str).prependTo($("#wrapper"));
}

function setup_log_watcher(callback) {

    // if the log file is not found keep trying until it is
    if (!fs.existsSync("rotkelchen.log")) {
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

module.exports = function() {
    this.string_capitalize = string_capitalize;
    this.setup_log_watcher = setup_log_watcher;
    this.startup_error = startup_error;
    this.showAlert = showAlert;
    this.reload_table_currency_val = reload_table_currency_val;
    this.reload_table_currency_val_if_existing = reload_table_currency_val_if_existing;
    this.throw_with_trace = throw_with_trace;
    this.dt_edit_drawcallback = dt_edit_drawcallback;
};
