import { settings } from './settings';
import { page_header } from './elements';
import { change_location } from './navigation';
import client from './zerorpc_client';
import { total_balances_get } from './balances_table';
import { create_task } from './monitor';
import { AssetTable } from './asset_table';
let SAVED_TABLES = {};

export function query_exchange_balances_async(name: string, is_balance_task: boolean) {
    client.invoke('query_exchange_balances_async', name, (error, res) => {
        if (error || res == null) {
            console.log('Error at querying exchange ' + name + ' balances: ' + error);
            return;
        }
        console.log('Query ' + name + '  returned task id ' + res['task_id']);
        create_task(
            res['task_id'],
            'query_exchange_balances',
            'Query ' + name + ' Balances',
            is_balance_task,
            true
        );
    });
}

function create_exchange_table(name: string) {
    let str = page_header(name);
    $('#page-wrapper').html(str);
    let table = SAVED_TABLES[name];
    if (!table) {
        let data = total_balances_get()[name];
        console.log('CREATING TABLE FOR ' + name);
        SAVED_TABLES[name] = new AssetTable('asset', name, 'appendTo', 'page-wrapper', data);
        settings.page_exchange[name] = $('#page-wrapper').html();
    }
}

export function reload_exchange_tables_if_existing() {
    for (let name in SAVED_TABLES) {
        if (SAVED_TABLES.hasOwnProperty(name)) {
            let table = SAVED_TABLES[name];
            table.reload();
        }
    }
}

export function create_or_reload_exchange(name: string) {
    change_location('exchange_' + name);
    if (!settings.page_exchange[name]) {
        console.log('At create/reload exchange, with a null page index');
        create_exchange_table(name);
    } else {
        console.log('At create/reload exchange, with a Populated page index');
        $('#page-wrapper').html(settings.page_exchange[name]);
    }
}

