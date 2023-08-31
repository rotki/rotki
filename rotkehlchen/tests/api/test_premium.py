from contextlib import ExitStack
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import create_patched_requests_get_for_premium


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_db(rotkehlchen_api_server):
    """Just a smoke test that the api works fine. Would have prevented:
    https://github.com/rotki/rotki/issues/6524.

    We don't test the actual upload here, as the various scenarios are tested in
    tests/integration/test_premium.py
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
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
        [stack.enter_context(patch) for patch in patches]  # pylint: disable=expression-not-assigned  # noqa: E501
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
def test_pull_db(rotkehlchen_api_server):
    """Just a smoke test that the api works fine for this endpoint.

    Actual functionality tested in tests/integration/test_premium.py
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
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
    patches.append(patch.object(
        rotki.premium_sync_manager.data,
        'decompress_and_decrypt_db',
        return_value=None,
    ))

    with ExitStack() as stack:
        [stack.enter_context(patch) for patch in patches]  # pylint: disable=expression-not-assigned  # noqa: E501
        response = requests.put(api_url_for(
            rotkehlchen_api_server,  # testing normal flow works fine
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'download'})
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert result['message'] == ''
        assert result['result'] is True
