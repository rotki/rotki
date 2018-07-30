let fs = require('fs');
let Tail = require('tail').Tail;
import { settings } from './settings';
import { total_balances_get } from './balances_table';
import client from './zerorpc_client';
const {dialog} = require('electron').remote;


// Prompt a directory selection dialog and pass selected directory to callback
// Callback should be a function which accepts a single argument which will be
// a list of pathnames. The list should only contain 1 entry.
export function prompt_directory_select_async(callback: any) {
    dialog.showOpenDialog({
        title: 'Select a directory',
        properties: ['openDirectory']
    }, callback);
}


export function utc_now() {
    return Math.floor(Date.now() / 1000);
}

export function timestamp_to_date(ts: number) {
    let date = new Date(ts * 1000);
    return (
        ('0' + date.getUTCDate()).slice(-2) + '/' +
        ('0' + (date.getUTCMonth() + 1)).slice(-2) + '/' +
        date.getUTCFullYear() + ' ' +
        ('0' + date.getUTCHours()).slice(-2) + ':' +
        ('0' + date.getUTCMinutes()).slice(-2)
    );
}

let log_searcher = null;
let client_auditor = null;

/**
 * This function is called periodically, query some data from the
 * client and update the UI with the response.
 */
function periodic_client_query() {
    // for now only query when was the last time balance data was saved
    client.invoke('query_last_balance_save_time', (error, res) => {
        if (error || res == null) {
            console.log('Error at periodic client query');
            return;
        }
        settings.last_balance_save = res;
    });
}

function _setup_log_watcher(callback: any) {
    if (log_searcher) {
        if (!fs.existsSync('rotkehlchen.log')) {
            return;
        }
        clearInterval(log_searcher);
    }

    let tail = new Tail('rotkehlchen.log');

    let rePattern = new RegExp('.*(WARNING|ERROR):.*:(.*)');
    tail.on('line', function(data: any) {
        let matches = data.match(rePattern);
        if (matches != null) {
            callback(matches[2], new Date().getTime() / 1000);
            console.log(matches[2]);
        }
    });

    tail.on('error', function(error: Error) {
        console.log('TAIL ERROR: ', error);
    });
}

// Show an error with TITLE and CONTENT
// If CALLBACK is given then it should be a callback
// to call when close is pressed
export function showError(title: string, content?: string, callback?: any) {
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
export function showInfo(title: string, content: string) {
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

export function showWarning(title: string, content: string) {
    $.confirm({
        title: title,
        content: content,
        type: 'yellow',
        typeAnimated: true,
        buttons: {
            close: function() {
                return;
            }
        }
    });
}

// TODO: Remove this/replace with something else. In the case of a huge log hangs the entire app
export function setup_log_watcher(callback: any) {
    // if the log file is not found keep trying until it is
    if (!fs.existsSync('rotkehlchen.log')) {
        log_searcher = setInterval(function() {_setup_log_watcher(callback); }, 5000);
        return;
    }
    _setup_log_watcher(callback);
}

export function setup_client_auditor() {
    if (!client_auditor) {
        client_auditor = setInterval(periodic_client_query, 60000);
    }
}

export function reload_table_currency_val(table: any, colnum: number) {
    table.rows().invalidate();
    $(table.column(colnum).header()).text(settings.main_currency.ticker_symbol + ' value');
    table.draw();
}

export function reload_table_currency_val_if_existing(table: any, colnum: number) {
    if (table) {
        reload_table_currency_val(table, colnum);
    }
}

export function string_capitalize(s: string) {
    return s && s[0].toUpperCase() + s.slice(1);
}

export function throw_with_trace(str: string) {
    let err = new Error();
    throw new Error(str + '\n' + err.stack);
}

export function date_text_to_utc_ts(txt: string | number | string[]) {
    // for now assuming YYY/MM/DD HH:MM
    if (settings.datetime_format !== 'd/m/Y G:i') {
        throw new Error('Invalid datetime format');
    }
    let m = txt.toString().match(/\d+/g);
    let day = parseInt(m[0], 10);
    let month = parseInt(m[1], 10) - 1;
    let year = parseInt(m[2], 10);
    let hours = parseInt(m[3], 10);
    let seconds = parseInt(m[4], 10);
    return (new Date(Date.UTC(year, month, day, hours, seconds))).getTime() / 1000;
}

interface IctxMenuItems {
    edit: any;
    delete: any;
    sep1: string;
    quit: any;
}

export function dt_edit_drawcallback(id: string, edit_fn: any, delete_fn: any) {
    return function (settings: any) {
        let ctx_menu_items = {} as IctxMenuItems;
        if (edit_fn) {
            ctx_menu_items.edit = {name: 'Edit', icon: 'fa-edit'};
        }
        if (delete_fn) {
            ctx_menu_items.delete = {name: 'Delete', icon: 'fa-trash'};
        }
        ctx_menu_items.sep1 = '---------';
        ctx_menu_items.quit =  {name: 'Quit', icon: 'fa-sign-out'};

        $.contextMenu({
            selector: '#' + id + '_body tr td',
            callback: function(key: any, options: any) {
                let tr = $(this).closest('tr');
                let row = $('#' + id).DataTable().row(tr);
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
                default:
                    break;
                }

            },
            items: ctx_menu_items
        });
    };
}


export function unsuggest_element(selector: string) {
    $(selector).pulsate('destroy');
    $(selector).removeAttr('style');
}

export function suggest_element(selector: string, state_to_set: string) {
    settings.start_suggestion = state_to_set;
    $(selector).pulsate({
        color: '#e45325', // set the color of the pulse
        reach: 20,        // how far the pulse goes in px
        speed: 1000,      // how long one pulse takes in ms
        pause: 0,         // how long the pause between pulses is in ms
        glow: true,       // if the glow should be shown too
        repeat: true,     // will repeat forever if true, if given a number will repeat for that many times
        onHover: false    // if true only pulsate if user hovers over the element
    });
}

export function suggest_element_until_click(selector: any, state_to_set: string) {
    suggest_element(selector, state_to_set);
    $(selector).click(function(event: JQuery.Event<any, null>) {
        unsuggest_element(selector);
    });
}

export function get_total_asssets_value(asset_dict: any) {
    let value = 0;
    for (let asset in asset_dict) {
        if (asset_dict.hasOwnProperty(asset)) {
            value += parseFloat(asset_dict[asset].usd_value);
        }
    }
    return value;
}

export function* iterate_saved_balances() {
    let saved_balances = total_balances_get();
    for (let location in saved_balances) {
        if (saved_balances.hasOwnProperty(location)) {
            let total = get_total_asssets_value(saved_balances[location]);
            if (settings.EXCHANGES.indexOf(location) >= 0) {
                yield [location, total, null];
            } else {
                let icon;
                if (location === 'blockchain') {
                    icon = 'fa-hdd-o';
                } else if (location === 'banks') {
                    icon = 'fa-university';
                } else {
                    throw new Error('Invalid location at dashboard box from saved balance creation');
                }
                yield [location, total, icon];
            }
        }
    }
}

