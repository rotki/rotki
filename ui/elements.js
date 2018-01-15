function form_entry(input_addon, input_id, initial_value, placeholder) {
    let str = '<div class="row"><form role="form"><div class="form-group input-group">';
    if (input_addon) {
        str += '<span class="input-group-addon">'+input_addon+':</span>';
    }
    str += '<input id="'+input_id+'" class="form-control" value="'+initial_value+'"';
    if (placeholder) {
        str +=' placeholder="'+placeholder+'"';
    }
    str += 'type="text"></div></div>';

    return str;
}

function form_text(prompt, id, rows, initial_value, placeholder) {
    let str = '<div class="form-group"><label>'+prompt+'</label>';
    str += '<textarea id="'+id+'" class="form-control" rows="'+rows+'"';
    str += ' value="'+initial_value+'"';
    if (placeholder) {
        str +=' placeholder="'+placeholder+'"';
    }
    str += ' ></textarea></div>';
    return str;
}

function form_select(prompt, id, options) {
    let str = '<div class="form-group"><label>'+prompt+'</label>';
    str += '<select id="'+id+'" class="form-control" style="font-family: \'FontAwesome\', \'sans-serif\';">';

    for (let i = 0; i < options.length; i++) {
        str += '<option value="'+options[i]+'">'+options[i]+'</option>';
    }
    str += '</select></div>';
    return str;
}

function form_button(prompt, id) {
    let str = '<button id="'+id+'" type="submit" class="btn btn-default">'+prompt+'</button>';
    return str;
}

module.exports = function() {
    this.form_entry = form_entry;
    this.form_text = form_text;
    this.form_select = form_select;
    this.form_button = form_button;
};
