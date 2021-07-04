from http import HTTPStatus

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)


@pytest.mark.parametrize('start_with_valid_premium', [True, False])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_get_grant_events(rotkehlchen_api_server, start_with_valid_premium):
    grant_id = 149  # rotki grant
    json_data = {
        'from_timestamp': 1622516400,  # 3 hours hours after midnight 01/06/2021
        'to_timestamp': 1623294000,  # 3 hours hours after midnight 10/06/2021
        'grant_id': grant_id,
    }
    response = requests.post(api_url_for(
        rotkehlchen_api_server,
        'gitcoineventsresource',
    ), json=json_data)
    if start_with_valid_premium is False:
        assert_error_response(
            response=response,
            contained_in_msg='does not have a premium subscription',
            status_code=HTTPStatus.CONFLICT,
        )
        return

    outcome = assert_proper_response_with_result(response)
    assert len(outcome) == 36
    assert outcome[:3] == [{
        'amount': '0.000475',
        'asset': 'ETH',
        'clr_round': None,
        'grant_id': grant_id,
        'timestamp': 1622518496,
        'tx_id': '8ee8bfe2d07a0a9192549725aa3d3dcf78b7913a6bf187895c2510fb058ed314',
        'tx_type': 'zksync',
        'usd_value': '1.25121175',
    }, {
        'amount': '0.000475',
        'asset': 'ETH',
        'clr_round': None,
        'grant_id': grant_id,
        'timestamp': 1622603572,
        'tx_id': 'b75d5a7b7073a8d306492641955106145a16728250243c6ed86c205857b75807',
        'tx_type': 'zksync',
        'usd_value': '1.28526450',
    }, {
        'amount': '0.095',
        'asset': 'ETH',
        'clr_round': None,
        'grant_id': grant_id,
        'timestamp': 1622613547,
        'tx_id': '0x6956dd7d09fa26dd1bcf8e3dfd430fa8faeb30ec47f122dec125b5fc9d1bdca8',
        'tx_type': 'ethereum',
        'usd_value': '257.05290',
    }]
    assert outcome[-1] == {
        'amount': '0.95',
        'asset': '_ceth_0x6B175474E89094C44Da98b954EedeAC495271d0F',
        'clr_round': None,
        'grant_id': grant_id,
        'timestamp': 1623250357,
        'tx_id': 'e2e2d8f24696a8dacbb5edceae718ef6b29a59123ed6e1d663ef9159c231b361',
        'tx_type': 'zksync',
        'usd_value': '0.9499999999999998000000000000',
    }
