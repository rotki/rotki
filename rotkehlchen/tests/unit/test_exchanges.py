import threading
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

from rotkehlchen.connections.types import new_connection_identifier
from rotkehlchen.db.connections import DBConnections
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.exchanges.binance import Binance
from rotkehlchen.locations.constants import (
    LOCATION_BINANCE,
    LOCATION_BITPANDA,
    LOCATION_KRAKEN,
    LOCATION_KUCOIN,
)
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.types import ApiKey, ApiSecret, ExchangeAuthCredentials

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.exchanges.manager import ExchangeManager
    from rotkehlchen.user_messages import MessagesAggregator


def test_exchanges_filtering(database, exchange_manager, function_scope_messages_aggregator):
    kraken1 = MockKraken(
        name='mockkraken_1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    kraken2 = MockKraken(
        name='mockkraken_2',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    binance1 = Binance(
        name='mockbinance_1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    binance2 = Binance(
        name='mockbinance_2',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )

    exchange_manager.initialize_exchanges([], database)
    exchange_manager.connected_exchanges[LOCATION_KRAKEN].append(kraken1)
    exchange_manager.connected_exchanges[LOCATION_KRAKEN].append(kraken2)
    exchange_manager.connected_exchanges[LOCATION_BINANCE].append(binance1)
    exchange_manager.connected_exchanges[LOCATION_BINANCE].append(binance2)
    assert set(exchange_manager.iterate_exchanges()) == {kraken1, kraken2, binance1, binance2}

    with database.user_write() as cursor:
        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[kraken1.connection_identifier, kraken2.connection_identifier],
        ))
        assert set(exchange_manager.iterate_exchanges()) == {binance1, binance2}

        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[binance1.connection_identifier],
        ))
        assert set(exchange_manager.iterate_exchanges()) == {binance2, kraken1, kraken2}


def test_query_exchange_history_events_respects_non_syncing(
        database: DBHandler,
        exchange_manager: ExchangeManager,
        function_scope_messages_aggregator: MessagesAggregator,
) -> None:
    kraken1 = MockKraken(
        name='mockkraken_1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )
    kraken2 = MockKraken(
        name='mockkraken_2',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
    )

    exchange_manager.initialize_exchanges([], database)
    exchange_manager.connected_exchanges[LOCATION_KRAKEN].append(kraken1)
    exchange_manager.connected_exchanges[LOCATION_KRAKEN].append(kraken2)

    with database.user_write() as cursor:
        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[kraken1.connection_identifier],
        ))

    with patch.object(kraken1, 'query_history_events') as kraken1_query, \
            patch.object(kraken2, 'query_history_events') as kraken2_query:
        exchange_manager.query_exchange_history_events(location=LOCATION_KRAKEN, identifier=None)

        kraken1_query.assert_not_called()
        kraken2_query.assert_called_once()


TEST_CREDENTIALS_1 = ExchangeAuthCredentials(
    api_key=ApiKey('api-key-1'),
    api_secret=ApiSecret(b'api-secret-1'),
    passphrase='passphrase-1',
)
TEST_CREDENTIALS_2 = ExchangeAuthCredentials(
    api_key=ApiKey('api-key-2'),
    api_secret=ApiSecret(b'api-secret-2'),
    passphrase='passphrase-2',
)
TEST_CREDENTIALS_3 = ExchangeAuthCredentials(
    api_key=ApiKey('api-key-3'),
    api_secret=ApiSecret(b'api-secret-3'),
    passphrase='passphrase-3',
)


def _saved_credentials(database: DBHandler, identifier: str) -> ExchangeAuthCredentials:
    with database.conn.read_ctx() as cursor:
        connection = DBConnections.get(cursor, identifier)
    assert connection is not None
    return ExchangeAuthCredentials(
        api_key=connection.api_key,
        api_secret=connection.api_secret,
        passphrase=connection.passphrase,
    )


def test_change_credentials(rotkehlchen_api_server: APIServer) -> None:
    """
    Test that chaining exchange credentials works as expected and if incorrect credentials
    were provided then the old credentials are restored.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    def mock_kucoin_validate_api_key(kucoin):
        if kucoin.api_passphrase in (TEST_CREDENTIALS_1.passphrase, TEST_CREDENTIALS_3.passphrase):
            return True, ''

        return False, 'Invalid passphrase'  # For TEST_KUCOIN_PASSPHRASE_2

    def get_current_credentials(kucoin) -> ExchangeAuthCredentials:
        return ExchangeAuthCredentials(kucoin.api_key, kucoin.secret, kucoin.api_passphrase)

    with patch('rotkehlchen.exchanges.kucoin.Kucoin.validate_api_key', mock_kucoin_validate_api_key):  # noqa: E501
        # Setup with correct credentials
        identifier, _ = rotki.setup_exchange(
            name='KuCoin',
            connector=LOCATION_KUCOIN,
            api_key=ApiKey('api-key-1'),
            api_secret=TEST_CREDENTIALS_1.api_secret,
            passphrase=TEST_CREDENTIALS_1.passphrase,
        )
        assert identifier is not None
        kucoin = rotki.exchange_manager.connected_exchanges[LOCATION_KUCOIN][0]
        assert _saved_credentials(rotki.data.db, identifier) == get_current_credentials(kucoin) == TEST_CREDENTIALS_1  # noqa: E501

        # Try to change credentials to incorrect ones
        success, _ = rotki.exchange_manager.edit_exchange(
            identifier=identifier,
            new_name=None,
            api_key=TEST_CREDENTIALS_2.api_key,
            api_secret=TEST_CREDENTIALS_2.api_secret,
            passphrase=TEST_CREDENTIALS_2.passphrase,
            kraken_account_type=None,
            kraken_futures_api_key=None,
            kraken_futures_api_secret=None,
            binance_selected_trade_pairs=None,
            okx_location=None,
        )
        assert success is False, 'Should not have been able to change credentials'
        assert _saved_credentials(rotki.data.db, identifier) == get_current_credentials(kucoin) == TEST_CREDENTIALS_1, 'Credentials should not have changed'  # noqa: E501

        # Change credentials to correct ones
        success, _ = rotki.exchange_manager.edit_exchange(
            identifier=identifier,
            new_name=None,
            api_key=TEST_CREDENTIALS_3.api_key,
            api_secret=TEST_CREDENTIALS_3.api_secret,
            passphrase=TEST_CREDENTIALS_3.passphrase,
            kraken_account_type=None,
            kraken_futures_api_key=None,
            kraken_futures_api_secret=None,
            binance_selected_trade_pairs=None,
            okx_location=None,
        )
        assert success is True, 'Should have been able to change credentials'
        assert _saved_credentials(rotki.data.db, identifier) == get_current_credentials(kucoin) == TEST_CREDENTIALS_3  # noqa: E501


def test_delete_cannot_interleave_with_setup_persistence(
        rotkehlchen_api_server: APIServer,
) -> None:
    """A delete arriving while setup persists the new exchange must serialize
    after the whole setup, so the DB cannot end up keeping credentials the
    registry lost -- which would resurrect the exchange on the next login"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    delete_results: list[tuple[bool, str]] = []
    original_add_exchange = rotki.data.db.add_exchange
    added = new_connection_identifier()
    delete_thread = threading.Thread(target=lambda: delete_results.append(
        rotki.exchange_manager.delete_exchange(added),
    ))

    def add_exchange_racing_a_delete(*args: Any, **kwargs: Any) -> str:
        delete_thread.start()
        delete_thread.join(timeout=0.5)  # must stay blocked on the registry lock
        assert delete_thread.is_alive(), 'the delete ran during setup persistence'
        with patch('rotkehlchen.db.connections.new_connection_identifier', return_value=added):
            return original_add_exchange(*args, **kwargs)

    with (
        patch('rotkehlchen.exchanges.kucoin.Kucoin.validate_api_key', return_value=(True, '')),
        patch.object(rotki.data.db, 'add_exchange', side_effect=add_exchange_racing_a_delete),
    ):
        identifier, msg = rotki.setup_exchange(
            name='KuCoin',
            connector=LOCATION_KUCOIN,
            api_key=ApiKey('api-key-1'),
            api_secret=TEST_CREDENTIALS_1.api_secret,
            passphrase=TEST_CREDENTIALS_1.passphrase,
        )
    assert identifier == added, msg
    delete_thread.join(timeout=5)
    assert not delete_thread.is_alive()

    # the delete ran after the setup completed, leaving no leftovers anywhere
    assert delete_results == [(True, '')]
    assert LOCATION_KUCOIN not in rotki.exchange_manager.connected_exchanges
    with rotki.data.db.conn.read_ctx() as cursor:
        assert rotki.data.db.get_exchange_credentials(cursor, connectors=[LOCATION_KUCOIN]) == []


def test_binance_selected_pairs_persist_after_restart(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    expected_trade_pairs = ['ETHBTC', 'BTCUSDT', 'NEOBTC']
    with patch('rotkehlchen.exchanges.binance.Binance.validate_api_key', return_value=(True, '')):
        rotki.setup_exchange(
            name='binance 1',
            connector=LOCATION_BINANCE,
            api_key=make_api_key(),
            api_secret=make_api_secret(),
            binance_selected_trade_pairs=expected_trade_pairs,
        )

    # simulate a restart of the app.
    rotki.exchange_manager.connected_exchanges.clear()
    with rotki.data.db.conn.read_ctx() as cursor:
        rotki.exchange_manager.initialize_exchanges(
            connections=rotki.data.db.get_exchange_credentials(cursor),
            database=rotki.data.db,
        )

    assert LOCATION_BINANCE in rotki.exchange_manager.connected_exchanges
    assert len(rotki.exchange_manager.connected_exchanges[LOCATION_BINANCE]) == 1

    selected_pairs = rotki.exchange_manager.connected_exchanges[LOCATION_BINANCE][0].selected_pairs  # type: ignore[attr-defined] # binance has the attribute present
    assert isinstance(selected_pairs, list)
    assert selected_pairs == expected_trade_pairs


def test_bitpanda_credentials_in_db(database: DBHandler) -> None:
    """Regression test for bitpanda credentials should work with NULL api_secret in database.

    Bitpanda only requires api_key, not api_secret. This test verifies the application
    handles this case correctly when retrieving credentials from the database.

    https://github.com/rotki/rotki/issues/9586
    """
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO integration_connections(identifier, name, connector_identifier, '
            'location_identifier, api_key) VALUES (?, ?, ?, ?, ?)',
            (new_connection_identifier(), 'Bitpanda 1', LOCATION_BITPANDA, LOCATION_BITPANDA, make_api_key()),  # noqa: E501
        )

    with database.conn.read_ctx() as cursor:
        credentials = database.get_exchange_credentials(
            cursor=cursor,
            connectors=[LOCATION_BITPANDA],
        )

    assert len(credentials) == 1
    assert credentials[0].api_secret is None
