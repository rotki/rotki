import { format_currency_value, settings } from './settings';
import { table_html } from './elements';
import { reload_table_currency_val, string_capitalize, throw_with_trace } from './utils';


export class AssetTable {

    first_column_name: string;
    id: string;
    table: DataTables.Api;

    /**
     * @param first_column      string         Name of the first column of the table
     * @param id                string         Id prefix for the generated table
     * @param placement_type    ANY('appendTo', 'insertAfter')    The type of placement for the table
     * @param placement_id      string         The id at which to perform placement
     * @param table_data        array          The data to populate the tablewith
     * @param header            OPTIONAL(string)    If given then a header with this text is prepended to the table
     * @parama header_id        OPTIONAL(string)    If given then this is the id of the header
     * @param draw_cb            OPTIONAL(function) If given then the datatable has a draw callback. Callack should follow the signature: (id:string, editfn:optional(function), deletefn:optional(function)
     */
    constructor(
        first_column: string,
        id: string,
        placement_type: any,
        placement_id: string,
        table_data: Array<any>,
        header?: string,
        header_id?: string,
        draw_cb?: any
    ) {
        this.first_column_name = first_column;
        this.id = id;
        let str = '';
        if (header) {
            str += '<h3 ';
            if (header_id) {
                str += `id="${header_id}"`;
            }
            str += `>${header}</h3>`;
        }
        str += table_html(3, id);
        if (placement_type === 'appendTo') {
            $(str).appendTo($('#' + placement_id));
        } else if (placement_type === 'insertAfter') {
            $(str).insertAfter('#' + placement_id);
        } else {
            let err = new Error();
            throw_with_trace('Invalid AssetTable construction value for placement_type: ' + placement_type);
        }
        this.populate(table_data, draw_cb);
    }
    format_data(original_data: any): Array<any> {
        let data = [];
        for (let asset in original_data) {
            if (original_data.hasOwnProperty(asset)) {
                const amount = 
                parseFloat(original_data[asset]['amount'])
                .toFixed(settings.floating_precision);
                let value = 
                parseFloat(original_data[asset]['usd_value'])
                .toFixed(settings.floating_precision);
                let row = {[this.first_column_name]: asset, 'amount': amount, 'usd_value': value};
                data.push(row);
            }
        }
        return data;
    }
    
    populate(table_data: any, draw_cb: any): void {
        let data = this.format_data(table_data);
        let first_column_name = this.first_column_name;
        let init_obj = {
            'data': data,
            'columns': [
                {'data': first_column_name, 'title': string_capitalize(first_column_name)},
                {'data': 'amount', 'title': 'Amount'},
                {
                    'data': 'usd_value',
                    'title': settings.main_currency.ticker_symbol + ' value',
                    'render': function (data: any , type: any, row: any) {
                        return format_currency_value(data, row[first_column_name], row['amount']);
                    }
                }
            ],
            'order': [[2, 'desc']]
        };
        if (draw_cb) {
            init_obj['drawCallback'] = draw_cb;
        }
        let table = $('#' + this.id + '_table').DataTable(init_obj);
        this.table = table;
    }
    
    reload() {
        reload_table_currency_val(this.table, 2);
    }
    
    update_format(new_data: Array<any>) {
        new_data = this.format_data(new_data);
        this.update(new_data);
    }
    
    update(new_data: Array<any>) {
        this.table.clear();
        this.table.rows.add(new_data);
        this.table.draw();
    }
}