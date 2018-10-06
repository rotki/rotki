import { page_header } from './elements';
import { total_balances_get } from './balances_table';
import { AssetTable } from './asset_table';
import { create_task } from './monitor';
import { change_location } from './navigation';
import { pages } from './settings';
import { PlacementType } from './enums/PlacementType';
import { service } from './rotkehlchen_service';

let SAVED_TABLES: { [name: string]: AssetTable } = {};

export function query_exchange_balances_async(name: string, is_balance_task: boolean) {
    service.query_exchange_balances_async(name).then(result => {
        console.log(`Query ${name} returned task id ${result.task_id}`);
        create_task(
            result.task_id,
            'query_exchange_balances_async',
            `Query ${name} Balances`,
            is_balance_task,
            true
        );
    }).catch(reason => {
        console.log(`Error at querying exchange ${name} balances: ${reason}`);
    });
}

function create_exchange_table(name: string) {
    const str = page_header(name);
    const $page_wrapper = $('#page-wrapper');
    $page_wrapper.html(str);
    pages.page_exchange[name] = $page_wrapper.html();
    const table = SAVED_TABLES[name];
    if (!table) {
        const data = total_balances_get()[name];
        console.log(`CREATING TABLE FOR ${name}`);
        SAVED_TABLES[name] = new AssetTable('asset', name, PlacementType.appendTo, 'page-wrapper', data);
    }
}

export function reload_exchange_table_if_existing(name: string) {
    if (SAVED_TABLES.hasOwnProperty(name)) {
        const table = SAVED_TABLES[name];
        const data = total_balances_get()[name];
        table.repopulate(data);
        table.reload();
    }
}

export function reset_exchange_tables() {
    SAVED_TABLES = {};
}

export function create_or_reload_exchange(name: string) {
    change_location(`exchange_${name}`);
    if (!pages.page_exchange[name]) {
        console.log('At create/reload exchange, with a null page index');
        create_exchange_table(name);
    } else {
        console.log('At create/reload exchange, with a Populated page index');
        $('#page-wrapper').html(pages.page_exchange[name]);
        reload_exchange_table_if_existing(name);
    }
}
