import {Callback} from './model/callback';
import {format_asset_title_for_ui, reload_table_currency_val, string_capitalize} from './utils';
import {format_currency_value, settings} from './settings';
import {table_html} from './elements';
import {PlacementType} from './enums/PlacementType';
import {AssetBalance} from './model/asset-balance';
import Api = DataTables.Api;

export class AssetTable {
    private first_column_name: string;
    private id: string;
    private table?: DataTables.Api;
    private header?: string;
    private header_id?: string;
    private placement_type: PlacementType;
    private placement_id: string;
    private table_html  = '';

    /**
     * @param first_column      string         Name of the first column of the table
     * @param id                string         Id prefix for the generated table
     * @param placement_type    ANY('appendTo', 'insertAfter')    The type of placement for the table
     * @param placement_id      string         The id at which to perform placement
     * @param table_data        array          The data to populate the table with
     * @param header            OPTIONAL(string)    If given then a header with this text is prepended to the table
     * @param header_id         OPTIONAL(string)    If given then this is the id of the header
     * @param draw_cb           OPTIONAL(function) If given then the datatable has a draw callback.
     * Callback should follow the signature:
     * (id:string, editfn:optional(function), deletefn:optional(function)
     */
    constructor(
        first_column: string,
        id: string,
        placement_type: PlacementType,
        placement_id: string,
        table_data: { [asset: string]: AssetBalance },
        header?: string,
        header_id?: string,
        draw_cb?: Callback | (() => void)
    ) {
        this.first_column_name = first_column;
        this.id = id;
        this.header = header;
        this.header_id = header_id;
        this.placement_type = placement_type;
        this.placement_id = placement_id;

        this.calculate_html();
        this.place_html();
        this.populate(table_data, draw_cb);
    }

    calculate_html() {
        let str = '';
        if (this.header) {
            str += '<h3 ';
            if (this.header_id) {
                str += `id="${this.header_id}"`;
            }
            str += `>${this.header}</h3>`;
        }
        str += table_html(3, this.id);
        this.table_html = str;
    }

    place_html() {
        const str = this.table_html;
        if (this.placement_type === PlacementType.appendTo) {
            $(str).appendTo($(`#${this.placement_id}`));
        } else if (this.placement_type === PlacementType.insertAfter) {
            $(str).insertAfter(`#${this.placement_id}`);
        } else {
            throw new Error(`Invalid AssetTable construction value for placement_type: ${this.placement_type}`);
        }
    }

    format_data(original_data: { [asset: string]: AssetBalance }): AssetBalance[] {
        const data: AssetBalance[] = [];
        for (const asset in original_data) {
            if (!original_data.hasOwnProperty(asset)) {
                continue;
            }
            const assetData = original_data[asset];
            const amount = parseFloat(assetData.amount as string);
            const amountStr = amount.toFixed(settings.floating_precision);
            const value = parseFloat(assetData.usd_value as string);
            const valueStr = value.toFixed(settings.floating_precision);
            const row: AssetBalance = {[this.first_column_name]: asset, 'amount': amountStr, 'usd_value': valueStr};
            data.push(row);
        }
        return data;
    }

    populate(table_data: { [asset: string]: AssetBalance }, draw_cb?: Callback | (() => void)) {
        const data = this.format_data(table_data);
        const first_column_name = this.first_column_name;
        const init_obj: DataTables.Settings = {
            'data': data,
            'columns': [
                {
                    'data': first_column_name,
                    'title': string_capitalize(first_column_name),
                    'render': (_data: any, _type: string, row: { [key: string]: string }) => {
                        // TODO: Lefteris should fix the fiat balances query
                        // to return 'asset' instead of 'currency' at some point
                        let asset;
                        if ('currency' in row) {
                            asset = row['currency'];
                            return format_asset_title_for_ui(asset);
                        } else if ('asset' in row) {
                            asset = row['asset'];
                            return format_asset_title_for_ui(asset);
                        } else if ('account' in row) {
                            // the first column is not always an asset. In the per account
                            // table it's an account so don't add icons there
                            return row['account'];
                        }
                        throw new Error('Unknown data for asset table');
                    }
                },
                {
                    'data': 'amount',
                    'title': 'Amount'
                },
                {
                    'data': 'usd_value',
                    'title': `${settings.main_currency.ticker_symbol} value`,
                    'render': (dat: string, _type: string, row: AssetBalance) => {
                        return format_currency_value(dat, row[first_column_name] as string, row.amount as string);
                    }
                }
            ],
            'order': [[2, 'desc']]
        };
        if (draw_cb) {
            // @ts-ignore
            init_obj['drawCallback'] = draw_cb;
        }
        this.table = $(`#${this.id}_table`).DataTable(init_obj);
    }

    reload() {
        reload_table_currency_val(this.table as Api, 2);
    }

    repopulate(new_data: { [asset: string]: AssetBalance }) {
        if (this.table) {
            $(`#${this.id}_table_wrapper`).empty();
            this.table.destroy(true);
            this.place_html();
            this.populate(new_data);
        }
    }

    update_format(new_data: { [asset: string]: AssetBalance }) {
        const new_data_array = this.format_data(new_data);
        this.update(new_data_array);
    }

    update(new_data: AssetBalance[]) {

        if (!this.table) {
            throw Error('Table was undefined');
        }

        this.table.clear();
        this.table.rows.add(new_data);
        this.table.draw();
    }

}
