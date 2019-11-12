import {page_header} from './elements';
import {settings} from './settings';
import {service} from './rotkehlchen_service';
import {showError} from './utils';

export function create_statistics_ui() {
    let str = page_header('Statistics');
    if (!settings.has_premium) {
        str += `<div><p>No premium subscription detected. Statistics are only available
to premium users. To get a premium subscription please visit our
<a href="https://rotki.com/products" target="_blank">website</a>.</p></div>`;
        $('#page-wrapper').html(str);
    } else {
        service.query_statistics_renderer().then(result => {
            eval(result);
        }).catch(reason => {
            showError('Error at querying statistics renderer', reason.message);
        });
    }
}

export function add_statistics_listeners() {
}
