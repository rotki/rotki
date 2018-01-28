var settings = require("./settings.js")();
require("./elements.js");
require("./utils.js");

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
function AssetTable(
    first_column,
    id,
    placement_type,
    placement_id,
    table_data,
    header,
    header_id,
    draw_cb) {
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
    if (placement_type == 'appendTo') {
        $(str).appendTo($('#'+placement_id));
    } else if (placement_type == 'insertAfter') {
        $(str).insertAfter('#'+placement_id);
    } else {
        var err = new Error();
        let stack = err.stack;
        throw_with_trace('Invalid AssetTable construction value for placement_type: ' + placement_type);
    }
    this.populate(table_data, draw_cb);
}

AssetTable.prototype.format_data =  function(original_data) {
    let data = [];
    for (var asset in original_data) {
        if(original_data.hasOwnProperty(asset)) {
            let amount = parseFloat(original_data[asset]['amount']);
            amount = amount.toFixed(settings.floating_precision);
            let value = parseFloat(original_data[asset]['usd_value']);
            value = value.toFixed(settings.floating_precision);
            let row = {[this.first_column_name]: asset, 'amount': amount, 'usd_value': value};
            data.push(row);
        }
    }
    return data;
};

AssetTable.prototype.populate = function (table_data, draw_cb) {
    let data = this.format_data(table_data);
    let init_obj = {
        "data": data,
        "columns": [
            {"data": this.first_column_name, "title": string_capitalize(this.first_column_name)},
            {"data": "amount", "title": "Amount"},
            {
                "data": 'usd_value',
                "title": settings.main_currency.ticker_symbol + ' value',
                "render": function (data, type, row) {
                    return format_currency_value(data);
                }
            }
        ],
        "order": [[2, 'desc']]
    };
    if (draw_cb) {
        init_obj['drawCallback'] = draw_cb;
    }
    let table = $('#'+this.id+'_table').DataTable(init_obj);
    this.table = table;
};

AssetTable.prototype.reload = function () {
    reload_table_currency_val(this.table, 2);
};

AssetTable.prototype.update_format = function(new_data) {
    new_data = this.format_data(new_data);
    this.update(new_data);
};

AssetTable.prototype.update = function (new_data) {
    this.table.clear();
    this.table.rows.add(new_data);
    this.table.draw();
};

module.exports = function() {
    this.AssetTable = AssetTable;
};
