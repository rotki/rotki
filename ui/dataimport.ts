import {page_header} from './elements';
import {service} from './rotkehlchen_service';
import {showError, showInfo, prompt_filepath_select_async} from './utils';

export function create_dataimport_ui() {
    let str = page_header('Import Data');
    str += `<div><p>You can manually import data from the services below by clicking on the respective logo</p></div><br />`;
    str += `<h3>Cointracking.info</h3><div><p>Important notes for importing data from cointracking's CSV exports.
<ul><li>Trades/deposits/withdrawals from Cointracking do not include fees.</li>
<li>All timestamps are rounded up to the minute. That is extremely innacurate for fast paced trading.</li>
<li>All trades imported from Cointracking will always be considered as buys due to the way the data are represented.</li>
<li>ETH Transactions are treated as deposits/withdrawals so they are not imported in Rotkehlchen.
To import ETH transactions simply input your accounts in user settings and they
will be imported automatically for you.</li>
</ul>
For the above reasons it's preferred to directly connect your exchanges in order to
import data from there. If you do not do that a lot of accuracy is lost.
</p><img class="importdata-button" id="dataimport_cointrackinginfo"src="images/cointracking_info.png"></img></div>`;
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
