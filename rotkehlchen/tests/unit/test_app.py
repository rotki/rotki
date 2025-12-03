import base64
import uuid
from unittest import mock

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.exchanges.constants import EXCHANGES_WITH_PASSPHRASE, SUPPORTED_EXCHANGES
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret, make_random_bytes
from rotkehlchen.types import Location


def test_initializing_exchanges(uninitialized_rotkehlchen):
    """Test that initializing exchanges for which credentials exist in the DB works

    This also tests db.get_exchange_credentials() since we also pretend to have
    a premium subscription credentials and that function should not return it.
    """
    rotki = uninitialized_rotkehlchen
    username = 'someusername'
    db_password = '123'
    rotki.data.unlock(username, db_password, create_new=True, resume_from_backup=False)
    database = rotki.data.db
    # Mock having user_credentials for all exchanges and for premium
    cmd = (
        'INSERT OR REPLACE INTO user_credentials '
        '(name, location, api_key, api_secret, passphrase) VALUES (?, ?, ?, ?, ?)'
    )

    credentials = []
    for location in SUPPORTED_EXCHANGES:
        passphrase = None
        if location in EXCHANGES_WITH_PASSPHRASE:
            passphrase = 'supersecretpassphrase'
        if location == Location.COINBASE:
            credentials.append(
                (str(location), location.serialize_for_db(), str(uuid.uuid4()), base64.b64encode(make_random_bytes(32)).decode(), passphrase),  # noqa: E501
            )
        else:
            credentials.append(
                (str(location), location.serialize_for_db(), make_api_key(), make_api_secret().decode(), passphrase),  # noqa: E501  # pylint: disable=no-member
            )
    credentials.append(
        ('rotkehlchen', Location.EXTERNAL.serialize_for_db(), make_api_key(), make_api_secret().decode(), None),  # noqa: E501  # pylint: disable=no-member
    )
    cursor = rotki.data.db.conn.cursor()
    for entry in credentials:
        cursor.execute(cmd, entry)
        rotki.data.db.conn.commit()

    exchange_credentials = rotki.data.db.get_exchange_credentials(cursor)
    rotki.exchange_manager.initialize_exchanges(
        exchange_credentials=exchange_credentials,
        database=database,
    )

    assert all(location in rotki.exchange_manager.connected_exchanges for location in SUPPORTED_EXCHANGES)  # noqa: E501


@mock.patch('os.access')
def test_initializing_rotki_with_datadir_with_wrong_permissions(mock_os_access, cli_args):
    mock_os_access.return_value = False
    success = True
    try:
        with pytest.raises(SystemPermissionError):
            Rotkehlchen(args=cli_args)
    except Exception:  # pylint: disable=broad-except
        success = False

    assert success is True


def test_solana_tokens_migration_notification(uninitialized_rotkehlchen):
    """Test that Solana tokens migration notification is sent when table exists"""
    rotki = uninitialized_rotkehlchen
    rotki.msg_aggregator.rotki_notifier = MockRotkiNotifier()

    # Create user_added_solana_tokens table in globaldb
    with GlobalDBHandler().conn.write_ctx() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_added_solana_tokens (
                identifier TEXT PRIMARY KEY NOT NULL COLLATE NOCASE
            )
        """)
        cursor.execute("INSERT INTO user_added_solana_tokens VALUES ('token1'), ('token2')")

    # Mock greenlet spawning to avoid background tasks
    with mock.patch.object(rotki.greenlet_manager, 'spawn_and_track'):
        # Unlock user
        rotki.unlock_user(
            user='testuser',
            password='123',
            create_new=True,
            sync_approval='unknown',
            premium_credentials=None,
            resume_from_backup=False,
        )

    # Check notification
    messages = rotki.msg_aggregator.rotki_notifier.messages
    assert len(messages) == 1
    assert messages[0].message_type == WSMessageType.SOLANA_TOKENS_MIGRATION
    assert messages[0].data == {'identifiers': ['token1', 'token2']}
