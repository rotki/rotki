import {page_header} from './elements';
import {service} from './rotkehlchen_service';
import {showError, showInfo, prompt_filepath_select_async} from './utils';

export function create_dataimport_ui() {
    let str = page_header('Import Data');
    str += `<div><p>You can manually import data from the services below by clicking on the respective </p></div>`;
    str += `<div><img id="dataimport_cointrackinginfo"src="images/cointracking_info.png"></img></div>`;
    $('#page-wrapper').html(str);
}

export function add_dataimport_listeners() {
    $('#dataimport_cointrackinginfo').click(cointracking_info_import);
}

function cointracking_info_import(event: JQuery.Event) {
    event.preventDefault();
    prompt_filepath_select_async('file', (files: string[]) => {
        if (files === undefined) {
            return;
        }
        const file = files[0];
        service.import_data_from('cointracking_info', file).then(() => {
            showInfo('Success', 'Data imported from cointracking.info export file succesfuly');
        }).catch((reason: Error) => {
            showError('Failed to import data from cointracking.info export file', reason.message);
        });
    });
}
