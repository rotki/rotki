from unittest.mock import patch

import pytest

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.errors import UnableToDecryptRemoteData
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import (
    assert_db_got_replaced,
    create_patched_premium_session_get,
    setup_starting_environment,
)
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server(rotkehlchen_instance, username, db_password):
    """Test our side of uploading data to the server"""
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    assert last_ts == 0

    # Write anything in the DB to set a non-zero last_write_ts
    rotkehlchen_instance.set_settings({'main_currency': 'EUR'})
    last_write_ts = rotkehlchen_instance.data.db.get_last_write_ts()
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)
    remote_hash = 'a' + our_hash[1:]

    def mock_succesfull_upload_data_to_server(
            url,  # pylint: disable=unused-argument
            data,
            timeout,
    ):
        # Can't compare data blobs as they are encrypted and as such can be
        # different each time
        assert 'data_blob' in data
        assert data['original_hash'] == our_hash
        assert data['last_modify_ts'] == last_write_ts
        assert 'index' in data
        assert len(data['data_blob']) == data['length']
        assert 'nonce' in data
        assert data['compression'] == 'zlib'

        assert timeout == ROTKEHLCHEN_SERVER_TIMEOUT
        return MockResponse(200, '{"success": true}')

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        side_effect=mock_succesfull_upload_data_to_server,
    )
    patched_get = create_patched_premium_session_get(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # Smaller Remote DB size
        metadata_data_size=2,
        saved_data='foo',
    )

    with patched_get, patched_put:
        rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()

    now = ts_now()
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    msg = 'The last data upload timestamp should have been saved in the db as now'
    assert last_ts >= now and last_ts - now < 50, msg
    last_ts = rotkehlchen_instance.premium_sync_manager.last_data_upload_ts
    msg = 'The last data upload timestamp should also be in memory'
    assert last_ts >= now and last_ts - now < 50, msg

    # and now logout and login again and make sure that the last_data_upload_ts is correct
    rotkehlchen_instance.logout()
    rotkehlchen_instance.data.unlock(username, db_password, create_new=False)
    assert last_ts == rotkehlchen_instance.premium_sync_manager.last_data_upload_ts
    assert last_ts == rotkehlchen_instance.data.db.get_last_data_upload_ts()


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server_same_hash(rotkehlchen_instance, db_password):
    """Test that if the server has same data hash as we no upload happens"""
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    assert last_ts == 0

    # Write anything in the DB to set a non-zero last_write_ts
    rotkehlchen_instance.set_settings({'main_currency': 'EUR'})
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)
    remote_hash = our_hash

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        return_value=None,
    )
    patched_get = create_patched_premium_session_get(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # Smaller Remote DB size
        metadata_data_size=2,
        saved_data='foo',
    )

    with patched_get, patched_put as put_mock:
        rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()
        # The upload mock should not have been called since the hash is the same
        assert not put_mock.called


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server_smaller_db(rotkehlchen_instance, db_password):
    """Test that if the server has bigger DB size no upload happens"""
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    assert last_ts == 0

    # Write anything in the DB to set a non-zero last_write_ts
    rotkehlchen_instance.set_settings({'main_currency': 'EUR'})
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)
    remote_hash = 'a' + our_hash[1:]

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        return_value=None,
    )
    patched_get = create_patched_premium_session_get(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=remote_hash,
        # larger DB than ours
        metadata_data_size=9999999999,
        saved_data='foo',
    )

    with patched_get, patched_put as put_mock:
        rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()
        # The upload mock should not have been called since the hash is the same
        assert not put_mock.called


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_new_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    # Test that even with can_sync False, at start of new account we attempt data pull
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        api_key=rotkehlchen_api_key,
        api_secret=rotkehlchen_api_secret,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        api_key=rotkehlchen_api_key,
        api_secret=rotkehlchen_api_secret,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=True,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_doesnt_pull_data_with_no_premium_sync(
        rotkehlchen_instance,
        username,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        api_key=rotkehlchen_api_key,
        api_secret=rotkehlchen_api_secret,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
    )
    # DB should not have changed
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_same_hash(
        rotkehlchen_instance,
        username,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        api_key=rotkehlchen_api_key,
        api_secret=rotkehlchen_api_secret,
        first_time=False,
        same_hash_with_remote=True,
        newer_remote_db=True,
        db_can_sync_setting=True,
    )
    # DB should not have changed
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_older_remote_ts(
        rotkehlchen_instance,
        username,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        api_key=rotkehlchen_api_key,
        api_secret=rotkehlchen_api_secret,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=False,
        db_can_sync_setting=True,
    )
    # DB should not have changed
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_password', ['different_password_than_remote_db_was_encoded_with'])
def test_try_premium_at_start_new_account_different_password_than_remote_db(
        rotkehlchen_instance,
        username,
        db_password,
        rotkehlchen_api_key,
        rotkehlchen_api_secret,
):
    """
    If we make a new account with api keys and provide a password different than
    the one the remote DB is encrypted with then make sure that UnableToDecryptRemoteData
    is thrown and that it is shown to the user.
    """
    with pytest.raises(UnableToDecryptRemoteData):
        setup_starting_environment(
            rotkehlchen_instance=rotkehlchen_instance,
            username=username,
            db_password=db_password,
            api_key=rotkehlchen_api_key,
            api_secret=rotkehlchen_api_secret,
            first_time=True,
            same_hash_with_remote=False,
            newer_remote_db=False,
            db_can_sync_setting=True,
        )
