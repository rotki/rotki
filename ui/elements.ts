export function form_entry(
    input_addon: string, 
    input_id: string, 
    initial_value: string | number, 
    placeholder: string, 
    input_type?: string
): string {
    let str = '<div class="form-group input-group">';
    if (input_addon) {
        str += '<span class="input-group-addon">' + input_addon + ':</span>';
    }
    str += '<input id="' + input_id + '" class="form-control" value="' + initial_value + '"';
    if (placeholder) {
        str += ' placeholder="' + placeholder + '"';
    }
    if (input_type) {
        str += `type="${input_type}"></div>`;
    } else {
        str += 'type="text"></div>';
    }

    return str;
}

export function form_text(
    prompt: string, 
    id: string, 
    rows: number, 
    initial_value: string, 
    placeholder: string
): string {
    let str = '<div class="form-group"><label class="form-prompt">' + prompt + '</label>';
    str += '<textarea id="' + id + '" class="form-control" rows="' + rows + '"';
    str += ' value="' + initial_value + '"';
    if (placeholder) {
        str += ' placeholder="' + placeholder + '"';
    }
    str += ' ></textarea></div>';
    return str;
}

export function form_select(
    prompt: string, 
    id: string, 
    options: Array<string>, 
    selected_option: string
): string {
    let str = '<div class="form-group"><label class="form-prompt">' + prompt + '</label>';
    str += '<select id="' + id + '" class="form-control" style="font-family: \'FontAwesome\', \'sans-serif\';">';

    for (let i = 0; i < options.length; i++) {
        str += '<option value="' + options[i] + '"';
        if (selected_option === options[i]) {
            str += ' selected="selected"';
        }
        str += '>' + options[i] + '</option>';
    }
    str += '</select></div>';
    return str;
}

export function form_checkbox(
    id: string,
    prompt: string, 
    checked: boolean
): string {
    let checkstr = 'checked';
    if (!checked) {
        checkstr = '';
    }
    return `<div class="checkbox"><label><input id="${id}" type="checkbox" ${checkstr}>${prompt}</label></div>`;
}

export function form_radio(
    prompt: string, 
    id: string, 
    options: Array<string>, 
    selected_option: string
): string {
    let str = '<div class="form-group"><label class="form-prompt">' + prompt + '</label><div class="row">';
    let colnum = Math.floor(12 / options.length);
    for (let i = 0; i < options.length; i++) {
        str += '<div class="col-sm-' + colnum + '"><input type="radio" name="' + id + '" value="' + options[i] + '"';
        if (selected_option === options[i]) {
            str += ' checked="checked"';
        }
        str += '>' + options[i] + '</input></div>';
    }
    str += '</div></div>';
    return str;
}

export function form_multiselect(
    prompt: string, 
    id: string, 
    options: any
): string {
    let str = '<div class="form-group"><label class="form-prompt">' + prompt + '</label>';
    // tslint:disable-next-line:max-line-length
    str += '<select id="' + id + '" class="form-control" multiple="multiple" style="font-family: \'FontAwesome\', \'sans-serif\';">';
    for (let i = 0; i < options.length; i++) {
        str += '<option value="' + options[i] + '">' + options[i] + '</option>';
    }
    return str;
}

export function form_button(
    prompt: string, 
    id: string
): string {
    let str = '<button id="' + id + '" type="submit" class="btn btn-default">' + prompt + '</button>';
    return str;
}

export function table_html(
    num_columns: number, 
    id: string
): string {
    let str = '<div class="row rotkehlchen-table"><table id="' + id + '_table"><thead><tr>';
    for (let i = 0; i < num_columns; i++) {
        str += '<th></th>';
    }
    str += '</tr/></thead><tfoot><tr>';
    for (let i = 0; i < num_columns; i++) {
        str += '<th></th>';
    }
    str += '</tr></tfoot><tbody id="' + id + '_table_body"></tbody></table></div>';
    return str;
}

export const page_header = (text: string) => 
`<div class="row"><div class="col-lg-12"><h1 class="page-header">${text}</h1></div></div>`;

export const settings_panel = (text: string, id: string) => 
`<div class="row">
    <div class="col-lg-12"><div class="panel panel-default">
        <div class="panel-heading">${text}</div><div id="${id}_panel_body" class="panel-body">
        </div>
    </div>
  </div>
</div>`;

export const loading_placeholder = (id) =>
      `<div id="${id}" class=loadingtest><div class="loadingwrapper_text"></div></div>`;

export const invisible_anchor = (id) => `<div id="${id}" class="invisible-anchor"></div>`;
