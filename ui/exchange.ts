
import { page_header } from './elements';
import { total_balances_get } from './balances_table';
import { AssetTable } from './asset_table';
import { create_task } from './monitor';
import { change_location } from './navigation';
import { pages } from './settings';
import { PlacementType } from './enums/PlacementType';
import { AsyncQueryResult } from './model/balance-result';
import { client } from './rotkehlchen_service';

const SAVED_TABLES: { [name: string]: AssetTable } = {};

export function query_exchange_balances_async(name: string, is_balance_task: boolean) {
    client.invoke('query_exchange_balances_async', name, (error: Error, res: AsyncQueryResult) => {
        if (error || res == null) {
            console.log(`Error at querying exchange ${name} balances: ${error}`);
            return;
        }
        console.log(`Query ${name} returned task id ${res.task_id}`);
        create_task(
            res.task_id,
            'query_exchange_balances',
            `Query ${name} Balances`,
            is_balance_task,
            true
        );
    });
}

function create_exchange_table(name: string) {
    const str = page_header(name);
    $('#page-wrapper').html(str);
    const table = SAVED_TABLES[name];
    if (!table) {
        const data = total_balances_get()[name];
        console.log(`CREATING TABLE FOR ${name}`);
        SAVED_TABLES[name] = new AssetTable('asset', name, PlacementType.appendTo, 'page-wrapper', data);
        pages.page_exchange[name] = $('#page-wrapper').html();
    }
}

export function reload_exchange_tables_if_existing() {
    for (const name in SAVED_TABLES) {
        if (SAVED_TABLES.hasOwnProperty(name)) {
            const table = SAVED_TABLES[name];
            table.reload();
        }
    }
}

export function create_or_reload_exchange(name: string) {
    change_location(`exchange_${name}`);
    if (!pages.page_exchange[name]) {
        console.log('At create/reload exchange, with a null page index');
        create_exchange_table(name);
    } else {
        console.log('At create/reload exchange, with a Populated page index');
        $('#page-wrapper').html(pages.page_exchange[name]);
    }
}
