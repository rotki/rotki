import os

import pytest

from rotkehlchen.errors import SystemPermissionError
from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


def test_initializing_exchanges(uninitialized_rotkehlchen):
    """Test that initializing exchanges for which credentials exist in the DB works

    This also tests db.get_exchange_credentials() since we also pretend to have
    a premium subscription credentials and that function should not return it.
    """
    rotki = uninitialized_rotkehlchen
    username = 'someusername'
    db_password = '123'
    rotki.data.unlock(username, db_password, create_new=True)
    database = rotki.data.db
    # Mock having user_credentials for all exchanges and for premium
    cmd = (
        'INSERT OR REPLACE INTO user_credentials '
        '(name, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?)'
    )

    credentials = []
    for name in SUPPORTED_EXCHANGES:
        passphrase = None
        if name in ('coinbasepro', 'kucoin'):
            passphrase = 'supersecretpassphrase'
        credentials.append((name, make_api_key(), make_api_secret(), passphrase))
    credentials.append(('rotkehlchen', make_api_key(), make_api_secret(), None))
    cursor = rotki.data.db.conn.cursor()
    for entry in credentials:
        cursor.execute(cmd, entry)
        rotki.data.db.conn.commit()

    exchange_credentials = rotki.data.db.get_exchange_credentials()
    rotki.exchange_manager.initialize_exchanges(
        exchange_credentials=exchange_credentials,
        database=database,
    )

    assert all(name in rotki.exchange_manager.connected_exchanges for name in SUPPORTED_EXCHANGES)


def test_initializing_rotki_with_datadir_with_wrong_permissions(cli_args, data_dir):
    os.chmod(data_dir, 0o200)
    with pytest.raises(SystemPermissionError):
        Rotkehlchen(args=cli_args)
    os.chmod(data_dir, 0o777)
