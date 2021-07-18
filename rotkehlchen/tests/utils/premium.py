import base64
import json
import os
from http import HTTPStatus
from typing import Optional
from unittest.mock import patch

from typing_extensions import Literal

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import A_GBP, DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.tests.utils.mock import MockResponse

# Probably invalid remote data but bigger than the test local DB
INVALID_BUT_BIGGER_REMOTE_DATA = base64.b64encode(make_random_b64bytes(92048)).decode()
# Remote data containing a different main currency (GBP)
REMOTE_DATA = b'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'  # noqa: E501
# Remote data containing an older DB version
REMOTE_DATA_OLDER_DB = b'qLQdzIvX6c8jJyucladYh2wZvpPbna/hmokjLu8NX64blb+lM/HxIGtCq5YH9TNUV51VHGMqMBhUeHqdtdOh1/VLg5q2NuzNmiCUroV0u97YMYM5dsGrKpy+J9d1Hbq33dlx8YcQxBsJEM2lSmLXiW8DQ/AfNJfT7twe6u+w1i9soFF7hbkafnrg2s7QGukB8D4CY1sIcZd2VRlMy7ATwtOF9ur8KDrKfVpZSQlTsWfyfiWyJmcVTmvPjqPAmZ0PEDlwqmNETe6yeRnkKgU0T2xTrTAJkawoGn41g0LnYi+ghTBPTboiLVTqASk/C71ofdEjN0gacy/9wNIBrq3cvfZBsrTpjzt88W2pnPHbLdfxrycToeGKNBASexs42uzBWOqa6BFPEiy7mSzKClLp4q+hiZtasyhnwMzUYvsIb25BvXBAPJQnjcBW+hzuiwQp+C3hynxTSPY1v2S80i3fqDK7BKY8VpPpjV+tC5B0pn6PsBETKZjB1pPKQ//m/I8HI0bWb+0fpVs4NbK9nFpRN6Capd8wJTzWtSp7vGbHOoaDAwtNtp61QI7eDsiMZGYXFy5jn8CmE+uWC4zDhLmoAUwAehuUSjv0v5RJGX/IAgWxoRMhAEra54bRwZ0vY1YRBS/Xf/AXp17BRzqE8NwSAUstgizOk7ryT3BQaTqybrt4y4omyw1VVpeisJROVK0fcFJFFH1zYUbbUB+0CBRq20y54faSSNNjc05pYHv456BBBIwpUwMS4M7yZz+HwP8b/OIq0LMr7d5SJdDjG9Ut1siZbaGRdyqv86WNTiSrlMmTASHi7+z+Z8CX9GnmEgVJna5mvvOhBC/zIpZiRLzwbYjdvrtw3N9X+NHzIaDGrAo1LtWh+eGmRHPKlb+CICOMj4TGvtGKlL/IfzBcrBfeTwkNSge2l4mOFG9l82ci4RZ7I4Yr6WUQJ+NU6DYQYKb5wMz+xTJmenHHaQxy0fsTulO5/RKfY8u1O9xT5kDtNc/R00CDheqcTS773NLDL4dqHEE/+lVxoVdFT/VvxzHrBKnI6M1UyJgDHu1BFIto2/z2wS0GjVXkBVFvMfQTYMZmb88RP/04F00kt3wqg/lrhAqr60BaC/FzIKG9lepDXXBAhHZyy+a1HYCkJlA43QoX3duu3fauViP+2RN306/tFw6HJvkRiCU7E3T9tLOHU508PLhcN8a5ON7aVyBtzdGO5i57j6Xm96di79IsfwStowS31kDix+B1mYeD8R1nvthWOKgL2KiAl/UpbXDPOuVBYubZ+V4/D8jxRCivM2ukME+SCIGzraR3EBqAdvjp3dLC1tomnawaEzAQYTUHbHndYatmIYnzEsTzFd8OWoX/gy0KGaZJ/mUGDTFBbkWIDE8='  # noqa: E501

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
        remote_data: bytes = REMOTE_DATA,
        sync_approval: Literal['yes', 'no', 'unknown'] = 'yes',
):
    """
    Sets up the starting environment for premium testing when the user
    starts up his node either for the first time or logs in an already
    existing account
    """
    if not first_time:
        # Emulate already having the api keys in the DB
        rotkehlchen_instance.data.db.set_rotkehlchen_premium(premium_credentials)

    rotkehlchen_instance.data.db.update_premium_sync(db_can_sync_setting)
    our_last_write_ts = rotkehlchen_instance.data.db.get_last_write_ts()
    assert rotkehlchen_instance.data.db.get_main_currency() == DEFAULT_TESTS_MAIN_CURRENCY
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
        )


def assert_db_got_replaced(rotkehlchen_instance: Rotkehlchen, username: str):
    """For environment setup with setup_starting_environment make sure DB is replaced"""
    msg = 'Test default main currency should be different from the restored currency'
    assert DEFAULT_TESTS_MAIN_CURRENCY != A_GBP, msg
    # At this point pulling data from rotkehlchen server should have worked
    # and our database should have been replaced. The new data have different
    # main currency
    assert rotkehlchen_instance.data.db.get_main_currency() == A_GBP
    # Also check a copy of our old DB is kept around.
    directory = os.path.join(rotkehlchen_instance.data.data_directory, username)
    files = [
        os.path.join(directory, f) for f in os.listdir(directory)
        if not f.endswith('backup') or f.startswith('rotkehlchen_db')
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
