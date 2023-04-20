from unittest.mock import patch

from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.exchanges.ftx import Ftx
from rotkehlchen.tests.utils.factories import make_api_key, make_api_secret
from rotkehlchen.tests.utils.kraken import MockKraken
from rotkehlchen.types import ApiKey, ApiSecret, ExchangeApiCredentials, Location


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
    ftx1 = Ftx(
        name='mockftx_1',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        ftx_subaccount=None,
    )
    ftx2 = Ftx(
        name='mockftx_2',
        api_key=make_api_key(),
        secret=make_api_secret(),
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
        ftx_subaccount=None,
    )

    exchange_manager.initialize_exchanges({}, database)
    exchange_manager.connected_exchanges[Location.KRAKEN].append(kraken1)
    exchange_manager.connected_exchanges[Location.KRAKEN].append(kraken2)
    exchange_manager.connected_exchanges[Location.FTX].append(ftx1)
    exchange_manager.connected_exchanges[Location.FTX].append(ftx2)
    assert set(exchange_manager.iterate_exchanges()) == {kraken1, kraken2, ftx1, ftx2}

    with database.user_write() as cursor:
        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[kraken1.location_id(), kraken2.location_id()],
        ))
        assert set(exchange_manager.iterate_exchanges()) == {ftx1, ftx2}

        database.set_settings(cursor, ModifiableDBSettings(
            non_syncing_exchanges=[ftx1.location_id()],
        ))
        assert set(exchange_manager.iterate_exchanges()) == {ftx2, kraken1, kraken2}


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


def test_change_credentials(rotkehlchen_api_server) -> None:
    """
    Test that chaning exchange credentials works as expected and if incorrect credentials
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
            ftx_subaccount=None,
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
            ftx_subaccount=None,
        )
        assert success is True, 'Should have been able to change credentials'
        with rotki.data.db.conn.read_ctx() as cursor:
            credentials_in_db = rotki.data.db.get_exchange_credentials(
                cursor=cursor,
                location=Location.KUCOIN,
                name='KuCoin',
            )[Location.KUCOIN][0]
            assert credentials_in_db == get_current_credentials(kucoin) == TEST_CREDENTIALS_3
