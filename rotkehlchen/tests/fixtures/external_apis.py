import pytest

from rotkehlchen.types import ExternalService


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
        write_cursor.execute(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) '
            'VALUES(?, ?, ?)',
            (ExternalService.MONERIUM.name.lower(), 'mockuser', 'mockpassword'),
        )
