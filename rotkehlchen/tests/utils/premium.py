import base64
import json
import os
from http import HTTPStatus
from typing import Literal, Optional
from unittest.mock import patch

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_GBP, DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.tests.utils.mock import MockResponse

# Valid format but not "real" premium api key and secret
VALID_PREMIUM_KEY = (
    'kWT/MaPHwM2W1KUEl2aXtkKG6wJfMW9KxI7SSerI6/QzchC45/GebPV9xYZy7f+VKBeh5nDRBJBCYn7WofMO4Q=='
)
VALID_PREMIUM_SECRET = (
    'TEF5dFFrOFcwSXNrM2p1aDdHZmlndFRoMTZQRWJhU2dacTdscUZSeHZTRmJLRm5ZaVRlV2NYU'
    'llYR1lxMjlEdUtRdFptelpCYmlXSUZGRTVDNWx3NDNYbjIx'
)


def mock_query_last_metadata(last_modify_ts, data_hash, data_size):
    def do_mock_query_last_metadata(url, data, timeout):  # pylint: disable=unused-argument
        assert len(data) == 1
        assert 'nonce' in data
        assert timeout == ROTKEHLCHEN_SERVER_TIMEOUT
        payload = (
            f'{{"upload_ts": 1337, '
            f'"last_modify_ts": {last_modify_ts}, '
            f'"data_hash": "{data_hash}",'
            f'"data_size": {data_size}}}'
        )
        return MockResponse(200, payload)

    return do_mock_query_last_metadata


def mock_get_saved_data(saved_data):
    def do_mock_get_saved_data(url, data, timeout):  # pylint: disable=unused-argument
        assert len(data) == 1
        assert 'nonce' in data
        assert timeout == ROTKEHLCHEN_SERVER_TIMEOUT
        decoded_data = None if saved_data is None else saved_data.decode()
        payload = f'{{"data": {json.dumps(decoded_data)}}}'
        return MockResponse(200, payload)

    return do_mock_get_saved_data


def create_patched_requests_get_for_premium(
        session,
        metadata_last_modify_ts=None,
        metadata_data_hash=None,
        metadata_data_size=None,
        saved_data=None,
        consider_authentication_invalid: bool = False,
):
    def mocked_get(url, *args, **kwargs):
        if consider_authentication_invalid:
            return MockResponse(
                HTTPStatus.UNAUTHORIZED,
                {'error': 'API KEY signature mismatch'},
            )

        if 'last_data_metadata' in url:
            assert metadata_last_modify_ts is not None
            assert metadata_data_hash is not None
            assert metadata_data_size is not None

            implementation = mock_query_last_metadata(
                last_modify_ts=metadata_last_modify_ts,
                data_hash=metadata_data_hash,
                data_size=metadata_data_size,
            )
        elif 'get_saved_data' in url:
            implementation = mock_get_saved_data(saved_data=saved_data)
        else:
            raise ValueError('Unmocked url in session get for premium')

        return implementation(url, *args, **kwargs)

    return patch.object(session, 'get', side_effect=mocked_get)


def create_patched_premium(
        premium_credentials: PremiumCredentials,
        patch_get: bool,
        metadata_last_modify_ts=None,
        metadata_data_hash=None,
        metadata_data_size=None,
        saved_data=None,
        consider_authentication_invalid: bool = False,
):
    premium = Premium(premium_credentials)
    patched_get = None
    if patch_get:
        patched_get = create_patched_requests_get_for_premium(
            session=premium.session,
            metadata_last_modify_ts=metadata_last_modify_ts,
            metadata_data_hash=metadata_data_hash,
            metadata_data_size=metadata_data_size,
            saved_data=saved_data,
            consider_authentication_invalid=consider_authentication_invalid,
        )
    patched_premium_at_start = patch(
        # note the patch location is in premium/sync.py
        'rotkehlchen.premium.sync.premium_create_and_verify',
        return_value=premium,
    )
    patched_premium_at_set = patch(
        # note the patch location is in rotkehlchen/rotkehlchen.py
        'rotkehlchen.rotkehlchen.premium_create_and_verify',
        return_value=premium,
    )
    return patched_premium_at_start, patched_premium_at_set, patched_get


def get_different_hash(given_hash: str) -> str:
    """Given the string hash get one that's different but has same length"""
    new_hash = ''
    for x in given_hash:
        new_hash = new_hash + chr(ord(x) + 1)

    return new_hash


def setup_starting_environment(
        rotkehlchen_instance: Rotkehlchen,
        username: str,
        db_password: str,
        first_time: bool,
        same_hash_with_remote: bool,
        newer_remote_db: bool,
        db_can_sync_setting: bool,
        premium_credentials: PremiumCredentials,
        remote_data: Optional[bytes],
        sync_approval: Literal['yes', 'no', 'unknown'] = 'yes',
        sync_database: bool = True,
):
    """
    Sets up the starting environment for premium testing when the user
    starts up his node either for the first time or logs in an already
    existing account
    """
    with rotkehlchen_instance.data.db.user_write() as cursor:
        if not first_time:
            # Emulate already having the api keys in the DB
            rotkehlchen_instance.data.db.set_rotkehlchen_premium(premium_credentials)

        rotkehlchen_instance.data.db.set_setting(cursor, name='premium_should_sync', value=db_can_sync_setting)  # noqa: E501
        our_last_write_ts = rotkehlchen_instance.data.db.get_setting(cursor, name='last_write_ts')
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == DEFAULT_TESTS_MAIN_CURRENCY  # noqa: E501

    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)

    if same_hash_with_remote:
        remote_hash = our_hash
    else:
        remote_hash = get_different_hash(our_hash)

    if newer_remote_db:
        metadata_last_modify_ts = our_last_write_ts + 10
    else:
        metadata_last_modify_ts = our_last_write_ts - 10

    patched_premium_at_start, _, patched_get = create_patched_premium(
        premium_credentials=premium_credentials,
        patch_get=True,
        metadata_last_modify_ts=metadata_last_modify_ts,
        metadata_data_hash=remote_hash,
        metadata_data_size=len(base64.b64decode(remote_data)) if remote_data else 0,
        saved_data=remote_data,
    )

    given_premium_credentials: Optional[PremiumCredentials]
    if first_time:
        given_premium_credentials = premium_credentials
        create_new = True
    else:
        given_premium_credentials = None
        create_new = False

    with patched_premium_at_start, patched_get:
        rotkehlchen_instance.premium_sync_manager.try_premium_at_start(
            given_premium_credentials=given_premium_credentials,
            username=username,
            create_new=create_new,
            sync_approval=sync_approval,
            sync_database=sync_database,
        )


def assert_db_got_replaced(rotkehlchen_instance: Rotkehlchen, username: str):
    """For environment setup with setup_starting_environment make sure DB is replaced
    """
    msg = 'Test default main currency should be different from the restored currency'
    assert DEFAULT_TESTS_MAIN_CURRENCY != A_GBP, msg
    # At this point pulling data from rotkehlchen server should have worked
    # and our database should have been replaced. The new data have different
    # main currency
    with rotkehlchen_instance.data.db.conn.read_ctx() as cursor:
        assert rotkehlchen_instance.data.db.get_setting(cursor, name='main_currency') == A_GBP
    # Also check a copy of our old DB is kept around.
    directory = os.path.join(rotkehlchen_instance.data.data_directory, username)
    files = [
        os.path.join(directory, f) for f in os.listdir(directory)
        if (not f.endswith('backup') or f.startswith('rotkehlchen_db')) and not f.startswith('rotkehlchen_transient')  # noqa: E501
    ]
    msg = f'Expected 2 or 3 files in the directory but got {files}'
    assert len(files) in (2, 3), msg  # 3rd file is the dbinfo.json
    # The order of the files is not guaranteed
    main_db_exists = False
    backup_db_exists = False
    for file in files:
        if 'rotkehlchen.db' in file:
            main_db_exists = True
        elif 'backup' in file:
            backup_db_exists = True

    assert main_db_exists
    assert backup_db_exists
