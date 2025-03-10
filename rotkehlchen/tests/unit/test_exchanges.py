from typing import TYPE_CHECKING
from unittest.mock import patch

from rotkehlchen.api.server import APIServer
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.exchanges.binance import Binance
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.types import ApiKey, ApiSecret, ExchangeApiCredentials, Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


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

    exchange_manager.initialize_exchanges({}, database)
    exchange_manager.connected_exchanges[Location.KRAKEN].append(kraken1)
    exchange_manager.connected_exchanges[Location.KRAKEN].append(kraken2)
    exchange_manager.connected_exchanges[Location.BINANCE].append(binance1)
    exchange_manager.connected_exchanges[Location.BINANCE].append(binance2)
    assert set(exchange_manager.iterate_exchanges()) == {kraken1, kraken2, binance1, binance2}

    with database.user_write() as cursor:
        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[kraken1.location_id(), kraken2.location_id()],
        ))
        assert set(exchange_manager.iterate_exchanges()) == {binance1, binance2}

        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[binance1.location_id()],
        ))
        assert set(exchange_manager.iterate_exchanges()) == {binance2, kraken1, kraken2}


TEST_CREDENTIALS_1 = ExchangeApiCredentials(
    name='KuCoin',
    location=Location.KUCOIN,
    api_key=ApiKey('api-key-1'),
    api_secret=ApiSecret(b'api-secret-1'),
    passphrase='passphrase-1',
)

TEST_CREDENTIALS_2 = ExchangeApiCredentials(
    name='KuCoin',
    location=Location.KUCOIN,
    api_key=ApiKey('api-key-2'),
    api_secret=ApiSecret(b'api-secret-2'),
    passphrase='passphrase-2',
)

TEST_CREDENTIALS_3 = ExchangeApiCredentials(
    name='KuCoin',
    location=Location.KUCOIN,
    api_key=ApiKey('api-key-3'),
    api_secret=ApiSecret(b'api-secret-3'),
    passphrase='passphrase-3',
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

    def get_current_credentials(kucoin) -> ExchangeApiCredentials:
        return ExchangeApiCredentials(
            name=kucoin.name,
            location=Location.KUCOIN,
            api_key=kucoin.api_key,
            api_secret=kucoin.secret,
            passphrase=kucoin.api_passphrase,
        )

    with patch('rotkehlchen.exchanges.kucoin.Kucoin.validate_api_key', mock_kucoin_validate_api_key):  # noqa: E501
        # Setup with correct credentials
        rotki.setup_exchange(
            name='KuCoin',
            location=Location.KUCOIN,
            api_key=TEST_CREDENTIALS_1.api_key,
            api_secret=TEST_CREDENTIALS_1.api_secret,
            passphrase=TEST_CREDENTIALS_1.passphrase,
        )
        kucoin = rotki.exchange_manager.connected_exchanges[Location.KUCOIN][0]
        with rotki.data.db.conn.read_ctx() as cursor:
            credentials_in_db = rotki.data.db.get_exchange_credentials(
                cursor=cursor,
                location=Location.KUCOIN,
                name='KuCoin',
            )[Location.KUCOIN][0]
            assert credentials_in_db == get_current_credentials(kucoin) == TEST_CREDENTIALS_1

        # Try to change credentials to incorrect ones
        success, _ = rotki.exchange_manager.edit_exchange(
            name='KuCoin',
            location=Location.KUCOIN,
            new_name=None,
            api_key=TEST_CREDENTIALS_2.api_key,
            api_secret=TEST_CREDENTIALS_2.api_secret,
            passphrase=TEST_CREDENTIALS_2.passphrase,
            kraken_account_type=None,
            binance_selected_trade_pairs=None,
        )
        assert success is False, 'Should not have been able to change credentials'
        with rotki.data.db.conn.read_ctx() as cursor:
            credentials_in_db = rotki.data.db.get_exchange_credentials(
                cursor=cursor,
                location=Location.KUCOIN,
                name='KuCoin',
            )[Location.KUCOIN][0]
            assert credentials_in_db == get_current_credentials(kucoin) == TEST_CREDENTIALS_1, 'Credentials should not have changed'  # noqa: E501

        # Change credentials to correct ones
        success, _ = rotki.exchange_manager.edit_exchange(
            name='KuCoin',
            location=Location.KUCOIN,
            new_name=None,
            api_key=TEST_CREDENTIALS_3.api_key,
            api_secret=TEST_CREDENTIALS_3.api_secret,
            passphrase=TEST_CREDENTIALS_3.passphrase,
            kraken_account_type=None,
            binance_selected_trade_pairs=None,
        )
        assert success is True, 'Should have been able to change credentials'
        with rotki.data.db.conn.read_ctx() as cursor:
            credentials_in_db = rotki.data.db.get_exchange_credentials(
                cursor=cursor,
                location=Location.KUCOIN,
                name='KuCoin',
            )[Location.KUCOIN][0]
            assert credentials_in_db == get_current_credentials(kucoin) == TEST_CREDENTIALS_3


def test_binance_selected_pairs_persist_after_restart(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    expected_trade_pairs = ['ETHBTC', 'BTCUSDT', 'NEOBTC']
    with patch('rotkehlchen.exchanges.binance.Binance.validate_api_key', return_value=(True, '')):
        rotki.setup_exchange(
            name='binance 1',
            location=Location.BINANCE,
            api_key=make_api_key(),
            api_secret=make_api_secret(),
            binance_selected_trade_pairs=expected_trade_pairs,
        )

    # simulate a restart of the app.
    rotki.exchange_manager.connected_exchanges.clear()
    with rotki.data.db.conn.read_ctx() as cursor:
        exchange_credentials = rotki.data.db.get_exchange_credentials(cursor)
        rotki.exchange_manager.initialize_exchanges(
            exchange_credentials=exchange_credentials,
            database=rotki.data.db,
        )

    assert Location.BINANCE in rotki.exchange_manager.connected_exchanges
    assert len(rotki.exchange_manager.connected_exchanges[Location.BINANCE]) == 1

    selected_pairs = rotki.exchange_manager.connected_exchanges[Location.BINANCE][0].selected_pairs  # type: ignore[attr-defined] # binance has the attribute present
    assert isinstance(selected_pairs, list)
    assert selected_pairs == expected_trade_pairs


def test_bitpanda_credentials_in_db(database: 'DBHandler') -> None:
    """Regression test for bitpanda credentials should work with NULL api_secret in database.

    Bitpanda only requires api_key, not api_secret. This test verifies the application
    handles this case correctly when retrieving credentials from the database.

    https://github.com/rotki/rotki/issues/9586
    """
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO user_credentials(name, location, api_key) VALUES (?, ?, ?)',
            ('Bitpanda 1', Location.BITPANDA.serialize_for_db(), make_api_key()),
        )

    with database.conn.read_ctx() as cursor:
        credentials = database.get_exchange_credentials(
            cursor=cursor,
            location=Location.BITPANDA,
        )

    assert len(credentials[Location.BITPANDA]) == 1
