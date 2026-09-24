import base64
import uuid
from argparse import Namespace
from unittest import mock

import pytest

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.errors.misc import SystemPermissionError
from rotkehlchen.exchanges.constants import EXCHANGES_WITH_PASSPHRASE, SUPPORTED_EXCHANGES
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.tests.fixtures.messages import MockRotkiNotifier
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret, make_random_bytes
from rotkehlchen.types import Location


def test_main_loop_keeps_scheduling_after_indexer_analytics_error() -> None:
    rotki = object.__new__(Rotkehlchen)
    rotki.shutdown_event = mock.MagicMock()
    rotki.shutdown_event.wait.side_effect = [False, False, True]
    rotki.indexer_stats = mock.MagicMock()
    rotki.indexer_stats.maybe_flush.side_effect = [RuntimeError("can't start new thread"), None]
    rotki.task_manager = mock.MagicMock()
    rotki.args = Namespace(disable_task_manager=False)

    with mock.patch('rotkehlchen.rotkehlchen.log') as log:
        rotki.main_loop()

    assert rotki.task_manager.schedule.call_count == 2
    log.exception.assert_called_once_with('Failed to flush indexer usage analytics')


def test_logout_does_not_wait_for_indexer_analytics() -> None:
    rotki = object.__new__(Rotkehlchen)
    rotki.user_is_logged_in = True
    for attribute in (
        'data', 'exchange_manager', 'task_manager', 'task_supervisor',
        'cryptocompare', 'defillama', 'coingecko', 'alchemy', 'moralis', 'msg_aggregator',
        'chains_aggregator', 'accountant', 'history_querying_manager', 'data_importer',
    ):
        setattr(rotki, attribute, mock.MagicMock())
    stats = mock.MagicMock()
    rotki.indexer_stats = stats
    stats.wait_for_close.side_effect = AssertionError('logout waited for upload')

    with (
        mock.patch.object(Rotkehlchen, 'deactivate_premium_status'),
        mock.patch('rotkehlchen.rotkehlchen.Inquirer') as inquirer,
        mock.patch('rotkehlchen.rotkehlchen.CachedSettings'),
    ):
        rotki._logout()

    stats.start_close.assert_called_once_with()
    stats.wait_for_close.assert_not_called()
    assert vars(rotki)['indexer_stats'] is None
    assert vars(rotki)['_closing_indexer_stats'] is stats
    assert vars(rotki)['user_is_logged_in'] is False
    stats.wait_for_close.reset_mock(side_effect=True)
    rotki.wait_for_indexer_stats_close()
    stats.wait_for_close.assert_called_once_with()
    assert vars(rotki)['_closing_indexer_stats'] is None
    inquirer.assert_called_once()


def test_shutdown_waits_for_indexer_analytics_after_cleanup() -> None:
    rest_api = object.__new__(RestAPI)
    events: list[str] = []
    rest_api.rotkehlchen = mock.MagicMock()
    rest_api.main_loop_task = mock.MagicMock()
    rest_api.stop_event = mock.MagicMock()
    rest_api.rotkehlchen.shutdown.side_effect = lambda: events.append('logout')
    rest_api.main_loop_task.join.side_effect = lambda: events.append('main loop')
    rest_api.rotkehlchen.wait_for_indexer_stats_close.side_effect = lambda: events.append('wait')
    rest_api.stop_event.set.side_effect = lambda: events.append('stop event')

    with (
        mock.patch.object(
            rest_api,
            '_cancel_api_tasks',
            side_effect=lambda reason: events.append(f'cancel:{reason}'),
        ),
        mock.patch('rotkehlchen.api.rest.GlobalDBHandler') as global_db,
        mock.patch(
            'rotkehlchen.api.rest.logging.shutdown',
            side_effect=lambda: events.append('logging'),
        ),
    ):
        global_db.return_value.cleanup.side_effect = lambda: events.append('global DB')
        rest_api.stop()

    assert events == [
        'cancel:Cancelled due to shutdown',
        'logout',
        'main loop',
        'global DB',
        'wait',
        'logging',
        'stop event',
    ]


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
    with mock.patch.object(rotki.task_supervisor, 'spawn_and_track'):
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
