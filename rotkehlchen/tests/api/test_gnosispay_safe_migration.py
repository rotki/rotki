from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.gnosispay import GNOSIS_PAY_SAFE_MIGRATION_ID
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_gnosis_pay_safe_migration(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    migration_data = {
        'migration_id': GNOSIS_PAY_SAFE_MIGRATION_ID,
        'untracked_addresses': [{
            'address': '0x2222222222222222222222222222222222222222',
            'type': 'new',
        }],
    }
    gnosis_pay = MagicMock()
    gnosis_pay.get_safe_migration_data.return_value = migration_data
    with (
        patch('rotkehlchen.api.v1.resources.has_premium_capability', return_value=True),
        patch('rotkehlchen.api.services.integrations.init_gnosis_pay', return_value=gnosis_pay),
    ):
        for async_query in (False, True):
            response = requests.get(
                api_url_for(rotkehlchen_api_server, 'gnosispaysafemigrationresource'),
                json={'async_query': async_query},
            )
            if async_query:
                task_id = assert_ok_async_response(response)
                outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
                assert outcome['message'] == ''
                result = outcome['result']
            else:
                result = assert_proper_sync_response_with_result(response)

            assert result == migration_data


@pytest.mark.parametrize(('gnosis_pay', 'message'), [
    (None, 'Gnosis Pay credentials are not configured'),
    (MagicMock(get_safe_migration_data=MagicMock(side_effect=RemoteError('API unavailable'))), 'API unavailable'),  # noqa: E501
])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_gnosis_pay_safe_migration_error(
        rotkehlchen_api_server: 'APIServer',
        gnosis_pay: MagicMock | None,
        message: str,
) -> None:
    with (
        patch('rotkehlchen.api.v1.resources.has_premium_capability', return_value=True),
        patch('rotkehlchen.api.services.integrations.init_gnosis_pay', return_value=gnosis_pay),
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'gnosispaysafemigrationresource',
        ))

    assert_error_response(
        response=response,
        contained_in_msg=message,
        status_code=HTTPStatus.CONFLICT,
    )
