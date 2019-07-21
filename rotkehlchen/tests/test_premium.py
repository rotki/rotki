import base64
from unittest.mock import patch

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.premium import Premium
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.premium import (
    assert_db_got_replaced,
    create_patched_premium_session_get,
    setup_starting_environment,
)
from rotkehlchen.utils.misc import ts_now


def test_upload_data_to_server(rotkehlchen_instance, username, db_password):
    """Test our side of uploading data to the server"""
    rotkehlchen_instance.premium = Premium(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        api_secret=base64.b64encode(make_random_b64bytes(128)),
    )
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    assert last_ts == 0

    # Write anything in the DB to set a non-zero last_write_ts
    rotkehlchen_instance.data.db.set_main_currency('EUR')
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
        saved_data='foo',
    )

    with patched_get, patched_put:
        rotkehlchen_instance.upload_data_to_server()

    now = ts_now()
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    msg = 'The last data upload timestamp should have been saved in the db as now'
    assert last_ts >= now and last_ts - now < 50, msg
    last_ts = rotkehlchen_instance.last_data_upload_ts
    msg = 'The last data upload timestamp should also be in memory'
    assert last_ts >= now and last_ts - now < 50, msg

    # and now logout and login again and make sure that the last_data_upload_ts is correct
    rotkehlchen_instance.logout()
    rotkehlchen_instance.data.unlock(username, db_password, create_new=False)
    assert last_ts == rotkehlchen_instance.last_data_upload_ts
    assert last_ts == rotkehlchen_instance.data.db.get_last_data_upload_ts()


def test_upload_data_to_server_same_hash(rotkehlchen_instance, db_password):
    """Test that if the server has same data hash as we no upload happens"""
    rotkehlchen_instance.premium = Premium(
        api_key=base64.b64encode(make_random_b64bytes(128)),
        api_secret=base64.b64encode(make_random_b64bytes(128)),
    )
    last_ts = rotkehlchen_instance.data.db.get_last_data_upload_ts()
    assert last_ts == 0

    # Write anything in the DB to set a non-zero last_write_ts
    rotkehlchen_instance.data.db.set_main_currency('EUR')
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        return_value=None,
    )
    patched_get = create_patched_premium_session_get(
        session=rotkehlchen_instance.premium.session,
        metadata_last_modify_ts=0,
        metadata_data_hash=our_hash,
        saved_data='foo',
    )

    with patched_get, patched_put as put_mock:
        rotkehlchen_instance.upload_data_to_server()
        # The upload mock should not have been called since the hash is the same
        assert not put_mock.called


def test_try_premium_at_start_new_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
):
    # Test that even with can_sync False, at start of new account we attempt data pull
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


def test_try_premium_at_start_old_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=True,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


def test_try_premium_at_start_old_account_doesnt_pull_data_with_no_premium_sync(
        rotkehlchen_instance,
        username,
        db_password,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
    )
    # DB should not have changed
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD


def test_try_premium_at_start_old_account_same_hash(
        rotkehlchen_instance,
        username,
        db_password,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        first_time=False,
        same_hash_with_remote=True,
        newer_remote_db=True,
        db_can_sync_setting=True,
    )
    # DB should not have changed
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD


def test_try_premium_at_start_old_account_older_remote_ts(
        rotkehlchen_instance,
        username,
        db_password,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=False,
        db_can_sync_setting=True,
    )
    # DB should not have changed
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD
