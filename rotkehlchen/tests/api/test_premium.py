import json
import sqlite3
import tempfile
from contextlib import ExitStack, closing
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from unittest.mock import patch

import machineid
import pytest
import requests

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT, FREE_REPORTS_LOOKUP_LIMIT
from rotkehlchen.constants.limits import FREE_HISTORY_EVENTS_LIMIT
from rotkehlchen.data_handler import RemoteBackup
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.errors.misc import RemoteBackupDowngrade
from rotkehlchen.premium.premium import get_free_capabilities
from rotkehlchen.premium.sync import (
    PASSWORD_CHANGE_SIZE_TOLERANCE_BYTES,
    PremiumSyncManager,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_async_response,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import create_patched_requests_get_for_premium
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterator
    from tempfile import _TemporaryFileWrapper

    from rotkehlchen.api.server import APIServer

CURRENT_DEVICE_ID = machineid.hashed_id('yabirgb')


@pytest.fixture
def mock_upload_preparation(rotkehlchen_api_server: APIServer) -> Iterator[None]:
    """Keep upload-result tests independent of full database export and backup encryption."""
    def export_small_db(tempdbfile: _TemporaryFileWrapper[bytes]) -> Path:
        tempdbpath = Path(tempdbfile.name)
        tempdbfile.close()
        with closing(sqlite3.connect(tempdbpath)) as conn:
            conn.execute('CREATE TABLE backup(payload BLOB)')
        return tempdbpath

    def prepared_backup(tempdbpath: Path, **_kwargs: object) -> tuple[bytearray, str]:
        tempdbpath.unlink()
        return bytearray(b'backup payload'), 'backup-hash'

    data = rotkehlchen_api_server.rest_api.rotkehlchen.data
    with (
        patch.object(data.db, 'export_unencrypted', side_effect=export_small_db),
        patch.object(
            data,
            'compress_and_encrypt_db',
            side_effect=prepared_backup,
        ),
    ):
        yield


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.usefixtures('mock_upload_preparation')
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


SIZE_LIMIT_MSG = 'Uploaded database is bigger than the maximum allowed for your tier'


def _force_upload(rotkehlchen_api_server: APIServer, post_response: MockResponse) -> dict:
    """Forces an upload against a server answering every chunk with post_response and
    returns the outcome of the task"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    with (
        create_patched_requests_get_for_premium(
            session=rotki.premium.session,
            metadata_last_modify_ts=0,
            metadata_data_hash='remote_hash',
            metadata_data_size=2,
            saved_data=b'foo',
        ),
        patch.object(rotki.premium.session, 'post', return_value=post_response),
    ):
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'upload'})
        task_id = assert_ok_async_response(response)
        return wait_for_async_task(rotkehlchen_api_server, task_id)


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.usefixtures('mock_upload_preparation')
def test_upload_db_failure_reason_is_returned(rotkehlchen_api_server: APIServer) -> None:
    """A failed forced upload must return its reason as an error, not as result False with the
    reason in the message, which the frontend would drop. A server error that is not marked
    as a size limit rejection stays a gateway error, whatever its message says."""
    assert_error_async_response(
        _force_upload(rotkehlchen_api_server, MockResponse(
            HTTPStatus.BAD_REQUEST,
            json.dumps({'success': False, 'msg': SIZE_LIMIT_MSG}),
        )),
        contained_in_msg=f'Upload failed. Could not upload database backup due to: {SIZE_LIMIT_MSG}',  # noqa: E501
        status_code=HTTPStatus.BAD_GATEWAY,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.usefixtures('mock_upload_preparation')
def test_upload_db_refused_by_server_for_size(rotkehlchen_api_server: APIServer) -> None:
    """A backup the server refuses for exceeding the tier's size is a conflict with the plan,
    not a gateway error, and retrying it is pointless"""
    outcome = _force_upload(rotkehlchen_api_server, MockResponse(
        HTTPStatus.BAD_REQUEST,
        json.dumps({
            'success': False,
            'msg': SIZE_LIMIT_MSG,
            'error_code': 'backup_size_limit_exceeded',
        }),
    ))
    assert_error_async_response(
        outcome,
        contained_in_msg='Upload failed. The rotki server refused the backup because it is bigger than your plan allows.',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('premium_limits_override', [{'max_backup_size_mb': 1}])
def test_upload_db_too_big_for_tier(rotkehlchen_api_server: APIServer) -> None:
    """A backup found too big for the tier before uploading is a conflict too"""
    with patch('rotkehlchen.data_handler.BYTES_PER_MB', 1):  # make the tiny test DB too big
        outcome = _force_upload(rotkehlchen_api_server, MockResponse(HTTPStatus.OK, '{}'))

    assert_error_async_response(
        outcome,
        contained_in_msg='Upload failed. The compressed database does not fit in the 1 MB your plan allows for backups.',  # noqa: E501
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_db_plan_without_backups(rotkehlchen_api_server: APIServer) -> None:
    """A forced upload on a plan that includes no backups says so, instead of a bare
    'Upload failed.' that leaves the user guessing"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    with (
        patch.object(rotki.premium, 'get_capabilities', return_value={'max_backup_size_mb': 0}),
        patch.object(rotki.premium_sync_manager, 'upload_data_to_server') as upload_mock,
    ):
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'upload'})
        task_id = assert_ok_async_response(response)
        assert_error_async_response(
            response_data=wait_for_async_task(rotkehlchen_api_server, task_id),
            contained_in_msg='Upload failed. Your premium plan does not include database backups.',
            status_code=HTTPStatus.BAD_GATEWAY,
        )
    upload_mock.assert_not_called()


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_settings', [{'premium_should_sync': True}])
@pytest.mark.parametrize('remote_size', ['smaller', 'slightly_bigger', 'over_tolerance'])
def test_password_change_makes_backup_upload_due(
        rotkehlchen_api_server: APIServer,
        username: str,
        db_password: str,
        remote_size: Literal['smaller', 'slightly_bigger', 'over_tolerance'],
) -> None:
    """The backup on the server is encrypted with the password it was made with. After a
    password change it is replaced at the next scheduled upload, even though it holds the
    latest data and an upload was attempted less than an hour ago. That also holds when it
    is a few bytes bigger than the new backup, since the compressed size shifts slightly,
    but not when the difference exceeds the small byte tolerance and so may represent data
    this DB lacks. Once replaced, a bigger remote backup is refused again."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    db, sync_manager = rotki.data.db, rotki.premium_sync_manager
    with db.conn.read_ctx() as cursor:
        backup_ts = db.get_setting(cursor, name='last_write_ts')
    recent_upload_ts = ts_now()
    sync_manager.last_upload_attempt_ts = recent_upload_ts
    with db.conn.write_ctx() as write_cursor:
        db.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
            value=recent_upload_ts,
        )
    with patch.object(rotki.premium, 'get_capabilities', return_value={'max_backup_size_mb': 100}):
        assert sync_manager.check_if_should_sync(force_upload=False) == (False, None)
        # Use the same second as the previous write to verify that changing the password
        # still advances last_write_ts strictly past the remote backup timestamp.
        with patch('rotkehlchen.db.dbhandler.ts_now', return_value=backup_ts):
            assert_simple_ok_response(requests.patch(
                api_url_for(rotkehlchen_api_server, 'userpasswordchangeresource', name=username),
                json={'name': username, 'current_password': db_password, 'new_password': 'foo'},
            ))
        with db.conn.read_ctx() as cursor:
            assert db.get_setting(cursor, name='last_write_ts') == (
                password_change_ts := Timestamp(backup_ts + 1)
            )
            assert db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.PREMIUM_BACKUP_PASSWORD_CHANGE_TS,
            ) == password_change_ts

        # Recreating the manager simulates an app restart before the scheduled upload.
        # The persisted password-change marker must keep the upload immediately due.
        restarted_sync_manager = PremiumSyncManager(
            migration_manager=sync_manager.migration_manager,
            data=rotki.data,
        )
        restarted_sync_manager.premium = rotki.premium
        sync_manager = restarted_sync_manager
        assert sync_manager.last_upload_attempt_ts == 0

        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
            new_backup, _ = rotki.data.compress_and_encrypt_db(
                tempdbpath=db.export_unencrypted(tempdbfile),
                last_modify_ts=password_change_ts,
            )
        # Bigger than the new backup, yet within the small absolute tolerance, so that only
        # the remote modification time decides the size check.
        within_tolerance_size = len(new_backup) + 100
        over_tolerance_size = len(new_backup) + PASSWORD_CHANGE_SIZE_TOLERANCE_BYTES + 1
        with (
            create_patched_requests_get_for_premium(
                session=rotki.premium.session,
                metadata_last_modify_ts=backup_ts,
                metadata_data_hash='remote_hash',
                metadata_data_size={
                    'smaller': 2,
                    'slightly_bigger': within_tolerance_size,
                    'over_tolerance': over_tolerance_size,
                }[remote_size],
                saved_data=b'foo',
            ),
            patch.object(
                rotki.premium.session,
                'post',
                return_value=MockResponse(HTTPStatus.OK, '{"success": true}'),
            ) as post_mock,
        ):
            assert sync_manager.check_if_should_sync(force_upload=False) == (True, None)
            if remote_size == 'over_tolerance':
                assert sync_manager.maybe_upload_data_to_server() == (
                    False, 'Remote database bigger than the local one',
                )
                assert post_mock.call_count == 0
                return

            assert sync_manager.maybe_upload_data_to_server() == (True, None)
            assert post_mock.call_count == 1
        with db.conn.read_ctx() as cursor:
            assert db.get_static_cache(
                cursor=cursor,
                name=DBCacheStatic.PREMIUM_BACKUP_PASSWORD_CHANGE_TS,
            ) == 0

        # the remote backup now has the new password, so the size check applies to it again
        with db.conn.write_ctx() as write_cursor:
            db.set_setting(write_cursor, name='last_write_ts', value=password_change_ts + 100)
        with (
            create_patched_requests_get_for_premium(
                session=rotki.premium.session,
                metadata_last_modify_ts=password_change_ts,
                metadata_data_hash='remote_hash',
                metadata_data_size=len(new_backup) * 2,
                saved_data=b'foo',
            ),
            patch.object(rotki.premium.session, 'post') as post_mock,
        ):
            assert sync_manager.maybe_upload_data_to_server() == (
                False, 'Remote database bigger than the local one',
            )
        assert post_mock.call_count == 0


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_password_change_during_backup_upload_stays_due(
        rotkehlchen_api_server: APIServer,
        username: str,
        db_password: str,
) -> None:
    """An upload encrypted before a password change must not satisfy that password change."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    db, sync_manager = rotki.data.db, rotki.premium_sync_manager
    with db.conn.read_ctx() as cursor:
        backup_ts = db.get_setting(cursor, name='last_write_ts')

    def change_password_during_upload(*args: object, **kwargs: object) -> MockResponse:
        assert_simple_ok_response(requests.patch(
            api_url_for(rotkehlchen_api_server, 'userpasswordchangeresource', name=username),
            json={'name': username, 'current_password': db_password, 'new_password': 'foo'},
        ))
        return MockResponse(HTTPStatus.OK, '{"success": true}')

    with (
        create_patched_requests_get_for_premium(
            session=rotki.premium.session,
            metadata_last_modify_ts=Timestamp(backup_ts - 1),
            metadata_data_hash='remote_hash',
            metadata_data_size=2,
            saved_data=b'foo',
        ),
        patch.object(rotki.premium.session, 'post', side_effect=change_password_during_upload),
    ):
        assert sync_manager.maybe_upload_data_to_server() == (True, None)

    with db.conn.read_ctx() as cursor:
        pending_password_change_ts = db.get_static_cache(
            cursor=cursor,
            name=DBCacheStatic.PREMIUM_BACKUP_PASSWORD_CHANGE_TS,
        )
    assert pending_password_change_ts is not None
    assert pending_password_change_ts > backup_ts
    assert sync_manager.last_upload_attempt_ts == 0


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_pull_db_without_remote_backup(rotkehlchen_api_server: APIServer) -> None:
    """A forced download with no backup on the server is a not found, not a gateway error"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    with (
        patch.object(rotki.premium_sync_manager, '_query_last_data_metadata'),
        patch.object(rotki.premium, 'pull_data', return_value=None),
    ):
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'download'})
        task_id = assert_ok_async_response(response)
        assert_error_async_response(
            response_data=wait_for_async_task(rotkehlchen_api_server, task_id),
            contained_in_msg='There is no database backup on the server.',
            status_code=HTTPStatus.NOT_FOUND,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize(('legacy', 'restored_backup_ts'), [(True, None), (False, 1760882400)])
def test_pull_db(
        rotkehlchen_api_server: APIServer,
        legacy: bool,
        restored_backup_ts: Timestamp | None,
) -> None:
    """Just a smoke test that the api works fine for this endpoint, and that a forced
    download returns the authenticated timestamp of the restored backup.

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
            metadata_last_modify_ts=restored_backup_ts or 0,
            metadata_data_hash=b'',
            metadata_data_size=9999999999,
            saved_data=b'foo',
        ), patch.object(
            rotki.premium_sync_manager.data,
            'decrypt_db',
            return_value=RemoteBackup(legacy=legacy, last_modify_ts=restored_backup_ts, user_db=b''),  # noqa: E501
        ), patch.object(
            rotki.premium_sync_manager.data,
            'restore_db',
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
        assert result['result'] == {'last_modify_ts': restored_backup_ts}


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_pull_db_refuses_legacy_backup_after_v1_sync(rotkehlchen_api_server: APIServer) -> None:
    """A forced download of a legacy backup, once this device synced the current format,
    fails with a message saying which device to update"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_PREMIUM_BACKUP_V1_SYNC_TS,
            value=Timestamp(1),
        )

    with create_patched_requests_get_for_premium(
        session=rotki.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=b'',
        metadata_data_size=9999999999,
        saved_data=(Path(__file__).resolve().parent.parent / 'data' / 'remote_encrypted_db.bin').read_bytes(),  # noqa: E501
    ), patch.object(rotki.data, 'restore_db') as restore_db:
        response = requests.put(api_url_for(
            rotkehlchen_api_server,
            'userpremiumsyncresource',
        ), json={'async_query': True, 'action': 'download'})
        task_id = assert_ok_async_response(response)
        assert_error_async_response(
            response_data=wait_for_async_task(rotkehlchen_api_server, task_id),
            contained_in_msg=str(RemoteBackupDowngrade()),
            status_code=HTTPStatus.CONFLICT,
        )
    assert restore_db.call_count == 0


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


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_premium_capabilities(rotkehlchen_api_server: APIServer) -> None:
    """Test the GET /premium/capabilities endpoint."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is not None
    with patch.object(
        rotki.premium,
        'fetch_limits',
        return_value={
            'current_tier': 'Advanced',
            'limit_of_devices': 4,
            'pnl_events_limit': 100000,
            'max_backup_size_mb': 600,
            'history_events_limit': 100000,
            'reports_lookup_limit': 300,
            'eth_staked_limit': 384,
            'eth_staking_view': True,
            'graphs_view': True,
            'event_analysis_view': False,
            'asset_movement_matching': True,
            'gnosispay': True,
            'monerium': False,
            'mcp': True,
            'unlocks': {
                'eth_staking_view': 'Basic',
                'graphs_view': 'Basic',
                'event_analysis_view': 'Basic',
                'asset_movement_matching': 'Basic',
                'gnosispay': 'Advanced',
                'monerium': 'Advanced',
                'mcp': 'Basic',
            },
        },
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'premiumcapabilitiesresource',
        ))
        result = assert_proper_sync_response_with_result(response)

        assert result == {
            'current_tier': 'Advanced',
            'limit_of_devices': 4,
            'pnl_events_limit': 100000,
            'max_backup_size_mb': 600,
            'history_events_limit': 100000,
            'reports_lookup_limit': 300,
            'eth_staked_limit': 384,
            'eth_staking_view': {
                'enabled': True,
                'minimum_tier': 'Basic',
            },
            'graphs_view': {
                'enabled': True,
                'minimum_tier': 'Basic',
            },
            'event_analysis_view': {
                'enabled': False,
                'minimum_tier': 'Basic',
            },
            'asset_movement_matching': {
                'enabled': True,
                'minimum_tier': 'Basic',
            },
            'gnosispay': {
                'enabled': True,
                'minimum_tier': 'Advanced',
            },
            'monerium': {
                'enabled': False,
                'minimum_tier': 'Advanced',
            },
            'mcp': {
                'enabled': True,
                'minimum_tier': 'Basic',
            },
        }


@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_get_free_user_capabilities(rotkehlchen_api_server: APIServer) -> None:
    """Test the GET /premium/capabilities endpoint for a free user."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    assert rotki.premium is None
    with patch(
        'rotkehlchen.api.rest.get_free_capabilities',
        return_value={
            'current_tier': 'Free',
            'limit_of_devices': 0,
            'pnl_events_limit': FREE_PNL_EVENTS_LIMIT,
            'max_backup_size_mb': 0,
            'history_events_limit': FREE_HISTORY_EVENTS_LIMIT,
            'reports_lookup_limit': FREE_REPORTS_LOOKUP_LIMIT,
            'eth_staked_limit': 0,
            'eth_staking_view': {
                'enabled': False,
                'minimum_tier': 'Basic',
            },
            'graphs_view': {
                'enabled': False,
                'minimum_tier': 'lite',
            },
            'event_analysis_view': {
                'enabled': False,
                'minimum_tier': 'lite',
            },
            'asset_movement_matching': {
                'enabled': False,
                'minimum_tier': 'Basic',
            },
            'gnosispay': {
                'enabled': False,
                'minimum_tier': 'Advanced',
            },
            'monerium': {
                'enabled': False,
                'minimum_tier': 'Advanced',
            },
        },
    ):
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'premiumcapabilitiesresource',
        ))
        result = assert_proper_sync_response_with_result(response)

        assert result == {
            'current_tier': 'Free',
            'limit_of_devices': 0,
            'pnl_events_limit': FREE_PNL_EVENTS_LIMIT,
            'max_backup_size_mb': 0,
            'history_events_limit': FREE_HISTORY_EVENTS_LIMIT,
            'reports_lookup_limit': FREE_REPORTS_LOOKUP_LIMIT,
            'eth_staked_limit': 0,
            'eth_staking_view': {
                'enabled': False,
                'minimum_tier': 'Basic',
            },
            'graphs_view': {
                'enabled': False,
                'minimum_tier': 'lite',
            },
            'event_analysis_view': {
                'enabled': False,
                'minimum_tier': 'lite',
            },
            'asset_movement_matching': {
                'enabled': False,
                'minimum_tier': 'Basic',
            },
            'gnosispay': {
                'enabled': False,
                'minimum_tier': 'Advanced',
            },
            'monerium': {
                'enabled': False,
                'minimum_tier': 'Advanced',
            },
        }


def test_free_capabilities_expose_every_unlock() -> None:
    """get_free_capabilities() must surface a block for each known capability.

    The endpoint test above patches this function out, so without this test the real
    implementation never runs and a capability missing from it goes unnoticed.
    """
    unlocks = {
        'eth_staking_view': 'Supporter',
        'graphs_view': 'Basic',
        'event_analysis_view': 'Basic',
        'asset_movement_matching': 'Basic',
        'gnosispay': 'Basic',
        'monerium': 'Basic',
        'mcp': 'Basic',
    }
    with patch(
        'rotkehlchen.premium.premium.fetch_capability_unlocks',
        return_value=unlocks,
    ):
        capabilities = get_free_capabilities()

    assert capabilities['current_tier'] == 'Free'
    for name, minimum_tier in unlocks.items():
        assert capabilities[name] == {  # type: ignore[literal-required]  # keys are capability names
            'enabled': False,
            'minimum_tier': minimum_tier,
        }, f'free capability {name} missing or not matching its unlock tier'
