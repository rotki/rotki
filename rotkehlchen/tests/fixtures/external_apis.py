import json

import pytest

from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.types import ExternalService
from rotkehlchen.utils.misc import ts_now


@pytest.fixture(name='gnosispay_credentials')
def fixture_gnosispay_credentials(database):
    """Input mock monerium credentials to the DB for testing"""
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) '
            'VALUES(?, ?, ?)',
            (ExternalService.GNOSIS_PAY.name.lower(), 'token', None),
        )


@pytest.fixture(name='monerium_credentials')
def fixture_monerium_credentials(database):
    """Input mock monerium credentials to the DB for testing"""
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS,
            value=json.dumps({
                'access_token': 'mock-access-token',
                'refresh_token': 'mock-refresh-token',
                'expires_at': ts_now() + 3600,
                'client_id': 'mock-client-id',
                'token_type': 'Bearer',
                'user_email': 'mock@monerium.com',
                'default_profile_id': 'profile-id',
                'profiles': [],
            }),
        )
