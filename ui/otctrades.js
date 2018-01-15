var settings = require("./settings.js")();
require("./elements.js")();

// TODO: Check this for an example without png images but font-awesome instead:
// http://live.datatables.net/bihawepu/1/edit
// Formatting function for row details - modify as you need
function format (d) {
    // `d` is the original data object for the row
    return '<table cellpadding="5" cellspacing="0" border="0" style="padding-left:50px;">'+
        '<tr>'+
        '<td>Extra Info</td>'+
        '<td>'+d.notes+'</td>'+
        '</tr>'+
        '<tr>'+
        '<td>Links:</td>'+
        '<td>'+d.link+'</td>'+
        '</tr>'+
        '<tr>'+
        '<td>Fee:</td>'+
        '<td>'+d.fee+' '+d.fee_currency+'</td>'+
        '</tr>'+
        '</table>';
}

function create_otctrades_table() {
    var str = '<div class="row"><div class="col-lg-12"><h1 class=page-header">OTC Trades List</h1></div></div>';
    str += '<div class="row"><table id="table_otctrades"><thead><tr><th></th><th>Pair</th><th>Type</th><th>Amount</th><th>Rate</th><th>Time</th></tr/></thead><tbody id="table_otctrades_body"></tbody></table></div>';
    $(str).appendTo($('#page-wrapper'));
    client.invoke("query_otctrades", (error, result) => {
        if (error || result == null) {
            console.log("Error at querying OTC trades: " + error);
        } else {
            for (let i = 0; i < result.length; i++) {
                // let str = '<tr><td>'+result[i].pair+'</td><td>'+result[i].type+'</td/><td>'+result[i].rate+'</td><td>'+(new Date(result[i].time * 1000)).toGMTString()+'</td></tr>';
                let str = '<tr><td></td><td></td/><td></td><td></td></tr>';
                $(str).appendTo($('#table_otctrades_body'));
            }
            var table = $('#table_otctrades').DataTable({
                "data": result,
                "columns": [
                    {
                        "className": 'details-control',
                        "orderable": false,
                        "data": null,
                        "defaultContent": '',
                        "render": function () {
                         return '<i class="fa fa-plus-square" aria-hidden="true"></i>';
                        },
                        width:"15px"
                    },
                    { "data": "pair" },
                    { "data": "type" },
                    { "data": "amount" },
                    { "data": "rate" },
                    {
                        "render": function (data, type, row) {
                            return (new Date(data * 1000)).toGMTString();
                        },
                        "data": "timestamp"
                    },
                ],
                "order": [[5, 'asc']]
            });
            // Add event listener for opening and closing details
            $('#table_otctrades tbody').on('click', 'td.details-control', function () {
                var tr = $(this).closest('tr');
                var tdi = tr.find("i.fa");
                var row = table.row(tr);

                if (row.child.isShown()) {
                    // This row is already open - close it
                    row.child.hide();
                    tr.removeClass('shown');
                    tdi.first().removeClass('fa-minus-square');
                    tdi.first().addClass('fa-plus-square');
                }
                else {
                    // Open this row
                    row.child(format(row.data())).show();
                    tr.addClass('shown');
                    tdi.first().removeClass('fa-plus-square');
                    tdi.first().addClass('fa-minus-square');
                }
            } );
        }
    });
}

function create_otctrades_ui() {
    var str = '<div class="row"><div class="col-lg-12"><h1 class="page-header">OTC Trades Management</h1></div></div>';
    str += '<div class="row"><div class="col-lg-12"><div class="panel panel-default"><div class="panel-heading">Register New Trade</div><div class="panel-body"></div></div></div></div>';
    $('#page-wrapper').html(str);

    str = form_entry('time', 'otc_time', '', 'Time that the trade took place');
    str += form_entry('pair', 'otc_pair', '', 'Asset pair for the trade');
    str += form_select('Trade Type', 'otc_type', ['buy', 'sell']);
    str += form_entry('amount', 'otc_amount', '', 'Amount bought/sold');
    str += form_entry('rate', 'otc_rate', '', 'Rate of the trade');
    str += form_entry('fee', 'otc_fee', '', 'Fee if any that the trade occured');
    str += form_entry('link', 'otc_link', '', 'A link to the trade. e.g.: in an explorer');
    str += form_text('Enter additional notes', 'otc_notes', 3, '', 'Additional notes to store for the trade');
    str += form_button('Save', 'otctradesubmit');
    $(str).appendTo($('.panel-body'));

    create_otctrades_table();
}

function add_listeners() {
    $('#otctradesubmit').click(function(event) {
        event.preventDefault();
    });
    $('#otc_time').datepicker();
}

function create_or_reload_otctrades() {
    change_location('otctrades');
    if (!settings.page_otctrades) {
        console.log("At create/reload otctrades, with a null page index");
        create_otctrades_ui();
    } else {
        console.log("At create/reload otctrades, with a Populated page index");
        $('#page-wrapper').html(settings.page_otctrades);
    }
    add_listeners();
}

module.exports = function() {
    this.create_or_reload_otctrades = create_or_reload_otctrades;
};
