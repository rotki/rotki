from rotkehlchen.exchanges.manager import SUPPORTED_EXCHANGES
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret


def test_initializing_exchanges(uninitialized_rotkehlchen, accounting_data_dir):
    """Test that initializing exchanges for which credentials exist in the DB works

    This also tests db.get_exchange_credentials() since we also pretend to have
    a premium subscription credentials and that function should not return it.
    """
    rotki = uninitialized_rotkehlchen
    username = 'foo'
    db_password = '123'
    rotki.data.unlock(username, db_password, create_new=True)
    # Mock having user_credentials for all exchanges and for premium
    cmd = 'INSERT OR REPLACE INTO user_credentials(name, api_key, api_secret) VALUES (?, ?, ?)'

    credentials = []
    for name in SUPPORTED_EXCHANGES:
        credentials.append((name, make_api_key(), make_api_secret()))
    credentials.append(('rotkehlchen', make_api_key(), make_api_secret()))
    cursor = rotki.data.db.conn.cursor()
    for entry in credentials:
        cursor.execute(cmd, entry)
        rotki.data.db.conn.commit()

    exchange_credentials = rotki.data.db.get_exchange_credentials()
    rotki.exchange_manager.initialize_exchanges(
        exchange_credentials=exchange_credentials,
        user_directory=accounting_data_dir,
    )

    assert all(name in rotki.exchange_manager.connected_exchanges for name in SUPPORTED_EXCHANGES)
