from base64 import b64decode
from pathlib import Path
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_EUR
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


@pytest.fixture(name='premium_remote_data')
def fixture_load_remote_premium_data() -> bytes:
    remote_db_path = Path(__file__).resolve().parent.parent / 'data' / 'remote_encrypted_db.txt'  # noqa: E501
    with open(remote_db_path, 'rb') as f:
        return f.read()


@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('db_settings', [
    {'premium_should_sync': True},
    {'premium_should_sync': False},
])
def test_upload_data_to_server(rotkehlchen_instance, username, db_password, db_settings):
    """Test our side of uploading data to the server"""
    with rotkehlchen_instance.data.db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_data_upload_ts')
        assert last_ts == 0

        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_GBP))  # noqa: E501
        last_write_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_write_ts')
        _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)
        remote_hash = get_different_hash(our_hash)

        def mock_succesfull_upload_data_to_server(
                url,  # pylint: disable=unused-argument
                data,
                timeout,  # pylint: disable=unused-argument
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

            return MockResponse(200, '{"success": true}')

        patched_put = patch.object(
            rotkehlchen_instance.premium.session,
            'put',
            side_effect=mock_succesfull_upload_data_to_server,
        )
        patched_get = create_patched_requests_get_for_premium(
            session=rotkehlchen_instance.premium.session,
            metadata_last_modify_ts=0,
            metadata_data_hash=remote_hash,
            # Smaller Remote DB size
            metadata_data_size=2,
            saved_data='foo',
        )

        now = ts_now()
        with patched_get, patched_put:
            rotkehlchen_instance.premium_sync_manager.maybe_upload_data_to_server()

        if db_settings['premium_should_sync'] is False:
            assert rotkehlchen_instance.data.db.get_setting(cursor, name='last_data_upload_ts') == 0  # noqa: E501
            assert rotkehlchen_instance.premium_sync_manager.last_data_upload_ts == 0
            return

        last_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_data_upload_ts')
        msg = 'The last data upload timestamp should have been saved in the db as now'
        assert last_ts >= now and last_ts - now < 50, msg
        last_ts = rotkehlchen_instance.premium_sync_manager.last_data_upload_ts
        msg = 'The last data upload timestamp should also be in memory'
        assert last_ts >= now and last_ts - now < 50, msg

    # and now logout and login again and make sure that the last_data_upload_ts is correct
    rotkehlchen_instance.logout()
    rotkehlchen_instance.data.unlock(username, db_password, create_new=False)
    assert last_ts == rotkehlchen_instance.premium_sync_manager.last_data_upload_ts
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert last_ts == rotkehlchen_instance.data.db.get_setting(cursor, name='last_data_upload_ts')  # noqa: E501


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_upload_data_to_server_same_hash(rotkehlchen_instance, db_password):
    """Test that if the server has same data hash as we no upload happens"""
    with rotkehlchen_instance.data.db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_data_upload_ts')
        assert last_ts == 0
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)
    remote_hash = our_hash

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        return_value=None,
    )
    patched_get = create_patched_requests_get_for_premium(
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
    with rotkehlchen_instance.data.db.user_write() as cursor:
        last_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_data_upload_ts')
        assert last_ts == 0
        # Write anything in the DB to set a non-zero last_write_ts
        rotkehlchen_instance.data.db.set_settings(cursor, ModifiableDBSettings(main_currency=A_EUR))  # noqa: E501
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)
    remote_hash = get_different_hash(our_hash)

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        return_value=None,
    )
    patched_get = create_patched_requests_get_for_premium(
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


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_new_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
        rotki_premium_credentials,
        premium_remote_data,
):
    # Test that even with can_sync False, at start of new account we attempt data pull
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
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
        db_password,
        rotki_premium_credentials,
        premium_remote_data,
):
    # Test that even with can_sync False, at start of new account we attempt data pull
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
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
        db_password,
        rotki_premium_credentials,
):
    """
    Test that if the remote DB is of an old version its upgraded before replacing our current

    For a new account
    """
    with open(Path(__file__).resolve().parent.parent / 'data' / 'remote_old_encrypted_db.txt', 'rb') as f:  # noqa: E501
        remote_data = f.read()

    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        premium_credentials=rotki_premium_credentials,
        first_time=True,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=False,
        remote_data=remote_data,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
        rotki_premium_credentials,
        premium_remote_data,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
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
        db_password,
        rotki_premium_credentials,
):
    """
    Test that if the remote DB is of an old version its upgraded before replacing our current

    For an old account
    """
    with open(Path(__file__).resolve().parent.parent / 'data' / 'remote_encrypted_db.txt', 'rb') as f:  # noqa: E501
        remote_data = f.read()

    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
        premium_credentials=rotki_premium_credentials,
        first_time=False,
        same_hash_with_remote=False,
        newer_remote_db=True,
        db_can_sync_setting=True,
        remote_data=remote_data,
    )
    assert_db_got_replaced(rotkehlchen_instance=rotkehlchen_instance, username=username)


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_try_premium_at_start_old_account_doesnt_pull_data_with_no_premium_sync(
        rotkehlchen_instance,
        username,
        db_password,
        rotki_premium_credentials,
        premium_remote_data,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
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
        db_password,
        rotki_premium_credentials,
        premium_remote_data,
):
    setup_starting_environment(
        rotkehlchen_instance=rotkehlchen_instance,
        username=username,
        db_password=db_password,
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
        db_password,
        rotki_premium_credentials,
        premium_remote_data,
):
    """Assure that newer remote ts and smaller remote size asks the user for sync"""
    with pytest.raises(RotkehlchenPermissionError):
        setup_starting_environment(
            rotkehlchen_instance=rotkehlchen_instance,
            username=username,
            db_password=db_password,
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
        db_password,
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
            db_password=db_password,
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
        db_password,
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
        db_password=db_password,
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


@pytest.mark.parametrize('ethereum_modules', [['uniswap', 'sushiswap', 'compound']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_premium_toggle_chain_manager(blockchain, rotki_premium_credentials):
    """Tests that modules receive correctly the premium status when it's toggled"""
    for _, module in blockchain.iterate_modules():
        assert module.premium is None

    premium_obj = Premium(rotki_premium_credentials)
    blockchain.activate_premium_status(premium_obj)
    for _, module in blockchain.iterate_modules():
        assert module.premium == premium_obj

    blockchain.deactivate_premium_status()
    for _, module in blockchain.iterate_modules():
        assert module.premium is None
