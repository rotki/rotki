import json
from base64 import b64decode
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import gevent
import pytest

from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.api import (
    IncorrectApiKeyFormat,
    PremiumAuthenticationError,
    RotkehlchenPermissionError,
)
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.tests.utils.constants import A_GBP, DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import (
    VALID_PREMIUM_KEY,
    VALID_PREMIUM_SECRET,
    assert_db_got_replaced,
    create_patched_requests_get_for_premium,
    get_different_hash,
    setup_starting_environment,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen


@pytest.fixture(name='premium_remote_data')
def fixture_load_remote_premium_data() -> bytes:
    return (Path(__file__).resolve().parent.parent / 'data' / 'remote_encrypted_db.bin').read_bytes()  # noqa: E501


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_settings', [
    {'premium_should_sync': True},
    {'premium_should_sync': False},
])
def test_upload_data_to_server(
        rotkehlchen_instance: 'Rotkehlchen',
        username: str,
        db_password: str,
        db_settings: dict[str, bool],
) -> None:
    """Test our side of uploading data to the server"""
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )
        assert last_ts is None

    with rotkehlchen_instance.data.db.user_write() as write_cursor:
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(
            write_cursor,
            ModifiableDBSettings(main_currency=A_GBP.resolve_to_fiat_asset()),
        )

    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        last_write_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_write_ts')

    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db()
    remote_hash = get_different_hash(our_hash)

    def mock_succesfull_upload_data_to_server(
            url,  # pylint: disable=unused-argument
            data,
            files,
            timeout,  # pylint: disable=unused-argument
    ):
        # Can't compare data blobs as they are encrypted and as such can be
        # different each time
        assert data['original_hash'] == our_hash
        assert data['last_modify_ts'] == last_write_ts
        assert 'index' in data
        assert len(files['db_file']) == data['length']
        assert 'nonce' in data
        assert data['compression'] == 'zlib'

        return MockResponse(200, '{"success": true}')

    assert rotkehlchen_instance.premium is not None
    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        side_effect=mock_succesfull_upload_data_to_server,
    )
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # Smaller Remote DB size
        metadata_data_size=2,
        saved_data=b'foo',
    )

    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS) is None  # noqa: E501

    now = ts_now()
    with patched_get, patched_post:
        tasks = rotkehlchen_instance.task_manager._maybe_schedule_db_upload()  # type: ignore[union-attr]  # task_manager can't be none here
        if tasks is not None:
            gevent.wait(tasks)

        if db_settings['premium_should_sync'] is False:
            with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
                assert rotkehlchen_instance.data.db.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS) is None  # noqa: E501
            assert rotkehlchen_instance.premium_sync_manager.last_data_upload_ts == 0
            return

        with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
            last_ts = rotkehlchen_instance.data.db.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS)  # noqa: E501
        db_msg = 'The last data upload timestamp should have been saved in the db as now'
        memory_msg = 'The last data upload timestamp should also be in memory'
        assert last_ts is not None, db_msg
        assert rotkehlchen_instance.premium_sync_manager.last_data_upload_ts is not None, memory_msg  # noqa: E501
        assert last_ts >= now and last_ts - now < 50, db_msg
        last_ts = rotkehlchen_instance.premium_sync_manager.last_data_upload_ts
        assert last_ts >= now and last_ts - now < 50, memory_msg

    # and now logout and login again and make sure that the last_data_upload_ts is correct
    rotkehlchen_instance.logout()
    rotkehlchen_instance.data.unlock(
        username=username,
        password=db_password,
        create_new=False,
        resume_from_backup=False,
    )
    assert last_ts == rotkehlchen_instance.premium_sync_manager.last_data_upload_ts
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert last_ts == rotkehlchen_instance.data.db.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS)  # noqa: E501


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server_same_hash(rotkehlchen_instance):
    """Test that if the server has same data hash as we no upload happens"""
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )

    assert last_ts is None
    with rotkehlchen_instance.data.db.user_write() as write_cursor:
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(write_cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501

    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db()
    remote_hash = our_hash

    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        return_value=MockResponse(200, '{"success": true}'),
    )
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # Smaller Remote DB size
        metadata_data_size=2,
        saved_data='foo',
    )

    with patched_get, patched_post as post_mock:
        rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()
        # The upload mock should not have been called since the hash is the same
        assert not post_mock.called


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_settings', [
    {'ask_user_upon_size_discrepancy': True},
    {'ask_user_upon_size_discrepancy': False},
])
def test_upload_data_to_server_smaller_db(rotkehlchen_instance, db_settings: dict[str, bool]):
    """Test that if the server has bigger DB size no upload happens"""
    with rotkehlchen_instance.data.db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )
        assert last_ts is None
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR.resolve_to_asset_with_oracles()))  # noqa: E501
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db()
    remote_hash = get_different_hash(our_hash)

    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        return_value=MockResponse(200, '{"success": true}'),
    )
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # larger DB than ours
        metadata_data_size=9999999999,
        saved_data=b'foo',
    )

    with patched_get, patched_post as post_mock:
        rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()
        if db_settings['ask_user_upon_size_discrepancy'] is True:
            # Ensure upload mock is not called when `ask_user_upon_size_discrepancy` is set
            assert not post_mock.called
        else:
            # Ensure upload mock is called when `ask_user_upon_size_discrepancy` is unset
            assert post_mock.called


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_new_account_can_pull_data(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    # Test that even with can_sync False, at start of new account we attempt data pull
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
        remote_data=premium_remote_data,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_new_account_rejects_data(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    # Test that even with can_sync False, at start of new account we attempt data pull
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
        sync_database=False,
        remote_data=premium_remote_data,
    )
    msg = 'Test default main currency should be different from the restored currency'
    assert DEFAULT_TESTS_MAIN_CURRENCY != A_GBP, msg
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == DEFAULT_TESTS_MAIN_CURRENCY  # noqa: E501


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_new_account_pull_old_data(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
):
    """
    Test that if the remote DB is of an old version its upgraded before replacing our current

    For a new account
    """
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
        remote_data=(Path(__file__).resolve().parent.parent / 'data' / 'remote_old_encrypted_db.bin').read_bytes(),  # noqa: E501
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_can_pull_data(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=True,
        remote_data=premium_remote_data,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_can_pull_old_data(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
):
    """
    Test that if the remote DB is of an old version its upgraded before replacing our current

    For an old account
    """
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=True,
        remote_data=(Path(__file__).resolve().parent.parent / 'data' / 'remote_encrypted_db.bin').read_bytes(),  # noqa: E501
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_doesnt_pull_data_with_no_premium_sync(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
        remote_data=premium_remote_data,
    )
    # DB should not have changed
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == DEFAULT_TESTS_MAIN_CURRENCY  # noqa: E501


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_older_remote_ts_smaller_remote_size(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=False,
        db_can_sync_setting=True,
        remote_data=premium_remote_data,
    )
    # DB should not have changed
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == DEFAULT_TESTS_MAIN_CURRENCY  # noqa: E501


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_newer_remote_ts_smaller_remote_size(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    """Assure that newer remote ts and smaller remote size asks the user for sync"""
    with pytest.raises(RotkehlchenPermissionError):
        setup_starting_environment(
            rotkehlchen_instance=rotkehlchen_instance,
            username=username,
            premium_credentials=rotki_premium_credentials,
            first_time=False,
            same_hash_with_remote=False,
            newer_remote_db=True,
            db_can_sync_setting=True,
            sync_approval='unknown',
            remote_data=premium_remote_data,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_password', ['different_password_than_remote_db_was_encoded_with'])
def test_try_premium_at_start_new_account_different_password_than_remote_db(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    """
    If we make a new account with api keys and provide a password different than
    the one the remote DB is encrypted with then make sure that PremiumAuthenticationError
    is thrown and that it is shown to the user.
    """
    with pytest.raises(PremiumAuthenticationError):
        setup_starting_environment(
            rotkehlchen_instance=rotkehlchen_instance,
            username=username,
            premium_credentials=rotki_premium_credentials,
            first_time=True,
            same_hash_with_remote=False,
            newer_remote_db=False,
            db_can_sync_setting=True,
            remote_data=premium_remote_data,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('premium_remote_data', [None])
def test_try_premium_at_start_first_time_no_previous_db(
        rotkehlchen_instance,
        username,
        rotki_premium_credentials,
        premium_remote_data,
):
    """Regression test for:
    - https://github.com/rotki/rotki/issues/1571
    - https://github.com/rotki/rotki/issues/2846
    """
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        premium_credentials=rotki_premium_credentials,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=False,
        db_can_sync_setting=True,
        remote_data=premium_remote_data,
    )
    # DB should not have changed and no exception raised
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == DEFAULT_TESTS_MAIN_CURRENCY  # noqa: E501
        # DB should have the given rotki premium credentials saved in it since premium
        # was succesfully initialized
        credentials = rotkehlchen_instance.data.db.get_rotkehlchen_premium(cursor)

    assert credentials is not None
    assert credentials.api_key == rotki_premium_credentials.api_key
    assert credentials.api_secret == rotki_premium_credentials.api_secret


def test_premium_credentials():
    """Test the premium credentials class"""
    # Test that improperly formatted keys are spotted
    with pytest.raises(IncorrectApiKeyFormat):
        credentials = PremiumCredentials('foo', 'boo')

    api_key = VALID_PREMIUM_KEY
    secret = VALID_PREMIUM_SECRET
    credentials = PremiumCredentials(
        given_api_key=api_key,
        given_api_secret=secret,
    )
    assert isinstance(credentials.api_key, str)
    assert credentials.api_key == api_key
    assert isinstance(credentials.api_secret, bytes)
    assert credentials.api_secret == b64decode(secret)


@pytest.mark.parametrize('ethereum_modules', [['uniswap', 'sushiswap']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_premium_toggle_chains_aggregator(blockchain, rotki_premium_credentials, username):
    """Tests that modules receive correctly the premium status when it's toggled"""
    for _, module in blockchain.iterate_modules():
        assert module.premium is None

    premium_obj = Premium(credentials=rotki_premium_credentials, username=username)
    blockchain.activate_premium_status(premium_obj)
    for _, module in blockchain.iterate_modules():
        assert module.premium == premium_obj

    blockchain.deactivate_premium_status()
    for _, module in blockchain.iterate_modules():
        assert module.premium is None


@pytest.mark.parametrize('sql_vm_instructions_cb', [10])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server_db_already_in_use(rotkehlchen_instance):
    """Test that if the server has bigger DB size and context switch happens it
    all works out. Essentially a test for https://github.com/rotki/rotki/issues/5038
    where the DB is already in use error occurs.

    This can happen if we get into maybe_upload_data_to_server from 2 different greenlets
    and reach the export code from both.
    The solution was to add a lock in the entire maybe_upload_data_to_server.

    We emulate bigger size by just lowering sql_vm_instructions_cb to force a context switch
    """
    with rotkehlchen_instance.data.db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )
        assert last_ts is None
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db()
    remote_hash = get_different_hash(our_hash)

    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        return_value=MockResponse(200, '{"success": true}'),
    )
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # larger DB than ours
        metadata_data_size=9999999999,
        saved_data='foo',
    )

    with patched_get, patched_post as post_mock:
        a = gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server)
        b = gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server)
        greenlets = [a, b]
        gevent.joinall(greenlets)
        for g in greenlets:
            assert g.exception is None, f'One of the greenlets had an exception: {g.exception}'
        # The upload mock should not have been called since the hash is the same
        assert not post_mock.called


@pytest.mark.parametrize('sql_vm_instructions_cb', [20])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server_db_locked(rotkehlchen_instance):
    """Test that if the server has big DB size and context switch happens it
    all works out. Essentially a test for https://github.com/rotki/rotki/issues/5038
    where the DB is locked part occurs.

    This can occur when there is a context switch between ATTACH/DETACH of the
    exported plaintext DB and a transaction is somehow open and stays open in
    another greenlet.

    We emulate bigger size by just lowering sql_vm_instructions_cb to force a context switch
    """

    db = rotkehlchen_instance.data.db

    def function_to_context_switch_to():
        """This is the function that export_unencrypted should context switch to.
        When the error occured any detach or other operation here would result
        in database is locked.

        So to check this does not happen we make sure that when we come here
        the plaintext DB is not attached. Which is also the fix. To make that
        export occur under a critical section
        """
        result = db.conn.execute('SELECT * FROM pragma_database_list;')
        assert len(result.fetchall()) == 1, 'the plaintext DB should not be attached here'

    with db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )
        assert last_ts is None
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501

    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db()
    remote_hash = get_different_hash(our_hash)

    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        return_value=MockResponse(200, '{"success": true}'),
    )
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # larger DB than ours
        metadata_data_size=9999999999,
        saved_data='foo',
    )

    greenlets = []
    with patched_get, patched_post as post_mock:
        greenlets.extend((
            gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server),
            gevent.spawn(function_to_context_switch_to)))
        gevent.joinall(greenlets)
        for g in greenlets:
            assert g.exception is None, f'One of the greenlets had an exception: {g.exception}'
        # The upload mock should not have been called since the hash is the same
        assert not post_mock.called


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_settings', [{'premium_should_sync': True}])
def test_error_db_too_big(rotkehlchen_instance: 'Rotkehlchen') -> None:
    """Test that we correctly handle the 413 error from nest server"""
    def mock_error_upload_data_to_server(
            url,
            data,
            files,
            timeout,
    ):  # pylint: disable=unused-argument
        return MockResponse(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'Payload size is too big')

    assert rotkehlchen_instance.premium is not None
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db()
    remote_hash = get_different_hash(our_hash)
    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        side_effect=mock_error_upload_data_to_server,
    )
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # small size otherwise upload will fail with a different error
        metadata_data_size=2,
        saved_data=b'foo',
    )
    with patched_get, patched_post:
        status, error = rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()

    assert status is False
    assert error == 'Size limit reached'


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('device_limit', [1, 2])
def test_device_limits(rotkehlchen_instance: 'Rotkehlchen', device_limit: int) -> None:
    """
    Test that registering new devices works both when we can register a new device and when the
    limit has been reached
    """
    device_registered = False
    device_limit_reached = device_limit == 1
    devices = {
        'devices': [
            {
                'device_name': 'laptop',
                'user': 'yabirgb',
                'device_identifier': '21312312',
            },
        ],
        'limit': device_limit,
    }

    def mock_devices_list(url, data, **kwargs):  # pylint: disable=unused-argument
        nonlocal devices
        if 'webapi/1/manage/premium/devices' in url:
            return MockResponse(HTTPStatus.OK, json.dumps(devices))
        raise NotImplementedError('unexpected url')

    def mock_device_registration(url, data, **kwargs):  # pylint: disable=unused-argument
        nonlocal device_registered
        device_registered = True
        return MockResponse(HTTPStatus.OK, json.dumps({'registered': True}))

    premium = rotkehlchen_instance.premium
    assert premium is not None

    with (
        patch.object(premium.session, 'get', side_effect=mock_devices_list),
        patch.object(premium.session, 'put', side_effect=mock_device_registration),
    ):
        if device_limit_reached is True:
            with pytest.raises(PremiumAuthenticationError):
                premium.authenticate_device()
        else:
            premium.authenticate_device()

    # check that the request to register the device was made when it is possible to register it
    assert device_registered != device_limit_reached
