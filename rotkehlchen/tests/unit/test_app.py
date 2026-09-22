import base64
import uuid
from unittest import mock

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.db.connections import DBConnections
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.exchanges.constants import EXCHANGES_WITH_PASSPHRASE, SUPPORTED_EXCHANGES
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.data_issues.manager import DataIssuesManager
from rotkehlchen.locations.constants import (
    LOCATION_COINBASE,
    LOCATION_EXTERNAL,
)
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret, make_random_bytes
from rotkehlchen.types import ApiSecret


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
    # Mock having connections for all exchanges and premium credentials

    credentials = []
    for location in SUPPORTED_EXCHANGES:
        passphrase = None
        if location in EXCHANGES_WITH_PASSPHRASE:
            passphrase = 'supersecretpassphrase'
        if location == LOCATION_COINBASE:
            credentials.append(
                (str(location), location, str(uuid.uuid4()), base64.b64encode(make_random_bytes(32)).decode(), passphrase),  # noqa: E501
            )
        else:
            credentials.append(
                (str(location), location, make_api_key(), make_api_secret().decode(), passphrase),  # pylint: disable=no-member
            )
    with rotki.data.db.user_write() as write_cursor:
        for name, connector, api_key, api_secret, passphrase in credentials:
            DBConnections.add(write_cursor, name=name, connector=connector, location=connector, api_key=api_key, api_secret=ApiSecret(api_secret.encode()), passphrase=passphrase)  # noqa: E501
        write_cursor.execute(
            'INSERT OR REPLACE INTO user_credentials(name, location, api_key, api_secret) VALUES (?, ?, ?, ?)',  # noqa: E501
            ('rotkehlchen', LOCATION_EXTERNAL, make_api_key(), make_api_secret().decode()),  # pylint: disable=no-member
        )

    with rotki.data.db.conn.read_ctx() as cursor:
        rotki.exchange_manager.initialize_exchanges(
            connections=rotki.data.db.get_exchange_credentials(cursor),
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
    with (
        mock.patch.object(rotki.task_supervisor, 'spawn_and_track'),
        mock.patch.object(DataIssuesManager, 'reset_orphaned_remediations') as reset_mock,
    ):
        # Unlock user
        rotki.unlock_user(
            user='testuser',
            password='123',
            create_new=True,
            sync_approval='unknown',
            premium_credentials=None,
            resume_from_backup=False,
        )

    reset_mock.assert_called_once_with()

    # Check notification
    messages = rotki.msg_aggregator.rotki_notifier.messages
    assert len(messages) == 1
    assert messages[0].message_type == WSMessageType.SOLANA_TOKENS_MIGRATION
    assert messages[0].data == {'identifiers': ['token1', 'token2']}
