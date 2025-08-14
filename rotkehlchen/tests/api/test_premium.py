import json
from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import patch

import machineid
import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import create_patched_requests_get_for_premium

CURRENT_DEVICE_ID = machineid.hashed_id('yabirgb')


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_db(rotkehlchen_api_server: APIServer) -> None:
    """Just a smoke test that the api works fine. Would have prevented:
    https://github.com/rotki/rotki/issues/6524.

    We don't test the actual upload here, as the various scenarios are tested in
    tests/integration/test_premium.py
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    patches = [patch.object(
        rotki.premium.session,
        verb,
        return_value=MockResponse(200, '{}'),
    ) for verb in ('put', 'post')]
    patches.append(create_patched_requests_get_for_premium(
        session=rotki.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=b'',
        metadata_data_size=9999999999,
        saved_data=b'foo',
    ))

    with ExitStack() as stack:
        [stack.enter_context(patch) for patch in patches]  # pylint: disable=expression-not-assigned
        response = requests.put(api_url_for(
            rotkehlchen_api_server,  # testing normal flow works fine
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'upload'})
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert result['message'] == ''
        assert result['result'] is True

        response = requests.put(api_url_for(
            rotkehlchen_api_server,  # test for invalid action arg
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'invalid_action'})
        assert_error_response(response, contained_in_msg='Must be one of: upload, download')


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_pull_db(rotkehlchen_api_server: APIServer) -> None:
    """Just a smoke test that the api works fine for this endpoint.

    Actual functionality tested in tests/integration/test_premium.py
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    patches = [patch.object(
        rotki.premium.session,
        verb,
        return_value=MockResponse(200, '{}'),
    ) for verb in ('put', 'post')]
    patches.extend((
        create_patched_requests_get_for_premium(
            session=rotki.premium.session,
            metadata_last_modify_ts=0,
            metadata_data_hash=b'',
            metadata_data_size=9999999999,
            saved_data=b'foo',
        ), patch.object(
            rotki.premium_sync_manager.data,
            'decompress_and_decrypt_db',
            return_value=None,
        )))

    with ExitStack() as stack:
        [stack.enter_context(patch) for patch in patches]  # pylint: disable=expression-not-assigned
        response = requests.put(api_url_for(
            rotkehlchen_api_server,  # testing normal flow works fine
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'download'})
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert result['message'] == ''
        assert result['result'] is True


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('username', ['yabirgb'])
def test_get_premium_devices(rotkehlchen_api_server: APIServer) -> None:
    """Test the GET /premium/devices endpoint with mocked external requests."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    devices_data = {
        'devices': [
            {
                'device_name': 'laptop',
                'user': 'yabirgb',
                'device_identifier': '21312312',
            },
            {
                'device_name': 'desktop',
                'user': 'yabirgb',
                'device_identifier': CURRENT_DEVICE_ID,
            },
        ],
        'current_device_id': CURRENT_DEVICE_ID,
        'limit': 3,
    }

    with patch.object(  # mock the external request
        rotki.premium.session,
        'get',
        return_value=MockResponse(200, json.dumps(devices_data)),
    ) as mock_get:
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'premiumdevicesresource',
        ))
        result = assert_proper_sync_response_with_result(response)
        assert result == devices_data

        # verify the external request was made correctly
        mock_get.assert_called_once()


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_premium_devices_error(rotkehlchen_api_server: APIServer) -> None:
    """Test the GET /premium/devices endpoint with external request error."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    # Mock external request error
    with patch.object(
        rotki.premium.session,
        'get',
        side_effect=requests.exceptions.RequestException('Network error'),
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'premiumdevicesresource',
        ))
        assert_error_response(
            response=response,
            status_code=HTTPStatus.CONFLICT,
            contained_in_msg='Network error',
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_delete_premium_device(rotkehlchen_api_server: APIServer) -> None:
    """Test the DELETE /premium/devices endpoint with mocked external requests."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    with patch.object(  # mock the external request
        rotki.premium.session,
        'delete',
        return_value=MockResponse(200, '{}'),
    ) as mock_delete:
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'premiumdevicesresource'),
            json={'device_identifier': '21312312'},
        )
        result = assert_proper_sync_response_with_result(response)
        assert result is True

        # verify the external request was made correctly
        mock_delete.assert_called_once()


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_delete_premium_device_error(rotkehlchen_api_server: APIServer) -> None:
    """Test the DELETE /premium/devices endpoint with external request error."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    with patch.object(   # mock external request error
        rotki.premium.session,
        'delete',
        side_effect=requests.exceptions.RequestException('Network error'),
    ):
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'premiumdevicesresource'),
            json={'device_identifier': '21312312'},
        )
        assert_error_response(
            response=response,
            status_code=HTTPStatus.BAD_GATEWAY,
            contained_in_msg='Network error',
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_authenticate_device_race_condition(rotkehlchen_api_server: APIServer) -> None:
    """Test device authentication handles race condition when
     device is registered by another process."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    # mock the check endpoint to return NOT_FOUND (device not registered)
    check_response = MockResponse(HTTPStatus.NOT_FOUND, '{}')

    # mock the registration endpoint to return 409
    # (simulating race condition where device was registered by another process)
    register_response = MockResponse(
        HTTPStatus.CONFLICT,
        '{"error": "Device with this identifier already exists"}',
    )
    register_response.url = 'https://test.com'  # Add missing url attribute

    with (
        patch.object(rotki.premium.session, 'post', return_value=check_response),
        patch.object(rotki.premium.session, 'put', return_value=register_response),
    ):
        # This should complete successfully despite the 409 error (race condition handled)
        rotki.premium.authenticate_device()  # Should not raise an exception


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_edit_premium_device(rotkehlchen_api_server: APIServer, caplog: pytest.LogCaptureFixture) -> None:  # noqa: E501
    """Test the PATCH /premium/devices endpoint with both success and error cases."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    for patch_response, is_error in [
        (MockResponse(200, '{}'), False),
        (MockResponse(409, 'Network issue'), True),
    ]:
        with patch.object(
            rotki.premium.session,
            'patch',
            return_value=patch_response,
        ) as mock_patch:
            response = requests.patch(
                api_url_for(rotkehlchen_api_server, 'premiumdevicesresource'),
                json={
                    'device_identifier': 'device_abc',
                    'device_name': 'new name',
                },
            )
            if is_error:
                assert_error_response(
                    response=response,
                    status_code=HTTPStatus.CONFLICT,
                    contained_in_msg='Failed to contact rotki server.',
                )
                assert 'Network issue' in caplog.text
            else:
                assert assert_proper_sync_response_with_result(response)

            mock_patch.assert_called_once()


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('username', ['yabirgb'])
def test_delete_current_device_fails(rotkehlchen_api_server: APIServer) -> None:
    """Test that deleting the current device returns an error."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None

    with patch.object(
        target=rotki.premium.session,
        attribute='delete',
        return_value=MockResponse(200, '{}'),
    ) as mock_delete:
        response = requests.delete(
            api_url_for(rotkehlchen_api_server, 'premiumdevicesresource'),
            json={'device_identifier': CURRENT_DEVICE_ID},
        )
        assert_error_response(
            response=response,
            status_code=HTTPStatus.CONFLICT,
            contained_in_msg='Cannot delete the current device',
        )

        # The external request should not be made because validation fails first
        mock_delete.assert_not_called()
