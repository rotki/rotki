import base64
import os
from http import HTTPStatus
from unittest.mock import patch

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.assets import A_GBP
from rotkehlchen.premium.premium import Premium, PremiumCredentials
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.constants import DEFAULT_TESTS_MAIN_CURRENCY
from rotkehlchen.tests.utils.mock import MockResponse

# Remote data containing a different main currency (GBP)
REMOTE_DATA = b'qLQdzIvX6c8jJyucladYh2wZvpPbna/hmokjLu8NX64blb+lM/HxIGtCq5YH9TNUV51VHGMqMBhUeHqdtdOh1/VLg5q2NuzNmiCUroV0u97YMYM5dsGrKpy+J9d1Hbq33dlx8YcQxBsJEM2lSmLXiW8DQ/AfNJfT7twe6u+w1i9soFF7hbkafnrg2s7QGukB8D4CY1sIcZd2VRlMy7ATwtOF9ur8KDrKfVpZSQlTsWfyfiWyJmcVTmvPjqPAmZ0PEDlwqmNETe6yeRnkKgU0T2xTrTAJkawoGn41g0LnYi+ghTBPTboiLVTqASk/C71ofdEjN0gacy/9wNIBrq3cvfZBsrTpjzt88W2pnPHbLdfxrycToeGKNBASexs42uzBWOqa6BFPEiy7mSzKClLp4q+hiZtasyhnwMzUYvsIb25BvXBAPJQnjcBW+hzuiwQp+C3hynxTSPY1v2S80i3fqDK7BKY8VpPpjV+tC5B0pn6PsBETKZjB1pPKQ//m/I8HI0bWb+0fpVs4NbK9nFpRN6Capd8wJTzWtSp7vGbHOoaDAwtNtp61QI7eDsiMZGYXFy5jn8CmE+uWC4zDhLmoAUwAehuUSjv0v5RJGX/IAgWxoRMhAEra54bRwZ0vY1YRBS/Xf/AXp17BRzqE8NwSAUstgizOk7ryT3BQaTqybrt4y4omyw1VVpeisJROVK0fcFJFFH1zYUbbUB+0CBRq20y54faSSNNjc05pYHv456BBBIwpUwMS4M7yZz+HwP8b/OIq0LMr7d5SJdDjG9Ut1siZbaGRdyqv86WNTiSrlMmTASHi7+z+Z8CX9GnmEgVJna5mvvOhBC/zIpZiRLzwbYjdvrtw3N9X+NHzIaDGrAo1LtWh+eGmRHPKlb+CICOMj4TGvtGKlL/IfzBcrBfeTwkNSge2l4mOFG9l82ci4RZ7I4Yr6WUQJ+NU6DYQYKb5wMz+xTJmenHHaQxy0fsTulO5/RKfY8u1O9xT5kDtNc/R00CDheqcTS773NLDL4dqHEE/+lVxoVdFT/VvxzHrBKnI6M1UyJgDHu1BFIto2/z2wS0GjVXkBVFvMfQTYMZmb88RP/04F00kt3wqg/lrhAqr60BaC/FzIKG9lepDXXBAhHZyy+a1HYCkJlA43QoX3duu3fauViP+2RN306/tFw6HJvkRiCU7E3T9tLOHU508PLhcN8a5ON7aVyBtzdGO5i57j6Xm96di79IsfwStowS31kDix+B1mYeD8R1nvthWOKgL2KiAl/UpbXDPOuVBYubZ+V4/D8jxRCivM2ukME+SCIGzraR3EBqAdvjp3dLC1tomnawaEzAQYTUHbHndYatmIYnzEsTzFd8OWoX/gy0KGaZJ/mUGDTFBbkWIDE8='  # noqa: E501

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
        payload = f'{{"data": "{saved_data.decode()}"}}'
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
            assert saved_data is not None
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


def setup_starting_environment(
        rotkehlchen_instance: Rotkehlchen,
        username: str,
        db_password: str,
        first_time: bool,
        same_hash_with_remote: bool,
        newer_remote_db: bool,
        db_can_sync_setting: bool,
        premium_credentials: PremiumCredentials,
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
        remote_hash = 'a' + our_hash[1:]
    remote_data = REMOTE_DATA

    if newer_remote_db:
        metadata_last_modify_ts = our_last_write_ts + 10
    else:
        metadata_last_modify_ts = our_last_write_ts - 10

    patched_premium_at_start, _, patched_get = create_patched_premium(
        premium_credentials=premium_credentials,
        patch_get=True,
        metadata_last_modify_ts=metadata_last_modify_ts,
        metadata_data_hash=remote_hash,
        metadata_data_size=len(base64.b64decode(REMOTE_DATA)),
        saved_data=remote_data,
    )

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
            sync_approval='yes',
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
    files = list(os.path.join(directory, f) for f in os.listdir(directory))
    assert len(files) == 2
    # The order of the files is not guaranteed
    assert 'rotkehlchen.db' in files[0] or 'rotkehlchen.db' in files[1]
    assert 'backup' in files[0] or 'backup' in files[1]
