function form_entry(input_addon, input_id, initial_value, placeholder, input_type) {
    let str = '<form role="form"><div class="form-group input-group">';
    if (input_addon) {
        str += '<span class="input-group-addon">'+input_addon+':</span>';
    }
    str += '<input id="'+input_id+'" class="form-control" value="'+initial_value+'"';
    if (placeholder) {
        str +=' placeholder="'+placeholder+'"';
    }
    if (input_type) {
        str += `type="${input_type}"></div>`;
    } else {
        str += 'type="text"></div>';
    }

    return str;
}

function form_text(prompt, id, rows, initial_value, placeholder) {
    let str = '<div class="form-group"><label class="form-prompt">'+prompt+'</label>';
    str += '<textarea id="'+id+'" class="form-control" rows="'+rows+'"';
    str += ' value="'+initial_value+'"';
    if (placeholder) {
        str +=' placeholder="'+placeholder+'"';
    }
    str += ' ></textarea></div>';
    return str;
}

function form_select(prompt, id, options, selected_option) {
    let str = '<div class="form-group"><label class="form-prompt">'+prompt+'</label>';
    str += '<select id="'+id+'" class="form-control" style="font-family: \'FontAwesome\', \'sans-serif\';">';

    for (let i = 0; i < options.length; i++) {
        str += '<option value="'+options[i]+'"';
        if (selected_option == options[i]) {
            str += ' selected="selected"';
        }
        str +='>'+options[i]+'</option>';
    }
    str += '</select></div>';
    return str;
}

function form_checkbox(id, prompt, checked) {
    let checkstr = 'checked';
    if (!checked) {
        checkstr = '';
    }

    return `<div class="checkbox"><label><input id="${id}" type="checkbox" ${checkstr}>${prompt}</label></div>`;
}

function form_multiselect(prompt, id, options) {
    let str = '<div class="form-group"><label class="form-prompt">'+prompt+'</label>';
    str += '<select id="'+id+'" class="form-control" multiple="multiple" style="font-family: \'FontAwesome\', \'sans-serif\';">';
    for (let i = 0; i < options.length; i++) {
        str += '<option value="'+options[i]+'">'+options[i]+'</option>';
    }
    return str;
}

function form_button(prompt, id) {
    let str = '<button id="'+id+'" type="submit" class="btn btn-default">'+prompt+'</button>';
    return str;
}

function table_html(num_columns, id) {
    let str = '<div class="row rotkehlchen-table"><table id="'+id+'_table"><thead><tr>';
    for (let i = 0; i < num_columns; i++) {
        str += '<th></th>';
    }
    str += '</tr/></thead><tfoot><tr>';
    for (let i = 0; i < num_columns; i++) {
        str += '<th></th>';
    }
    str += '</tr></tfoot><tbody id="'+id+'_table_body"></tbody></table></div>';
    return str;
}

const page_header = (text) => `<div class="row"><div class="col-lg-12"><h1 class="page-header">${text}</h1></div></div>`;

const settings_panel = (text, id) => `<div class="row"><div class="col-lg-12"><div class="panel panel-default"><div class="panel-heading">${text}</div><div id="${id}_panel_body" class="panel-body"></div></div></div></div>`;

const loading_placeholder = (id) =>
      `<div id="${id}" class=loadingtest><div class="loadingwrapper_text"></div></div>`;

const invisible_anchor = (id) => `<div id="${id}" class="invisible-anchor"></div>`;

module.exports = function() {
    this.form_entry = form_entry;
    this.form_text = form_text;
    this.form_checkbox = form_checkbox;
    this.form_select = form_select;
    this.form_multiselect = form_multiselect;
    this.form_button = form_button;
    this.table_html = table_html;
    this.page_header = page_header;
    this.settings_panel = settings_panel;
    this.loading_placeholder = loading_placeholder;
    this.invisible_anchor = invisible_anchor;
};
