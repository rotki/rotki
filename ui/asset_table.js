var settings = require("./settings.js")();
require("./elements.js");
require("./utils.js");

function format_table_data(original_data) {
    let data = [];
    for (var asset in original_data) {
        if(original_data.hasOwnProperty(asset)) {
            let amount = parseFloat(original_data[asset]['amount']);
            amount = amount.toFixed(settings.floating_precision);
            let value = parseFloat(original_data[asset]['usd_value']);
            value = value.toFixed(settings.floating_precision);
            data.push({'asset': asset, 'amount': amount, 'usd_value': value});
        }
    }
    return data;
}

function populate_asset_table(table_data, id) {
    let data = format_table_data(table_data);
    let table = $('#'+id).DataTable({
        "data": data,
        "columns": [
            {"data": "asset", "title": "Asset"},
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
    });
    return table;
}

function create_asset_table(id, append_to_id, table_data) {
    let str = table_html(3, id);
    $(str).appendTo($('#'+append_to_id));
    return populate_asset_table(table_data, id+'_table');
}

function reload_asset_table(table) {
    reload_table_currency_val_if_existing(table, 2);
}

module.exports = function() {
    this.create_asset_table = create_asset_table;
    this.populate_asset_table = populate_asset_table;
    this.reload_asset_table = reload_asset_table;
};
