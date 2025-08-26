import json
import os
import tempfile
from base64 import b64decode
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import call, patch

import gevent
import pytest

from rotkehlchen.api.websockets.typedefs import DBUploadStatusStep, WSMessageType
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.api import (
    IncorrectApiKeyFormat,
    PremiumAuthenticationError,
    RotkehlchenPermissionError,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.premium.premium import (
    DOCKER_PLATFORM_KEY,
    KUBERNETES_PLATFORM_KEY,
    Premium,
    PremiumCredentials,
    check_docker_container,
    get_kubernetes_pod_name,
)
from rotkehlchen.tests.utils.constants import A_GBP, DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.tests.utils.decoders import patch_decoder_reload_data
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import (
    VALID_PREMIUM_KEY,
    VALID_PREMIUM_SECRET,
    assert_db_got_replaced,
    create_patched_requests_get_for_premium,
    get_different_hash,
    setup_starting_environment,
)
from rotkehlchen.types import ChainID
from rotkehlchen.user_messages import MessagesAggregator
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

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)
    remote_hash = get_different_hash(our_hash)

    def mock_successful_upload_data_to_server(
            url,  # pylint: disable=unused-argument
            data,
            files,
            timeout,  # pylint: disable=unused-argument
            headers,
    ):
        # Can't compare the data blob and its hash as it is encrypted and as such can be
        # different each time
        assert 'file_hash' in data
        assert 'total_size' in data
        assert data['last_modify_ts'] == last_write_ts
        assert 'nonce' in data
        assert data['compression'] == 'zlib'

        # Parse Content-Range header (in format: `bytes 0-524287/25000000`)
        content_range = headers['Content-Range']
        assert content_range.startswith('bytes ')
        range_info, total_size = content_range.replace('bytes ', '').split('/')
        start, end = range_info.split('-')

        expected_chunk_size = len(files['chunk_data'][1])  # chunk_data is a tuple (filename, data)
        assert int(end) - int(start) + 1 == expected_chunk_size

        if int(end) + 1 == int(total_size):  # last chunk, return ok
            return MockResponse(HTTPStatus.OK, '{"success": true}')
        else:  # intermediate chunk, return permanent redirect with upload_id
            return MockResponse(HTTPStatus.PARTIAL_CONTENT, '{"upload_id": "12345678"}')

    assert rotkehlchen_instance.premium is not None
    chunk_size_patch = patch('rotkehlchen.premium.premium.UPLOAD_CHUNK_SIZE', 300000)
    ws_patch = patch.object(rotkehlchen_instance.msg_aggregator, 'add_message')
    patched_post = patch.object(
        rotkehlchen_instance.premium.session,
        'post',
        side_effect=mock_successful_upload_data_to_server,
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
    with patched_get, chunk_size_patch, patched_post as mocked_post, ws_patch as ws_mock:
        tasks = rotkehlchen_instance.task_manager._maybe_schedule_db_upload()  # type: ignore[union-attr]  # task_manager can't be none here
        if tasks is not None:
            gevent.wait(tasks)

        if db_settings['premium_should_sync'] is False:
            assert mocked_post.call_count == 0
            with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
                assert rotkehlchen_instance.data.db.get_static_cache(cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS) is None  # noqa: E501
            assert rotkehlchen_instance.premium_sync_manager.last_data_upload_ts == 0
            return

        assert mocked_post.call_count == 3  # uploads in three chunks
        # Check WS messages via mocking since the websocket_connection fixture doesn't work
        # with the rotkehlchen_instance fixture
        assert ws_mock.call_args_list == [
            call(message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS, data={'type': str(DBUploadStatusStep.COMPRESSING)}),  # noqa: E501
            call(message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS, data={'type': str(DBUploadStatusStep.ENCRYPTING)}),  # noqa: E501
            call(message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS, data={'type': str(DBUploadStatusStep.UPLOADING), 'current_chunk': 1, 'total_chunks': 3}),  # noqa: E501
            call(message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS, data={'type': str(DBUploadStatusStep.UPLOADING), 'current_chunk': 2, 'total_chunks': 3}),  # noqa: E501
            call(message_type=WSMessageType.DATABASE_UPLOAD_PROGRESS, data={'type': str(DBUploadStatusStep.UPLOADING), 'current_chunk': 3, 'total_chunks': 3}),  # noqa: E501
            call(message_type=WSMessageType.DATABASE_UPLOAD_RESULT, data={'uploaded': True, 'actionable': False, 'message': None}),  # noqa: E501
        ]
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

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)
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

    with patched_get, patched_post as post_mock, patch.object(
        target=rotkehlchen_instance.data,
        attribute='compress_and_encrypt_db',
        new=lambda *args: (None, our_hash),
    ):
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

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)
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
        # was successfully initialized
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
def test_premium_toggle_chains_aggregator(
        blockchain,
        rotki_premium_credentials,
        username,
        database,
):
    """Tests that modules receive correctly the premium status when it's toggled"""
    for _, module in blockchain.iterate_modules():
        assert module.premium is None

    premium_obj = Premium(
        credentials=rotki_premium_credentials,
        username=username,
        msg_aggregator=MessagesAggregator(),
        db=database,
    )
    blockchain.activate_premium_status(premium_obj)
    for _, module in blockchain.iterate_modules():
        assert module.premium == premium_obj

    blockchain.deactivate_premium_status()
    for _, module in blockchain.iterate_modules():
        assert module.premium is None


@pytest.mark.parametrize('sql_vm_instructions_cb', [10])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_upload_data_to_server_db_already_in_use(rotkehlchen_instance):
    """Test that if the server has bigger DB size and context switch happens it
    all works out. Essentially a test for https://github.com/rotki/rotki/issues/5038
    where the DB is already in use error occurs.

    This can happen if we get into maybe_upload_data_to_server from 2 different greenlets
    and reach the export code from both.
    The solution was to add a lock in the entire maybe_upload_data_to_server.

    We emulate bigger size by just lowering sql_vm_instructions_cb to force a context switch

    Also this test checks for the deadlock (database locked message in the test) caused by doing DB
    operations in a different threadpool greenlet. The fix was to move only the compressing and
    encrypting into that thread greenlet but not the DB reading.
    """
    with rotkehlchen_instance.data.db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )
        assert last_ts is None
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)
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
    chain_manager = rotkehlchen_instance.chains_aggregator.get_evm_manager(ChainID.ETHEREUM)

    def mock_stuff(chain_id, limit):
        """Just mock get_transaction_hashes_not_decoded which is called during
        get_and_decode_undecoded_transactions() to add some DB work and some sleeping.
        This triggers the threadpool deadlock problem in 50% of the test runs"""
        with chain_manager.node_inquirer.database.conn.read_ctx() as cursor:
            for _ in range(3):
                cursor.execute('SELECT * FROM settings').fetchall()

        gevent.sleep(.5)
        return []

    patched_get_hashes_not_decoded = patch.object(
        chain_manager.transactions_decoder.dbevmtx,
        'get_transaction_hashes_not_decoded',
        wraps=mock_stuff,
    )  # Mix in calls to decoding and calls to maybe_upload to emulate the deadlock of different threadpool greenlet that's mentioned in the docstring  # noqa: E501
    with patched_get_hashes_not_decoded, patch_decoder_reload_data(), patched_get, patched_post as post_mock:  # noqa: E501
        greenlets = [
            gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server),
            gevent.spawn(chain_manager.transactions_decoder.get_and_decode_undecoded_transactions, True),  # noqa: E501
            gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server),
            gevent.spawn(chain_manager.transactions_decoder.get_and_decode_undecoded_transactions, True),  # noqa: E501
            gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server),
            gevent.spawn(chain_manager.transactions_decoder.get_and_decode_undecoded_transactions, True),  # noqa: E501
            gevent.spawn(rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server),
            gevent.spawn(chain_manager.transactions_decoder.get_and_decode_undecoded_transactions, True),  # noqa: E501
        ]
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
        When the error occurred any detach or other operation here would result
        in database is locked.

        So to check this does not happen we make sure that when we come here
        the plaintext DB is not attached. Which is also the fix. To make that
        export occur under a critical section
        """
        with db.conn.read_ctx() as cursor:
            result = cursor.execute('SELECT * FROM pragma_database_list;')
            assert len(result.fetchall()) == 1, 'the plaintext DB should not be attached here'

    with db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_static_cache(
            cursor=cursor, name=DBCacheStatic.LAST_DATA_UPLOAD_TS,
        )
        assert last_ts is None
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)
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
def test_upload_data_error(rotkehlchen_instance: 'Rotkehlchen') -> None:
    """Test that we correctly handle errors from the nest server"""
    assert rotkehlchen_instance.premium is not None
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tempdbfile:
        tempdbpath = rotkehlchen_instance.data.db.export_unencrypted(tempdbfile)
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(tempdbpath)
    remote_hash = get_different_hash(our_hash)
    patched_get = create_patched_requests_get_for_premium(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # small size otherwise upload will fail with a different error
        metadata_data_size=2,
        saved_data=b'foo',
    )
    for (status_code, response_text, error_msg, expected_call_count) in (
        (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, 'Payload size is too big', 'Size limit reached', 1),
        (HTTPStatus.BAD_REQUEST, 'XYZ', 'Could not upload database backup due to: XYZ', 2),
    ):
        with patched_get, patch.object(
            rotkehlchen_instance.premium.session,
            'post',
            return_value=MockResponse(status_code, response_text),
        ) as mock_post:
            status, error = rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()

        assert status is False
        assert error == error_msg
        assert mock_post.call_count == expected_call_count


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
        if 'nest/1/devices' in url:
            return MockResponse(HTTPStatus.OK, json.dumps(devices))
        raise NotImplementedError('unexpected url')

    def mock_device_registration(url, **kwargs):  # pylint: disable=unused-argument
        nonlocal device_registered
        device_registered = True
        return MockResponse(HTTPStatus.CREATED, json.dumps({'registered': True}))

    def mock_device_check(url, **kwargs):  # pylint: disable=unused-argument
        if device_limit_reached:
            return MockResponse(HTTPStatus.FORBIDDEN, '')

        status_code = HTTPStatus.OK if device_registered else HTTPStatus.NOT_FOUND
        return MockResponse(status_code, '')

    premium = rotkehlchen_instance.premium
    assert premium is not None

    with (
        patch.object(premium.session, 'get', side_effect=mock_devices_list),
        patch.object(premium.session, 'post', side_effect=mock_device_check),
        patch.object(premium.session, 'put', side_effect=mock_device_registration),
    ):
        if device_limit_reached is True:
            with pytest.raises(PremiumAuthenticationError):
                premium.authenticate_device()
        else:
            premium.authenticate_device()

    # check that the request to register the device was made when it is possible to register it
    assert device_registered != device_limit_reached


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_limits_caching(rotkehlchen_instance: 'Rotkehlchen') -> None:
    """Test that user limits are cached properly to avoid repeated API calls."""
    premium = rotkehlchen_instance.premium
    assert premium is not None

    premium._cached_limits = None
    assert premium._cached_limits is None

    limits_data = {  # mock limits response
        'history_events': 10000,
        'pnl_reports': 50,
        'devices': 3,
    }
    with patch.object(  # mock the external request
        premium.session,
        'get',
        return_value=MockResponse(200, json.dumps(limits_data)),
    ) as mock_get:
        # First call should hit the API
        limits1 = premium.fetch_limits()
        assert limits1 == limits_data
        assert premium._cached_limits == limits_data
        assert mock_get.call_count == 1

        # Second call should use cache, not hit API
        limits2 = premium.fetch_limits()
        assert limits2 == limits_data
        assert premium._cached_limits == limits_data
        assert mock_get.call_count == 1  # Should still be 1, not 2

        # Third call should also use cache
        limits3 = premium.fetch_limits()
        assert limits3 == limits_data
        assert mock_get.call_count == 1  # Should still be 1, not 2

    # check that cache is cleared when credentials are reset
    premium.reset_credentials(premium.credentials)
    assert premium._cached_limits is None

    with patch.object(  # after reset, next call should hit API again
        premium.session,
        'get',
        return_value=MockResponse(200, json.dumps(limits_data)),
    ) as mock_get:
        limits4 = premium.fetch_limits()
        assert limits4 == limits_data
        assert premium._cached_limits == limits_data


def test_docker_device_version_update(rotki_premium_object, database):
    """Test that Docker device registration handles version updates correctly"""
    premium = rotki_premium_object
    premium.db = database  # Set the database for this test

    with (
        # Mock platform.system to return Linux (Docker detection)
        patch('rotkehlchen.premium.premium.platform.system', return_value='Linux'),
        # Mock check_docker_container to return a container ID
        patch('rotkehlchen.premium.premium.check_docker_container', return_value=('abc123def456', DOCKER_PLATFORM_KEY)),  # noqa: E501
        # Mock get_system_spec to control version
        patch('rotkehlchen.premium.premium.get_system_spec', return_value={'rotkehlchen': '1.0.0'}),  # noqa: E501
    ):
        # Test 1: Initial registration failure with device limit and no cached info
        with (
            patch.object(premium.session, 'put', return_value=MockResponse(HTTPStatus.UNPROCESSABLE_ENTITY, '{}')),  # noqa: E501
            patch.object(premium.session, 'delete') as mock_delete,
        ):
            # No cached info, should just fail
            with pytest.raises(RemoteError):
                premium._register_new_device('test_device_id')
            mock_delete.assert_not_called()

        # Save device info to cache for subsequent tests (same version as current)
        premium._set_docker_device_info('old_device_id', '1.0.0')

        # Test 2: Same version - should not delete old device
        with (
            patch.object(premium.session, 'put', return_value=MockResponse(HTTPStatus.UNPROCESSABLE_ENTITY, '{}')),  # noqa: E501
            patch.object(premium.session, 'delete') as mock_delete,
        ):
            with pytest.raises(RemoteError):
                premium._register_new_device('test_device_id')
            mock_delete.assert_not_called()

        # Update cached version to older version
        premium._set_docker_device_info('old_device_id', '0.8.0')

        # Test 3: Newer version - should delete old device and register new
        with (
            patch.object(premium.session, 'put', side_effect=[
                MockResponse(HTTPStatus.UNPROCESSABLE_ENTITY, '{}'),  # First attempt fails
                MockResponse(HTTPStatus.CREATED, '{}'),  # Second attempt after delete succeeds
            ]) as mock_put,
            patch.object(premium.session, 'delete', return_value=MockResponse(HTTPStatus.OK, '{}')) as mock_delete,  # noqa: E501
        ):
            premium._register_new_device('new_device_id')

            # Verify delete was called with old device
            mock_delete.assert_called_once()
            call_args = mock_delete.call_args
            assert call_args[1]['json']['device_identifier'] == 'old_device_id'

            # Verify registration was attempted twice
            assert mock_put.call_count == 2

            # Verify cache was updated with new device info
            cached_info = premium._get_docker_device_info()
            assert cached_info is not None
            assert cached_info[0] == 'new_device_id'
            assert cached_info[1] == '1.0.0'


def test_get_kubernetes_pod_name_reads_hostname():
    """Ensures pod name is read from /etc/hostname when K8s is detected."""
    with (
        patch.dict(os.environ, {'KUBERNETES_SERVICE_HOST': '1'}, clear=False),
        patch(
            'rotkehlchen.premium.premium.Path.read_text',
            return_value=(pod_id := 'test-pod-123'),
        ),
    ):
        assert get_kubernetes_pod_name() == pod_id
        assert check_docker_container() == (pod_id, KUBERNETES_PLATFORM_KEY)
