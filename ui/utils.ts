import {settings} from './settings';
import {remote} from 'electron';
import {service} from './rotkehlchen_service';
import Timer = NodeJS.Timer;

// Prompt a directory selection dialog and pass selected directory to callback
// Callback should be a function which accepts a single argument which will be
// a list of pathnames. The list should only contain 1 entry.
export function prompt_directory_select_async(callback: (directories: string[]) => void) {
    remote.dialog.showOpenDialog({
        title: 'Select a directory',
        properties: ['openDirectory']
    }, callback);
}


export function utc_now() {
    return Math.floor(Date.now() / 1000);
}

export function timestamp_to_date(ts: number) {
    const date = new Date(ts * 1000);
    return (
        ('0' + date.getUTCDate()).slice(-2) + '/' +
        ('0' + (date.getUTCMonth() + 1)).slice(-2) + '/' +
        date.getUTCFullYear() + ' ' +
        ('0' + date.getUTCHours()).slice(-2) + ':' +
        ('0' + date.getUTCMinutes()).slice(-2)
    );
}

let client_auditor: Timer;

/**
 * This function is called periodically, query some data from the
 * client and update the UI with the response.
 */
function periodic_client_query() {
    // for now only query when was the last time balance data was saved
    service.query_last_balance_save_time().then(value => {
        settings.last_balance_save = value;
    }).catch(reason => {
        console.log('Error at periodic client query' + reason);
    });
}


// Show an error with TITLE and CONTENT
// If CALLBACK is given then it should be a callback
// to call when close is pressed
export function showError(title: string, content?: string, callback?: () => void) {
    if (!callback) {
        callback = () => {
        };
    }
    $.confirm({
        title: title,
        content: content,
        type: 'red',
        typeAnimated: true,
        buttons: {
            close: {
                text: 'Close',
                keys: ['enter'],
                action: callback
            }
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
            close: {
                text: 'Close',
                keys: ['enter'],
            }
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
            close: {
                text: 'Close',
                keys: ['enter'],
            }
        }
    });
}

export function setup_client_auditor() {
    if (!client_auditor) {
        client_auditor = setInterval(periodic_client_query, 60000);
    }
}


export function reload_table_currency_val(table: DataTables.Api, colnum: number) {
    table.rows().invalidate();
    $(table.column(colnum).header()).text(settings.main_currency.ticker_symbol + ' value');
    table.draw();
}

export function reload_table_currency_val_if_existing(table: DataTables.Api, colnum: number) {
    if (table) {
        reload_table_currency_val(table, colnum);
    }
}

export function string_capitalize(s: string) {
    return s && s[0].toUpperCase() + s.slice(1);
}

export function date_text_to_utc_ts(txt: string) {
    // for now assuming YYY/MM/DD HH:MM
    if (settings.datetime_format !== 'd/m/Y G:i') {
        throw new Error('Invalid datetime format');
    }
    const m = txt.match(/\d+/g);

    if (!m) {
        throw new Error('match failed for ' + txt);
    }

    const day = parseInt(m[0], 10);
    const month = parseInt(m[1], 10) - 1;
    const year = parseInt(m[2], 10);
    const hours = parseInt(m[3], 10);
    const seconds = parseInt(m[4], 10);
    return (new Date(Date.UTC(year, month, day, hours, seconds))).getTime() / 1000;
}

interface MenuItem {
    readonly name: string;
    readonly icon: string;
}

export function dt_edit_drawcallback(
    id: string,
    edit_fn?: ((row: DataTables.RowMethods) => void) | null,
    delete_fn?: ((row: DataTables.RowMethods) => void) | null
) {
    return () => {
        const ctx_menu_items: { [key: string]: string | MenuItem } = {};

        if (edit_fn) {
            ctx_menu_items['edit'] = {name: 'Edit', icon: 'fa-edit'};
        }

        if (delete_fn) {
            ctx_menu_items['delete'] = {name: 'Delete', icon: 'fa-trash'};
        }
        ctx_menu_items['sep1'] = '---------';
        ctx_menu_items['quit'] = {name: 'Quit', icon: 'fa-sign-out'};

        // idea taken from:
        // https://stackoverflow.com/questions/43161236/how-to-show-edit-and-delete-buttons-on-datatables-when-right-click-to-rows
        $.contextMenu({
            selector: `#${id}_body tr td`,
            callback: (key: string, options: { $trigger: JQuery }) => {
                const tr = options.$trigger.closest('tr');
                const row = $(`#${id}`).DataTable().row(tr);
                console.log(row);
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


export function unsuggest_element(selector: string) {
    $(selector).pulsate('destroy');
    $(selector).removeAttr('style');
}

export function suggest_element(selector: string, state_to_set: string) {
    settings.start_suggestion = state_to_set;
    $(selector).pulsate({
        color: '#e45325',   // set the color of the pulse
        reach: 20,          // how far the pulse goes in px
        speed: 1000,        // how long one pulse takes in ms
        pause: 0,           // how long the pause between pulses is in ms
        glow: true,         // if the glow should be shown too
        repeat: true,       // will repeat forever if true, if given a number will repeat for that many times
        onHover: false      // if true only pulsate if user hovers over the element
    });
}

export function suggest_element_until_click(selector: string, state_to_set: string) {
    suggest_element(selector, state_to_set);
    $(selector).click(() => {
        unsuggest_element(selector);
    });
}

export function format_asset_title_for_ui(asset: string): string {
    let symbol, str;
    if (asset === 'IOTA') {
        symbol = 'MIOTA';
    } else {
        symbol = asset;
    }

    const path = settings.ICON_MAP_LIST[symbol.toLowerCase()];
    if (path !== undefined) {
        str = `<img src="../${path}" /> ${asset}`;
    } else {
        str = ` ¤ ${asset}`;
    }
    return str;
}
