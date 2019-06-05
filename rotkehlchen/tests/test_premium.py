import base64
import hashlib
from unittest.mock import patch

from rotkehlchen.constants import ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.premium import Premium
from rotkehlchen.tests.utils.factories import make_random_b64bytes
from rotkehlchen.tests.utils.mock import MockResponse
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

    def mock_query_last_metadata(url, data, timeout):  # pylint: disable=unused-argument
        assert len(data) == 1
        assert 'nonce' in data
        assert timeout == ROTKEHLCHEN_SERVER_TIMEOUT
        data_hash = base64.b64encode(
            hashlib.sha256(b'a').digest(),
        ).decode()
        payload = f'{{"upload_ts": 1337, "last_modify_ts": 0, "data_hash": "{data_hash}"}}'
        return MockResponse(200, payload)

    patched_put = patch.object(
        rotkehlchen_instance.premium.session,
        'put',
        side_effect=mock_succesfull_upload_data_to_server,
    )
    patched_get = patch.object(
        rotkehlchen_instance.premium.session,
        'get',
        side_effect=mock_query_last_metadata,
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
