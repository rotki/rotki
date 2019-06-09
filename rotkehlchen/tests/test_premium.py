import base64
import os
from unittest.mock import patch

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.premium import Premium
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import ApiKey, ApiSecret
from rotkehlchen.utils.misc import ts_now


def patched_create_premium(
        api_key: ApiKey,
        api_secret: ApiSecret,
        patch_get: bool,
        metadata_last_modify_ts=None,
        metadata_data_hash=None,
        saved_data=None,
):
    premium = Premium(
        api_key=api_key,
        api_secret=api_secret,
    )
    patched_get = None
    if patch_get:
        patched_get = create_patched_premium_session_get(
            session=premium.session,
            metadata_last_modify_ts=metadata_last_modify_ts,
            metadata_data_hash=metadata_data_hash,
            saved_data=saved_data,
        )
    patched_premium = patch(
        # note the patch location is in rotkehlchen.py
        'rotkehlchen.rotkehlchen.premium_create_and_verify',
        return_value=premium,
    )

    return patched_premium, patched_get


def mock_query_last_metadata(last_modify_ts, data_hash):
    def do_mock_query_last_metadata(url, data, timeout):  # pylint: disable=unused-argument
        assert len(data) == 1
        assert 'nonce' in data
        assert timeout == ROTKEHLCHEN_SERVER_TIMEOUT
        # data_hash = base64.b64encode(
        #     hashlib.sha256(b'a').digest(),
        # ).decode()
        payload = (
            f'{{"upload_ts": 1337, '
            f'"last_modify_ts": {last_modify_ts}, '
            f'"data_hash": "{data_hash}"}}'
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


def create_patched_premium_session_get(
        session,
        metadata_last_modify_ts,
        metadata_data_hash,
        saved_data,
):
    def mocked_get(url, data, timeout):
        if 'last_data_metadata' in url:
            implementation = mock_query_last_metadata(
                last_modify_ts=metadata_last_modify_ts,
                data_hash=metadata_data_hash,
            )
        elif 'get_saved_data' in url:
            implementation = mock_get_saved_data(saved_data=saved_data)
        else:
            raise ValueError('Unmocked url in session get for premium')

        return implementation(url, data, timeout)

    return patch.object(
        session,
        'get',
        side_effect=mocked_get,
    )


def create_patched_premium_with_keypair(
        patch_get: bool,
        metadata_last_modify_ts=None,
        metadata_data_hash=None,
        saved_data=None,
):
    api_key = ApiKey(base64.b64encode(make_random_b64bytes(128)))
    api_secret = ApiSecret(base64.b64encode(make_random_b64bytes(128)))
    patches = patched_create_premium(
        api_key,
        api_secret,
        patch_get,
        metadata_last_modify_ts,
        metadata_data_hash,
        saved_data,
    )
    return api_key, api_secret, patches[0], patches[1]


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
    _, data_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)

    def mock_succesfull_upload_data_to_server(
            url,  # pylint: disable=unused-argument
            data,
            timeout,
    ):
        # Can't compare data blobs as they are encrypted and as such can be
        # different each time
        assert 'data_blob' in data
        assert data['original_hash'] == data_hash
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
        metadata_data_hash=data_hash,
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


# TODO: Seems that the premium_should_sync option is not used. Write test for it
def test_try_premium_at_start_new_account_can_pull_data(
        rotkehlchen_instance,
        username,
        db_password,
):
    our_last_write_ts = rotkehlchen_instance.data.db.get_last_write_ts()
    assert rotkehlchen_instance.data.db.get_main_currency() == A_USD
    _, our_hash = rotkehlchen_instance.data.compress_and_encrypt_db(db_password)

    remote_hash = 'a' + our_hash[1:]
    remote_data = b'qLQdzIvX6c8jJyucladYh2wZvpPbna/hmokjLu8NX64blb+lM/HxIGtCq5YH9TNUV51VHGMqMBhUeHqdtdOh1/VLg5q2NuzNmiCUroV0u97YMYM5dsGrKpy+J9d1Hbq33dlx8YcQxBsJEM2lSmLXiW8DQ/AfNJfT7twe6u+w1i9soFF7hbkafnrg2s7QGukB8D4CY1sIcZd2VRlMy7ATwtOF9ur8KDrKfVpZSQlTsWfyfiWyJmcVTmvPjqPAmZ0PEDlwqmNETe6yeRnkKgU0T2xTrTAJkawoGn41g0LnYi+ghTBPTboiLVTqASk/C71ofdEjN0gacy/9wNIBrq3cvfZBsrTpjzt88W2pnPHbLdfxrycToeGKNBASexs42uzBWOqa6BFPEiy7mSzKClLp4q+hiZtasyhnwMzUYvsIb25BvXBAPJQnjcBW+hzuiwQp+C3hynxTSPY1v2S80i3fqDK7BKY8VpPpjV+tC5B0pn6PsBETKZjB1pPKQ//m/I8HI0bWb+0fpVs4NbK9nFpRN6Capd8wJTzWtSp7vGbHOoaDAwtNtp61QI7eDsiMZGYXFy5jn8CmE+uWC4zDhLmoAUwAehuUSjv0v5RJGX/IAgWxoRMhAEra54bRwZ0vY1YRBS/Xf/AXp17BRzqE8NwSAUstgizOk7ryT3BQaTqybrt4y4omyw1VVpeisJROVK0fcFJFFH1zYUbbUB+0CBRq20y54faSSNNjc05pYHv456BBBIwpUwMS4M7yZz+HwP8b/OIq0LMr7d5SJdDjG9Ut1siZbaGRdyqv86WNTiSrlMmTASHi7+z+Z8CX9GnmEgVJna5mvvOhBC/zIpZiRLzwbYjdvrtw3N9X+NHzIaDGrAo1LtWh+eGmRHPKlb+CICOMj4TGvtGKlL/IfzBcrBfeTwkNSge2l4mOFG9l82ci4RZ7I4Yr6WUQJ+NU6DYQYKb5wMz+xTJmenHHaQxy0fsTulO5/RKfY8u1O9xT5kDtNc/R00CDheqcTS773NLDL4dqHEE/+lVxoVdFT/VvxzHrBKnI6M1UyJgDHu1BFIto2/z2wS0GjVXkBVFvMfQTYMZmb88RP/04F00kt3wqg/lrhAqr60BaC/FzIKG9lepDXXBAhHZyy+a1HYCkJlA43QoX3duu3fauViP+2RN306/tFw6HJvkRiCU7E3T9tLOHU508PLhcN8a5ON7aVyBtzdGO5i57j6Xm96di79IsfwStowS31kDix+B1mYeD8R1nvthWOKgL2KiAl/UpbXDPOuVBYubZ+V4/D8jxRCivM2ukME+SCIGzraR3EBqAdvjp3dLC1tomnawaEzAQYTUHbHndYatmIYnzEsTzFd8OWoX/gy0KGaZJ/mUGDTFBbkWIDE8='  # noqa: E501
    api_key, api_secret, patched_premium, patched_get = create_patched_premium_with_keypair(
        patch_get=True,
        metadata_last_modify_ts=our_last_write_ts + 10,  # Remote DB is newer
        metadata_data_hash=remote_hash,
        saved_data=remote_data,
    )

    with patched_premium, patched_get:
        rotkehlchen_instance.try_premium_at_start(
            api_key=api_key,
            api_secret=api_secret,
            username=username,
            create_new=True,
            sync_approval='yes',
        )

    # At this point pulling data from rotkehlchen server should have worked
    # and our database should have been replaced. The new data have different
    # main currency
    assert rotkehlchen_instance.data.db.get_main_currency() == A_GBP
    # Also check a copy of our old DB is kept around.
    directory = os.path.join(rotkehlchen_instance.data.data_directory, username)
    files = list(os.path.join(directory, f) for f in os.listdir(directory))
    assert len(files) == 2
    assert 'rotkehlchen.db' in files[0]
    assert 'backup' in files[1]


def test_pulling_data_from_server(rotkehlchen_instance, username, db_password):
    """Test our side of retrieving data from the server"""
    pass
