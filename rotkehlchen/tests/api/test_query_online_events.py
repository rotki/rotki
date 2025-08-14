import random
from http import HTTPStatus
from unittest.mock import call, patch

import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_async_response,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.types import ExternalService, Timestamp


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_refresh_gnosis_pay_and_monerium(
        rotkehlchen_api_server: APIServer,
        gnosispay_credentials: None,
        monerium_credentials: None,
        start_with_valid_premium: bool,
) -> None:
    """Test that refreshing gnosis pay and monerium data via the online events endpoint works."""
    async_query = random.choice([False, True])
    for query_type, patch_path, service, error_msg, expected_call in ((
        'gnosis_pay',
        'rotkehlchen.externalapis.gnosispay.GnosisPay.get_and_process_transactions',
        ExternalService.GNOSIS_PAY,
        'Unable to refresh Gnosis Pay data due to missing credentials',
        call(after_ts=Timestamp(0)),
    ), (
        'monerium',
        'rotkehlchen.externalapis.monerium.Monerium.get_and_process_orders',
        ExternalService.MONERIUM,
        'Unable to refresh Monerium data due to missing credentials',
        call(),
    )):
        with patch(patch_path) as mock_query_service:
            response = requests.post(
                api_url_for(rotkehlchen_api_server, 'eventsonlinequeryresource'),
                json={'async_query': async_query, 'query_type': query_type},
            )
            if not start_with_valid_premium:  # Check the error message without premium
                pretty_name = 'Gnosis Pay' if query_type == 'gnosis_pay' else 'Monerium'
                contained_in_msg = f'You can only use {pretty_name} with rotki premium'
                status_code = HTTPStatus.FORBIDDEN
                if async_query:
                    task_id = assert_ok_async_response(response)
                    response_data = wait_for_async_task(rotkehlchen_api_server, task_id)
                    assert_error_async_response(response_data, contained_in_msg, status_code)
                else:
                    assert_error_response(response, contained_in_msg, status_code)
                continue  # skip the rest of the checks without premium

            assert_proper_response_with_result(response, rotkehlchen_api_server, async_query)

        assert mock_query_service.call_count == 1
        assert mock_query_service.call_args_list == [expected_call]

        # also check the error when there aren't credentials
        rotkehlchen_api_server.rest_api.rotkehlchen.data.db.delete_external_service_credentials(services=[service])
        assert_error_response(
            response=requests.post(
                api_url_for(rotkehlchen_api_server, 'eventsonlinequeryresource'),
                json={'async_query': False, 'query_type': query_type},
            ),
            contained_in_msg=error_msg,
            status_code=HTTPStatus.CONFLICT,
        )
