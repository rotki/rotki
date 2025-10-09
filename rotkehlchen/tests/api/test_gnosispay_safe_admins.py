from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0xaCFEb570426e260Eb930971FE528c8014f1002a0',
    '0xD501c55f42214fcC22D7Bfad845bD069D528bda1',
]])
def test_gnosis_pay_safe_admins_success(
        rotkehlchen_api_server: 'APIServer',
        gnosis_accounts: list[str],
) -> None:
    for async_query in (False, True):
        response = requests.get(
            api_url_for(rotkehlchen_api_server, 'gnosispaysafeadminsresource'),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_sync_response_with_result(response)

        assert result == {
            gnosis_accounts[0]: [
                '0x37f18A82493cdF80675fF01e58c1A1b39637cf50',
                '0xc37b40ABdB939635068d3c5f13E7faF686F03B65',
            ],
        }


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_gnosis_pay_safe_admins_no_accounts(rotkehlchen_api_server: 'APIServer') -> None:
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'gnosispaysafeadminsresource',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == {}
