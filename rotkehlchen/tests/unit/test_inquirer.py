import datetime
import os
from http import HTTPStatus
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
import requests
from freezegun import freeze_time

from rotkehlchen.assets.asset import Asset, CustomAsset, EvmToken, FiatAsset, UnderlyingToken
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_AAVE,
    A_BTC,
    A_CRV,
    A_DAI,
    A_ETH,
    A_EUR,
    A_KFEE,
    A_LINK,
    A_USD,
    A_USDC,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ethaddress_to_identifier, evm_address_to_identifier
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import (
    globaldb_set_general_cache_values,
    globaldb_set_unique_cache_value,
)
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import (
    CURRENT_PRICE_CACHE_SECS,
    DEFAULT_RATE_LIMIT_WAITING_TIME,
    CurrentPriceOracle,
    Inquirer,
    _query_currency_converterapi,
)
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.tests.utils.constants import A_CNY, A_JPY
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    VELODROME_POOL_PROTOCOL,
    CacheType,
    ChainID,
    EvmTokenKind,
    Price,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.penalizable_oracle import ORACLE_PENALTY_TS

UNDERLYING_ASSET_PRICES = {
    A_AAVE: FVal('100'),
    A_LINK: FVal('25'),
    A_CRV: FVal('10'),
    A_USD: FVal('1'),
}


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in rate limiting of these apis',
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_query_realtime_price_apis(inquirer):
    """Query some of the exchange rates APIs we use.

    For x-rates.com we already have a test in externalapis directory
    """
    result = _query_currency_converterapi(A_USD, A_EUR)
    assert result and isinstance(result, FVal)
    usd = A_USD.resolve_to_fiat_asset()
    result = inquirer.query_historical_fiat_exchange_rates(usd, A_CNY, 1411603200)
    assert result == FVal('6.133938')


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in rate limiting of these apis',
)
def test_query_price_for_not_supported_fiat_asset(inquirer: Inquirer):
    """Check that if we can't find the price for a fiat currency we correctly return None"""
    current_price = inquirer.query_historical_fiat_exchange_rates(
        from_fiat_currency=A_USD.resolve_to_fiat_asset(),
        to_fiat_currency=FiatAsset('NGN'),
        timestamp=ts_now(),
    )
    assert current_price is None


@pytest.mark.skipif(
    'CI' in os.environ,
    reason='This test would contribute in rate limiting of these apis',
)
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_switching_to_backup_api(inquirer):
    count = 0
    original_get = requests.get

    def mock_xratescom_fail(url, timeout):  # pylint: disable=unused-argument
        nonlocal count
        count += 1
        if 'www.x-rates.com' in url:
            return MockResponse(501, '{"msg": "some error")')
        return original_get(url)

    with patch('requests.get', side_effect=mock_xratescom_fail):
        usd, eur = A_USD.resolve_to_fiat_asset(), A_EUR.resolve_to_fiat_asset()
        result, oracle = inquirer._query_fiat_pair(usd, eur)
        assert result and isinstance(result, FVal)
        assert count > 1, 'requests.get should have been called more than once'
        assert oracle == CurrentPriceOracle.FIAT


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_fiat_pair_caching(inquirer):
    def mock_xratescom_exchange_rate(from_currency: Asset):  # pylint: disable=unused-argument
        return {A_EUR: FVal('0.9165902841')}
    usd, eur = A_USD.resolve_to_fiat_asset(), A_EUR.resolve_to_fiat_asset()
    with patch('rotkehlchen.inquirer.get_current_xratescom_exchange_rates', side_effect=mock_xratescom_exchange_rate):  # noqa: E501
        result = inquirer._query_fiat_pair(usd, eur)
        assert result[0] == FVal('0.9165902841')

    # Now outside the mocked response, we should get same value due to caching
    assert inquirer._query_fiat_pair(usd, eur)[0] == FVal('0.9165902841')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_fallback_to_cached_values_within_a_month(inquirer):  # pylint: disable=unused-argument
    def mock_api_remote_fail(url, timeout):  # pylint: disable=unused-argument
        return MockResponse(500, '{"msg": "shit hit the fan"')

    # Get a date 15 days ago and insert a cached entry for EUR JPY then
    # Get a date 31 days ago and insert a cache entry for EUR CNY then
    now = ts_now()
    eurjpy_val = Price(FVal('124.123'))
    cache_data = [HistoricalPrice(
        from_asset=A_EUR,
        to_asset=A_JPY,
        source=HistoricalPriceOracle.XRATESCOM,
        timestamp=Timestamp(now - 86400 * 15),
        price=eurjpy_val,
    ), HistoricalPrice(
        from_asset=A_EUR,
        to_asset=A_CNY,
        source=HistoricalPriceOracle.XRATESCOM,
        timestamp=Timestamp(now - 86400 * 31),
        price=Price(FVal('7.719')),
    )]
    GlobalDBHandler().add_historical_prices(cache_data)

    with patch('requests.get', side_effect=mock_api_remote_fail):
        # We fail to find a response but then go back 15 days and find the cached response
        result = inquirer._query_fiat_pair(
            A_EUR.resolve_to_fiat_asset(),
            A_JPY.resolve_to_fiat_asset(),
        )
        assert result[0] == eurjpy_val
        # The cached response for EUR CNY is too old so we will fail here
        with pytest.raises(RemoteError):
            result = inquirer._query_fiat_pair(
                A_EUR.resolve_to_fiat_asset(),
                A_CNY.resolve_to_fiat_asset(),
            )


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_parsing_forex_cache_works(
        inquirer,
        data_dir,
        mocked_current_prices,
        current_price_oracles_order,
):  # pylint: disable=unused-argument
    price = Price(FVal('124.123'))
    now = ts_now()
    cache_data = [HistoricalPrice(
        from_asset=A_EUR,
        to_asset=A_JPY,
        source=HistoricalPriceOracle.XRATESCOM,
        timestamp=Timestamp(now - 2000),
        price=price,
    )]
    GlobalDBHandler().add_historical_prices(cache_data)
    assert inquirer._query_fiat_pair(A_EUR, A_JPY)[0] == price


@pytest.mark.vcr()
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_fallback_to_coingecko(inquirer: Inquirer):
    """Cryptocompare does not return current prices for some assets.
    For those we are going to be using coingecko"""
    price = inquirer.find_usd_price(EvmToken('eip155:1/erc20:0xFca59Cd816aB1eaD66534D82bc21E7515cE441CF'), skip_onchain=True)  # RARI # noqa: E501
    assert price != ZERO_PRICE
    price = inquirer.find_usd_price(EvmToken('eip155:1/erc20:0x679131F591B4f369acB8cd8c51E68596806c3916'), skip_onchain=True)  # TLN # noqa: E501
    assert price != ZERO_PRICE


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_cache(inquirer, freezer):  # pylint: disable=unused-argument
    call_count = 0

    def mock_query_price(from_asset, to_asset, match_main_currency):  # pylint: disable=unused-argument
        assert from_asset.identifier == 'ETH'
        assert to_asset.identifier == 'USD'
        nonlocal call_count
        if call_count == 0:
            price = Price(FVal('1'))
        elif call_count in {1, 2}:
            price = Price(FVal('2'))
        else:
            raise AssertionError('Called too many times for this test')

        call_count += 1
        return price, False

    cc_patch = patch.object(
        inquirer._cryptocompare,
        'query_current_price',
        wraps=mock_query_price,
    )
    inquirer.set_oracles_order(oracles=[CurrentPriceOracle.CRYPTOCOMPARE])

    with cc_patch as cc:
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 1
        assert price == Price(FVal('1'))

        # next time we run, make sure it's the cache
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 1
        assert price == Price(FVal('1'))

        # now move forward in time to invalidate the cache
        freezer.move_to(datetime.datetime.fromtimestamp(
            ts_now() + CURRENT_PRICE_CACHE_SECS + 1,
            tz=datetime.timezone.utc,
        ))
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 2
        assert price == Price(FVal('2'))

        # also test that ignore_cache works
        price = inquirer.find_usd_price(A_ETH)
        assert cc.call_count == 2
        assert price == Price(FVal('2'))
        price = inquirer.find_usd_price(A_ETH, ignore_cache=True)
        assert cc.call_count == 3
        assert price == Price(FVal('2'))


def test_set_oracles_order(inquirer):
    inquirer.set_oracles_order([CurrentPriceOracle.COINGECKO])

    assert inquirer._oracles == [CurrentPriceOracle.COINGECKO]
    assert inquirer._oracle_instances == [inquirer._coingecko]


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_all_rate_limited_in_last(inquirer):
    """Test zero price is returned when all the oracles have exceeded the rate
    limits requesting the USD price of an asset.
    """
    class OracleMock(CurrentPriceOracleInterface):
        def __init__(self, name):
            self.rate_limited_in_last_call_count = 0
            self.query_current_price_call_count = 0
            super().__init__(name)

        def rate_limited_in_last(self, seconds):
            self.rate_limited_in_last_call_count += 1
            return True

        def query_current_price(self, from_asset, to_asset, match_main_currency):
            self.query_current_price_call_count += 1

    inquirer._oracle_instances = [OracleMock('x') for _ in inquirer._oracles]

    price = inquirer.find_usd_price(A_BTC)
    assert price == ZERO_PRICE
    for oracle_instance in inquirer._oracle_instances:
        assert oracle_instance.rate_limited_in_last_call_count == 1
        assert oracle_instance.query_current_price_call_count == 0


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_no_price_found(inquirer):
    """Test zero price is returned when all the oracles returned zero price
    requesting the USD price of an asset.
    """
    inquirer._oracle_instances = [MagicMock() for _ in inquirer._oracles]

    for oracle_instance in inquirer._oracle_instances:
        oracle_instance.query_current_price.return_value = (ZERO_PRICE, False)

    price = inquirer.find_usd_price(A_BTC)

    assert price == ZERO_PRICE
    for oracle_instance in inquirer._oracle_instances:
        assert oracle_instance.query_current_price.call_count == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_via_second_oracle(inquirer):
    """Test price is returned via the second oracle when the first oracle fails
    requesting the USD price of an asset.
    """
    inquirer._oracle_instances = [MagicMock() for _ in inquirer._oracles]

    expected_price = Price(FVal('30000'))
    inquirer._oracle_instances[0].query_current_price.side_effect = RemoteError
    inquirer._oracle_instances[1].query_current_price.return_value = (expected_price, False)

    price = inquirer.find_usd_price(A_BTC)

    assert price == expected_price
    for oracle_instance in inquirer._oracle_instances[0:2]:
        assert oracle_instance.query_current_price.call_count == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('mocked_current_prices', [UNDERLYING_ASSET_PRICES])
@pytest.mark.parametrize('ignore_mocked_prices_for', [['eip155:1/erc20:0xc37b40ABdB939635068d3c5f13E7faF686F03B65', 'USD']])  # noqa: E501
def test_price_underlying_tokens(inquirer, globaldb):
    aave_weight, link_weight, crv_weight = FVal('0.6'), FVal('0.2'), FVal('0.2')
    address = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
    identifier = ethaddress_to_identifier(address)
    token = EvmToken.initialize(
        address=address,
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Test',
        symbol='YAB',
        underlying_tokens=[
            UnderlyingToken(address=A_AAVE.resolve_to_evm_token().evm_address, token_kind=EvmTokenKind.ERC20, weight=aave_weight),  # noqa: E501
            UnderlyingToken(address=A_LINK.resolve_to_evm_token().evm_address, token_kind=EvmTokenKind.ERC20, weight=link_weight),  # noqa: E501
            UnderlyingToken(address=A_CRV.resolve_to_evm_token().evm_address, token_kind=EvmTokenKind.ERC20, weight=crv_weight),  # noqa: E501
        ],
    )
    globaldb.add_asset(token)

    price = inquirer.find_price(EvmToken(identifier), A_USD)
    assert price == FVal(67)


@pytest.mark.vcr()
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_uniswap_v2_lp_token_price(inquirer, ethereum_manager, globaldb):
    """Tests that the Uniswap v2 lp token's price is correctly found. The special price
    calculation that is needed, is applied based on the protocol attribute of the lp token"""
    identifier = ethaddress_to_identifier(string_to_evm_address('0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'))  # LINK ETH POOL  # noqa: E501
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(  # the protocol attribute is missing from the packaged db for this token as of this commit and is necessary for price calculation  # noqa: E501
            'UPDATE evm_tokens SET protocol=? WHERE identifier=?',
            ('UNI-V2', identifier),
        )
    inquirer.inject_evm_managers([(ChainID.ETHEREUM, ethereum_manager)])
    price = inquirer.find_lp_price_from_uniswaplike_pool(token=EvmToken(identifier))
    assert price is not None


@pytest.mark.vcr()
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_velodrome_v2_lp_token_price(inquirer, optimism_manager):
    """Tests that the Velodrome v2 lp token's price is correctly found. The special price
    calculation that is needed, is applied based on the protocol attribute of the lp token"""
    token = get_or_create_evm_token(
        userdb=optimism_manager.node_inquirer.database,
        evm_address=string_to_evm_address('0xd25711EdfBf747efCE181442Cc1D8F5F8fc8a0D3'),
        chain_id=ChainID.OPTIMISM,
        protocol=VELODROME_POOL_PROTOCOL,
    )
    inquirer.inject_evm_managers([(ChainID.OPTIMISM, optimism_manager)])
    price = inquirer.find_lp_price_from_uniswaplike_pool(token=token)
    assert price is not None


@pytest.mark.vcr()
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_curve_lp_token_price(inquirer_defi, ethereum_manager):
    with GlobalDBHandler().conn.write_ctx() as write_cursor:  # querying curve lp token price normally triggers curve cache query. Set all query ts to now, so it does not happen.  # noqa: E501
        write_cursor.execute('UPDATE general_cache SET last_queried_ts=? WHERE key=?', (ts_now(), 'CURVE_LP_TOKENS'))  # noqa: E501

    lp_token_address = '0xA3D87FffcE63B53E0d54fAa1cc983B7eB0b74A9c'
    pool_address = '0xc5424B857f758E906013F3555Dad202e4bdB4567'
    identifier = ethaddress_to_identifier(lp_token_address)
    inquirer_defi.inject_evm_managers([(ChainID.ETHEREUM, ethereum_manager)])
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.CURVE_LP_TOKENS,),
            values=[lp_token_address],
        )
        globaldb_set_unique_cache_value(
            write_cursor=write_cursor,
            key_parts=(CacheType.CURVE_POOL_ADDRESS, lp_token_address),
            value=pool_address,
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.CURVE_POOL_TOKENS, pool_address, '0'),
            values=['0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.CURVE_POOL_TOKENS, pool_address, '1'),
            values=['0x5e74C9036fb86BD7eCdcb084a0673EFc32eA31cb'],
        )
    price = inquirer_defi.find_curve_pool_price(EvmToken(identifier))
    assert price is not None
    # Check that the protocol is correctly caught by the inquirer
    assert price == inquirer_defi.find_usd_price(EvmToken(identifier))


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_kfee_price(inquirer):
    price = inquirer.find_usd_price(A_KFEE)
    assert FVal(price) == FVal(0.01)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_asset_with_no_api_oracles(inquirer_defi):
    """
    Test that uniswap oracles correctly query USD price of assets
    """
    price = inquirer_defi.find_usd_price(A_1INCH, ignore_cache=True)
    inquirer_defi.set_oracles_order(
        oracles=[CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.CRYPTOCOMPARE],
    )
    price_uni_v2 = inquirer_defi.find_usd_price(A_1INCH, ignore_cache=True)
    inquirer_defi.set_oracles_order(
        oracles=[CurrentPriceOracle.UNISWAPV3, CurrentPriceOracle.CRYPTOCOMPARE],
    )
    price_uni_v3 = inquirer_defi.find_usd_price(A_1INCH, ignore_cache=True)

    assert price != ZERO_PRICE
    assert price != price_uni_v2
    assert price.is_close(price_uni_v2, max_diff='0.05')
    assert price.is_close(price_uni_v3, max_diff='0.05')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_price_non_ethereum_evm_token(inquirer_defi, globaldb):
    """
    This test checks that `inquirer.find_usd_price` does not fail with
    "'NoneType' object has no attribute 'underlying_tokens'" when an evm token
    that's not from the Ethereum chain is passed.

    https://github.com/rotki/rotki/blob/a2cc1676f874ece1ddfe84686d8dfcc82ed6ffcf/rotkehlchen/inquirer.py#L611
    """
    address = string_to_evm_address('0x2656f02bc30427Ed9d380E20CEc5E04F5a7A50FE')
    evm_address_to_identifier(
        address=address,
        chain_id=ChainID.BINANCE,
        token_type=EvmTokenKind.ERC20,
    )
    token = EvmToken.initialize(
        address=address,
        chain_id=ChainID.BINANCE,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='SLOUGI',
        symbol='SLOUGI',
        underlying_tokens=None,
    )
    globaldb.add_asset(token)

    # Since the asset is not from a valid chain the query will fail and return zero
    assert inquirer_defi.find_usd_price(EvmToken(token.identifier)) == ZERO


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_price_for_custom_assets(inquirer, database, globaldb):
    db_custom_assets = DBCustomAssets(database)
    db_custom_assets.add_custom_asset(CustomAsset.initialize(
        identifier='id',
        name='my name',
        custom_asset_type='oh my type',
    ))
    asset = Asset('id')
    # check that inquirer doesn't fail if there is no price for a custom asset
    assert inquirer.find_usd_price(asset) == ZERO
    globaldb.add_manual_latest_price(
        from_asset=asset,
        to_asset=A_USD,
        price=Price(FVal(10)),
    )
    inquirer.remove_cached_current_price_entry((asset, A_USD))
    assert inquirer.find_usd_price(asset) == Price(FVal(10))


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_coingecko_handles_rate_limit(inquirer):
    """
    Test that the mechanism to ignore coingecko when the user gets rate limited works as expected
    """
    coingecko_api_calls = 0

    def mock_coingecko_return(url, *args, **kwargs):  # pylint: disable=unused-argument
        nonlocal coingecko_api_calls
        coingecko_api_calls += 1
        return MockResponse(HTTPStatus.TOO_MANY_REQUESTS, '{}')

    coingecko_patch = patch.object(inquirer._coingecko.session, 'get', side_effect=mock_coingecko_return)  # noqa: E501
    inquirer.set_oracles_order(oracles=[CurrentPriceOracle.COINGECKO])
    with coingecko_patch:
        # Query a price and get rate limited
        price = inquirer.find_usd_price(A_ETH)
        assert price == ZERO_PRICE
        assert inquirer._coingecko.last_rate_limit > 0
        # Now try again, since we are rate limited the price query wil fail
        assert inquirer.find_usd_price(A_ETH, ignore_cache=True) == ZERO_PRICE
        # Change the last_rate_limit time to allow for further calls
        inquirer._coingecko.last_rate_limit = ts_now() - (DEFAULT_RATE_LIMIT_WAITING_TIME + 10)
        inquirer.find_usd_price(A_ETH, ignore_cache=True)
        # Check that the last price query contacted coingecko api
        assert coingecko_api_calls == 2


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_punishing_of_oracles_works(inquirer):
    defillama_patch = patch.object(inquirer._defillama.session, 'get', return_value=MockResponse(HTTPStatus.OK, '{"coins":{"coingecko:bitcoin":{"price":100.14,"symbol":"BTC","timestamp":1668592376,"confidence":0.99}}}'))  # noqa: E501
    coingecko_patch = patch.object(inquirer._coingecko.session, 'get', side_effect=requests.exceptions.RequestException('An unexpected error occurred!'))  # noqa: E501
    inquirer.set_oracles_order(oracles=[CurrentPriceOracle.COINGECKO, CurrentPriceOracle.DEFILLAMA])  # noqa: E501

    with coingecko_patch as coingecko_mock, defillama_patch as defillama_mock:
        for counter in range(1, 7):
            assert inquirer.find_usd_price(A_BTC, ignore_cache=True) > ZERO_PRICE
            # check that coingecko is not called the sixth time and is already penalized.
            if counter == 6:
                assert coingecko_mock.call_count == 5
                assert inquirer._coingecko.is_penalized() is True
            else:
                assert coingecko_mock.called is True
                assert defillama_mock.called is True

        # move the current time forward and check that coingecko is still penalized
        with freeze_time(datetime.datetime.fromtimestamp(
                ts_now() + ORACLE_PENALTY_TS / 2,
                tz=datetime.timezone.utc,
        )):
            assert inquirer._coingecko.is_penalized() is True

        # move the current time forward and check that coingecko is no longer penalized
        with freeze_time(datetime.datetime.fromtimestamp(
                ts_now() + ORACLE_PENALTY_TS + 1,
                tz=datetime.timezone.utc,
        )):
            assert inquirer._coingecko.is_penalized() is False


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_yearn_vaults_v2_price(inquirer_defi, globaldb):
    """
    When this test was written yearn vaults query was relying in the underlying token
    being correctly recorded in the global DB. To emulate that we make sure one is
    missing.

    This test makes sure if underlying token is missing the chain is asked for it
    and it's recorded in the DB, so that next time price is asked, that remote query
    is not done again.
    """
    yvusdc = EvmToken('eip155:1/erc20:0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9')
    yvdai = EvmToken('eip155:1/erc20:0xdA816459F1AB5631232FE5e97a05BBBb94970c95')

    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE from underlying_tokens_list WHERE parent_token_entry=?',
            (yvdai.identifier,),
        )

    for token, underlying_token in ((yvusdc, A_USDC), (yvdai, A_DAI)):
        price = inquirer_defi.find_yearn_price(token)
        assert price is not None

        with globaldb.conn.read_ctx() as cursor:
            result = globaldb.fetch_underlying_tokens(cursor, token.identifier)
            assert result and result[0].address == underlying_token.resolve_to_evm_token().evm_address  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_protocol_price_falllback_to_oracle(inquirer_defi):
    """Test that if the onchain price query fails for a known protocol token,
    the external oracles are still queried and provide us (potentially) with an answer
    """
    yvusdc = EvmToken('eip155:1/erc20:0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9')
    yearn_patch = patch('rotkehlchen.inquirer.get_underlying_asset_price', side_effect=lambda *args: (None, None))  # noqa: E501
    with yearn_patch:
        price = inquirer_defi.find_usd_price(yvusdc)
    assert price is not None and price != ZERO


@pytest.mark.vcr()
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_cache_is_hit_for_collection(inquirer: Inquirer):
    """Test that the price for a collection is saved to cache and not query for every asset"""
    wsteth = Asset('eip155:1/erc20:0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0')
    wsteth_op = Asset('eip155:10/erc20:0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb')
    with mock.patch.object(
        Inquirer,
        '_query_oracle_instances',
        wraps=inquirer._query_oracle_instances,
    ) as oracle_query:
        inquirer.find_usd_price(wsteth)
        assert (wsteth_op, A_USD) in inquirer._cached_current_price.cache
        inquirer.find_usd_price(wsteth_op)

    assert oracle_query.call_count == 1
