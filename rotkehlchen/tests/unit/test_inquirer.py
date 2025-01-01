import datetime
import math
import os
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
import requests
from freezegun import freeze_time
from web3 import HTTPProvider, Web3

from rotkehlchen.assets.asset import Asset, CustomAsset, EvmToken, FiatAsset, UnderlyingToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.evm.contracts import find_matching_event_abi
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.curve.constants import CURVE_CHAIN_ID
from rotkehlchen.chain.evm.decoding.curve.curve_cache import (
    CurvePoolData,
    _query_curve_data_from_api,
    query_curve_data,
)
from rotkehlchen.chain.evm.node_inquirer import _query_web3_get_logs, construct_event_filter_params
from rotkehlchen.chain.evm.types import NodeName, string_to_evm_address
from rotkehlchen.chain.gnosis.transactions import ADDED_RECEIVER_ABI, BLOCKREWARDS_ADDRESS
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_POL_HARDFORK
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_AAVE,
    A_BSQ,
    A_BTC,
    A_CRV,
    A_DAI,
    A_ETH,
    A_EUR,
    A_KFEE,
    A_LINK,
    A_POLYGON_POS_MATIC,
    A_USD,
    A_USDC,
    A_USDT,
    A_WETH_ARB,
    A_XDAI,
    A_YV1_DAI,
    A_YV1_USDC,
    A_YV1_WETH,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.constants.resolver import ethaddress_to_identifier, evm_address_to_identifier
from rotkehlchen.db.custom_assets import DBCustomAssets
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import (
    BTC_PER_BSQ,
    CURRENT_PRICE_CACHE_SECS,
    DEFAULT_RATE_LIMIT_WAITING_TIME,
    CurrentPriceOracle,
    Inquirer,
    _query_currency_converterapi,
)
from rotkehlchen.interfaces import CurrentPriceOracleInterface
from rotkehlchen.tests.conftest import TestEnvironment, requires_env
from rotkehlchen.tests.unit.decoders.test_curve_lend import (
    fixture_ethereum_vault_token,  # noqa: F401
    fixture_ethereum_vault_underlying_token,  # noqa: F401
)
from rotkehlchen.tests.unit.test_cost_basis import ONE_PRICE
from rotkehlchen.tests.utils.constants import A_CNY, A_JPY
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.morpho import create_ethereum_morpho_vault_token
from rotkehlchen.types import (
    EVM_CHAINS_WITH_TRANSACTIONS,
    VELODROME_POOL_PROTOCOL,
    YEARN_VAULTS_V3_PROTOCOL,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EvmTokenKind,
    Price,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
    from rotkehlchen.db.dbhandler import DBHandler


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
    GlobalDBHandler.add_historical_prices(cache_data)

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


@pytest.mark.vcr
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

    def mock_query_price(from_asset, to_asset):  # pylint: disable=unused-argument
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
        return price

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
            tz=datetime.UTC,
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

        def query_current_price(self, from_asset, to_asset):
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
        oracle_instance.query_current_price.return_value = ZERO_PRICE

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
    inquirer._oracle_instances[1].query_current_price.return_value = expected_price

    price = inquirer.find_usd_price(A_BTC)

    assert price == expected_price
    for oracle_instance in inquirer._oracle_instances[0:2]:
        assert oracle_instance.query_current_price.call_count == 1


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_usd_price_manual_prices_preference(inquirer, globaldb):
    """Test that manual prices is checked first before all other oracles
    and special price calculations."""
    inquirer._oracle_instances = [MagicMock() for _ in inquirer._oracles]
    manual_price = Price(FVal('30000'))
    globaldb.add_manual_latest_price(from_asset=A_BTC, to_asset=A_USD, price=manual_price)

    assert inquirer.find_usd_price(A_BTC) == manual_price

    for oracle_instance in inquirer._oracle_instances:
        assert oracle_instance.query_current_price.call_count == 0


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


@pytest.mark.vcr
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
    AssetResolver.clean_memory_cache(identifier)
    inquirer.inject_evm_managers([(ChainID.ETHEREUM, ethereum_manager)])
    price = inquirer.find_lp_price_from_uniswaplike_pool(token=EvmToken(identifier))
    assert price is not None


@pytest.mark.vcr
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_curve_lp_token_price(inquirer: 'Inquirer', blockchain: 'ChainsAggregator'):
    tested_tokens: dict[ChainID, tuple[str, FVal]] = {
        ChainID.ETHEREUM: ('0xA3D87FffcE63B53E0d54fAa1cc983B7eB0b74A9c', FVal('3584.181065')),
        # 3CRV-OP-gauge
        ChainID.OPTIMISM: ('0x4456d13Fc6736e8e8330394c0C622103E06ea419', FVal('1864.150003')),
        # Curve.fi amDAI/amUSDC/amUSDT (am3CRV)
        ChainID.POLYGON_POS: ('0xE7a24EF0C5e95Ffb0f6684b813A78F2a3AD7D171', FVal('1.129260')),
        # crvUSDT-gauge
        ChainID.ARBITRUM_ONE: ('0xB08FEf57bFcc5f7bF0EF69C0c090849d497C8F8A', FVal('2.025168')),
        # tricrypto
        ChainID.BASE: ('0x63Eb7846642630456707C3efBb50A03c79B89D81', FVal('1.011604')),
        # crvusdusdt-gauge
        ChainID.GNOSIS: ('0xC2EfDbC1a21D82A677380380eB282a963A6A6ada', FVal('0.997623')),
    }

    inquirer.inject_evm_managers([
        (chain.to_chain_id(), blockchain.get_chain_manager(chain))
        for chain in EVM_CHAINS_WITH_TRANSACTIONS
    ])

    def mock_query_curve_data_from_api(
            chain_id: ChainID,
            existing_pools: set[ChecksumEvmAddress],
    ) -> list[CurvePoolData]:
        for pool in _query_curve_data_from_api(
            chain_id=chain_id,
            existing_pools=existing_pools,
        ):
            if tested_tokens[chain_id][0] in {pool.lp_token_address, pool.gauge_address}:
                return [pool]
        return []

    with patch(
        target='rotkehlchen.chain.evm.decoding.curve.curve_cache._query_curve_data_from_api',
        new=mock_query_curve_data_from_api,
    ):
        inquirer.set_oracles_order([CurrentPriceOracle.DEFILLAMA])
        for chain_id in CURVE_CHAIN_ID:
            manager = inquirer.get_evm_manager(chain_id)
            manager.node_inquirer.ensure_cache_data_is_updated(
                cache_type=CacheType.CURVE_LP_TOKENS,
                query_method=query_curve_data,
                chain_id=manager.node_inquirer.chain_id,
                cache_key_parts=(str(manager.node_inquirer.chain_id.serialize_for_db()),),
            )

    with GlobalDBHandler().conn.write_ctx() as write_cursor:  # querying curve lp token price normally triggers curve cache query. Set all query ts to now, so it does not happen.  # noqa: E501
        write_cursor.execute('UPDATE general_cache SET last_queried_ts=? WHERE key LIKE ?', (ts_now(), 'CURVE_LP_TOKENS%'))  # noqa: E501

    for chain_id, (address, price) in tested_tokens.items():
        assert inquirer.find_usd_price(EvmToken(evm_address_to_identifier(
            address=address,
            chain_id=chain_id,
            token_type=EvmTokenKind.ERC20,
        ))).is_close(price)


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
    Inquirer._cached_current_price.remove((asset, A_USD))
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
        # Now try again, since we are rate limited the price query will fail
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
        penalty_duration = CachedSettings().oracle_penalty_duration
        with freeze_time(datetime.datetime.fromtimestamp(
                ts_now() + penalty_duration / 2,
                tz=datetime.UTC,
        )):
            assert inquirer._coingecko.is_penalized() is True

        # move the current time forward and check that coingecko is no longer penalized
        with freeze_time(datetime.datetime.fromtimestamp(
                ts_now() + penalty_duration + 1,
                tz=datetime.UTC,
        )):
            assert inquirer._coingecko.is_penalized() is False


@pytest.mark.vcr(filter_query_parameters=['apikey'])
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
        price = inquirer_defi.find_yearn_price(token, 'YEARN_VAULT_V2')
        assert price is not None

        with globaldb.conn.read_ctx() as cursor:
            result = globaldb.fetch_underlying_tokens(cursor, token.identifier)
            assert result and result[0].address == underlying_token.resolve_to_evm_token().evm_address  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_yearn_vaults_v3_price(
        database: 'DBHandler',
        inquirer_defi: 'Inquirer',
        globaldb: 'GlobalDBHandler',
) -> None:
    """Check that we can find the price of a yearn v3 vault asset.
    The v3 assets are retrieved via query_yearn_vaults when the app runs,
    so the vault asset isn't in the global db yet and must be added manually here.
    """
    crvusd_address = string_to_evm_address('0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E')
    yvcrvusd = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xBF319dDC2Edc1Eb6FDf9910E39b37Be221C8805F'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='yvcrvUSD-2',
        name='crvUSD-2 yVault',
        decimals=18,
        protocol=YEARN_VAULTS_V3_PROTOCOL,
        started=Timestamp(1713104219),
        underlying_tokens=[UnderlyingToken(
            address=crvusd_address,
            token_kind=EvmTokenKind.ERC20,
            weight=ONE,
        )],
    )

    price = inquirer_defi.find_yearn_price(yvcrvusd, 'YEARN_VAULT_V3')
    assert price is not None

    with globaldb.conn.read_ctx() as cursor:
        result = globaldb.fetch_underlying_tokens(cursor, yvcrvusd.identifier)
        assert result and result[0].address == crvusd_address


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_gearbox_lp_price(inquirer: 'Inquirer', arbitrum_one_manager: 'ArbitrumOneManager'):
    dwethv3 = EvmToken('eip155:42161/erc20:0x04419d3509f13054f60d253E0c79491d9E683399')
    sdwethv3 = EvmToken('eip155:42161/erc20:0x6773fF780Dd38175247795545Ee37adD6ab6139a')

    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE from underlying_tokens_list WHERE parent_token_entry=?',
            (sdwethv3.identifier,),
        )
    inquirer.inject_evm_managers([(ChainID.ARBITRUM_ONE, arbitrum_one_manager)])
    for token, underlying_token in ((sdwethv3, A_WETH_ARB), (dwethv3, A_WETH_ARB)):
        price = inquirer.find_gearbox_price(token)
        assert price is not None

        with GlobalDBHandler().conn.read_ctx() as cursor:
            result = GlobalDBHandler.fetch_underlying_tokens(cursor, token.identifier)
            assert result and result[0].address == underlying_token.resolve_to_evm_token().evm_address  # noqa: E501


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_protocol_price_fallback_to_oracle(inquirer_defi):
    """Test that if the onchain price query fails for a known protocol token,
    the external oracles are still queried and provide us (potentially) with an answer
    """
    yvusdc = EvmToken('eip155:1/erc20:0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9')
    yearn_patch = patch('rotkehlchen.inquirer.get_underlying_asset_price', side_effect=lambda *args: (None, None))  # noqa: E501
    with yearn_patch:
        price = inquirer_defi.find_usd_price(yvusdc)
    assert price is not None and price != ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_yearn_v1_vault_token_price(inquirer_defi):
    """Regression test for https://github.com/rotki/rotki/pull/8838
    Similar prices were found by this method with and without the change in PR 8838
    """
    assert inquirer_defi.find_usd_price(A_YV1_USDC).is_close(FVal(1.10959), max_diff=1e-5)
    assert inquirer_defi.find_usd_price(A_YV1_WETH).is_close(FVal(2555.94460), max_diff=1e-5)
    assert inquirer_defi.find_usd_price(A_YV1_DAI).is_close(FVal(1.15431), max_diff=1e-5)


@pytest.mark.vcr
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


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@requires_env([TestEnvironment.NIGHTLY])
def test_usd_price(inquirer: Inquirer, globaldb: GlobalDBHandler):
    """Check that price is queried for tokens in different chains using defillama"""
    inquirer.set_oracles_order(oracles=[CurrentPriceOracle.DEFILLAMA])
    globaldb.add_asset(EvmToken.initialize(
        address=string_to_evm_address('0x66a2A913e447d6b4BF33EFbec43aAeF87890FBbc'),
        chain_id=ChainID.BOBA,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='USDC',
        symbol='USDC',
    ))
    globaldb.add_asset(EvmToken.initialize(
        address=string_to_evm_address('0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'),
        chain_id=ChainID.AVALANCHE,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='Wrapped Avax',
        symbol='WAVAX',
    ))

    globaldb.add_asset(EvmToken.initialize(
        address=string_to_evm_address('0x15C3Eb3B621d1Bff62CbA1c9536B7c1AE9149b57'),
        chain_id=ChainID.EVMOS,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='USD Coin on Axelar',
        symbol='USDC',
    ))
    globaldb.add_asset(EvmToken.initialize(
        address=string_to_evm_address('0xA8CE8aee21bC2A48a5EF670afCc9274C7bbbC035'),
        chain_id=ChainID.POLYGON_ZKEVM,
        token_kind=EvmTokenKind.ERC20,
        decimals=18,
        name='USD Coin',
        symbol='USDC',
    ))

    for token in (  # era, nova and celo are not tracked by coingecko
        Asset('eip155:1/erc20:0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72'),  # ethereum
        Asset('eip155:10/erc20:0x4200000000000000000000000000000000000006'),  # optimism
        Asset('eip155:56/erc20:0x111111111117dC0aa78b770fA6A738034120C302'),  # binance
        Asset('eip155:100/erc20:0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d'),  # gnosis
        Asset('eip155:137/erc20:0x0000000000000000000000000000000000001010'),  # polygon
        Asset('eip155:250/erc20:0x841FAD6EAe12c286d1Fd18d1d525DFfA75C7EFFE'),  # fantom
        Asset('eip155:8453/erc20:0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA'),  # base
        Asset('eip155:42161/erc20:0x5979D7b546E38E414F7E9822514be443A4800529'),  # arb
        Asset('eip155:43114/erc20:0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'),  # avax
        Asset('eip155:288/erc20:0x66a2A913e447d6b4BF33EFbec43aAeF87890FBbc'),  # boba
        Asset('eip155:1101/erc20:0xA8CE8aee21bC2A48a5EF670afCc9274C7bbbC035'),  # zkevm
    ):
        price = inquirer.find_usd_price(token)
        assert price != ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
def test_connect_rpc_with_hex_chainid(ethereum_inquirer: EthereumInquirer):
    """Test that connecting to an RPC that returns the chain id as an hex value
    instead of an integer works correctly
    """
    success, msg = ethereum_inquirer.attempt_connect(
        node=NodeName(
            name='reth',
            endpoint='https://eth.merkle.io',
            owned=True,
            blockchain=SupportedBlockchain.ETHEREUM,
        ),
    )
    assert success is True and msg == ''


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_fake_symbol_doesnt_query_cc(inquirer: 'Inquirer'):
    """Test that a token that has the symbol of another token (like USDC) doesn't trigger
    a price query"""
    inquirer.set_oracles_order(oracles=[CurrentPriceOracle.CRYPTOCOMPARE])
    token = EvmToken.initialize(
        address=string_to_evm_address('0x9fca10428566808CC9175412491dF4681cF39cE4'),
        chain_id=ChainID.GNOSIS,
        token_kind=EvmTokenKind.ERC20,
        name='Fake USDC',
        symbol='USDC',
        decimals=18,
    )
    assert inquirer.find_usd_price(token) == ZERO


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_recursion_in_inquirer(inquirer: Inquirer, globaldb: GlobalDBHandler):
    """Test that if a token has itself as underlying token we don't create an
    infinite recursion querying its price"""
    a_usdt = A_USDT.resolve_to_evm_token()
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO underlying_tokens_list(identifier, weight, parent_token_entry) '
            'VALUES(?, ?, ?)',
            (a_usdt.identifier, '1', a_usdt.identifier),
        )

    AssetResolver.clean_memory_cache(A_USDT.identifier)
    assert inquirer.find_usd_price(A_USDT) != ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_recursion_handling_in_inquirer(inquirer: Inquirer, globaldb: GlobalDBHandler):
    """This is a regression test that checks for the handling of the recursion error in the inquirer."""  # noqa: E501
    a_usdt = A_USDT.resolve_to_evm_token()
    with globaldb.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'INSERT INTO price_history(from_asset, to_asset, source_type, price, timestamp) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
            (a_usdt.identifier, A_BTC.identifier, 'E', '5', ts_now()),
        )
        write_cursor.execute(
            'INSERT INTO price_history(from_asset, to_asset, source_type, price, timestamp) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
            (A_BTC.identifier, a_usdt.identifier, 'E', '2', ts_now()),
        )

    price, oracle = inquirer.find_usd_price_and_oracle(A_USDT)
    assert oracle == CurrentPriceOracle.MANUALCURRENT
    assert price == Price(FVal('10.010'))


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_recursion_decorator(inquirer: Inquirer):
    """Test that the decorator handle_recursion_error works properly"""
    with patch('rotkehlchen.inquirer.Inquirer._find_usd_price', side_effect=RecursionError):
        assert inquirer.find_usd_price(A_USDT) == ZERO


@pytest.mark.freeze_time
@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_matic_pol_hardforked_price(inquirer: Inquirer, freezer):
    """Test that we return price of POL for MATIC after hardfork"""
    before_hardfork = Timestamp(POLYGON_POS_POL_HARDFORK - 1)
    after_hardfork = Timestamp(POLYGON_POS_POL_HARDFORK + 1)

    with patch(
        'rotkehlchen.externalapis.coingecko.Coingecko.query_current_price',
        wraps=inquirer._coingecko.query_current_price,
    ) as patched_gecko:
        freezer.move_to(datetime.datetime.fromtimestamp(before_hardfork, tz=datetime.UTC))
        inquirer.find_usd_price(A_POLYGON_POS_MATIC, ignore_cache=True)
        assert patched_gecko.call_args.kwargs['from_asset'] == A_POLYGON_POS_MATIC
        freezer.move_to(datetime.datetime.fromtimestamp(after_hardfork, tz=datetime.UTC))
        inquirer.find_usd_price(A_POLYGON_POS_MATIC, ignore_cache=True)
        assert patched_gecko.call_args.kwargs['from_asset'] == Asset('eip155:1/erc20:0x455e53CBB86018Ac2B8092FdCd39d8444aFFC3F6')  # POL token  # noqa: E501


@pytest.mark.vcr
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_vthor_price(inquirer_defi: 'Inquirer', database: 'DBHandler'):
    """Test that we can query price for vTHOR using the ratio that it maintains with THOR"""
    inquirer_defi._oracle_instances = [inquirer_defi._defillama]
    get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0xa5f2211B9b8170F694421f2046281775E8468044'),
        chain_id=ChainID.ETHEREUM,
        symbol='THOR',
        name='THORSwap Token',
        decimals=18,
    )
    get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x815C23eCA83261b6Ec689b60Cc4a58b54BC24D8D'),
        chain_id=ChainID.ETHEREUM,
        symbol='vTHOR',
        name='vTHOR',
        decimals=18,
    )

    price = inquirer_defi.find_usd_price(
        asset=Asset('eip155:1/erc20:0x815C23eCA83261b6Ec689b60Cc4a58b54BC24D8D'),
    )
    assert price.is_close(FVal(0.97656), max_diff=1e-5)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_morpho_vault_price(database: 'DBHandler', inquirer_defi: 'Inquirer') -> None:
    """Test that we get the correct price for Morpho vault tokens."""
    usual_boosted_usdc_vault = create_ethereum_morpho_vault_token(database=database)
    price = inquirer_defi.find_usd_price(asset=usual_boosted_usdc_vault)
    assert price.is_close(FVal(1.02611), max_diff=1e-5)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_balancer_pool_price(database: 'DBHandler', inquirer_defi: 'Inquirer') -> None:
    """Test that we get the correct price for Balancer pool tokens."""
    pufeth_wseth_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x63E0d47A6964aD1565345Da9bfA66659F4983F02'),
        chain_id=ChainID.ETHEREUM,
        token_kind=EvmTokenKind.ERC20,
        symbol='pufETH/wstETH',
        name='Balancer pufETH/wstETH',
        decimals=18,
        protocol=CPT_BALANCER_V2,
        underlying_tokens=[UnderlyingToken(
            address=string_to_evm_address('0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0'),
            token_kind=EvmTokenKind.ERC20,
            weight=FVal('0.5'),
        ), UnderlyingToken(
            address=string_to_evm_address('0xD9A442856C234a39a81a089C06451EBAa4306a72'),
            token_kind=EvmTokenKind.ERC20,
            weight=FVal('0.5'),
        )],
    )
    price = inquirer_defi.find_usd_price(asset=pufeth_wseth_token)
    assert price.is_close(FVal('3400.8425'), max_diff=1e-5)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_find_curve_lending_vault_price(
        inquirer_defi: 'Inquirer',
        ethereum_vault_token: 'EvmToken',
) -> None:
    """Test that we get the correct price for Curve lending vault tokens."""
    price = inquirer_defi.find_usd_price(asset=ethereum_vault_token)
    assert price.is_close(FVal(0.00102), max_diff=1e-5)


@pytest.mark.vcr
@pytest.mark.freeze_time('2024-10-21 18:00:00 GMT')
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_fiat_to_fiat(inquirer):
    """Test that fiat to fiat works for current prices and goes through the fiat oracle path"""
    inquirer.set_oracles_order([CurrentPriceOracle.COINGECKO, CurrentPriceOracle.DEFILLAMA])
    with patch.object(Inquirer, '_query_fiat_pair', wraps=Inquirer._query_fiat_pair) as _query_fiat_pair:  # noqa: E501
        price = inquirer.find_price(A_USD, A_EUR)
        assert price == FVal('0.924303')
        _query_fiat_pair.assert_called_once_with(
            base=A_USD.resolve_to_fiat_asset(),
            quote=A_EUR.resolve_to_fiat_asset(),
        )


@pytest.mark.vcr
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_price_of_assets_in_collection(inquirer):
    """
    Test that the inquirer can correctly find the USD price of the main asset and
    secondary assets in a collection.

    Checks that:
    - The price of the main asset (DAI) is close to the expected price of 1 USD.
    - The price of the secondary asset (xDAI) is the same as the main asset price.
    """
    dai_price = inquirer.find_usd_price(A_DAI)
    assert dai_price.is_close(ONE_PRICE, max_diff='0.01')

    xdai_price = inquirer.find_usd_price(A_XDAI)
    assert xdai_price == dai_price


@pytest.mark.vcr
def test_errors_web3_logs():
    """
    1rpc.io/gnosis has a limit of 1000 logs per query. This test
    ensure that the amount of queries made to the node is the minimum
    possible and that the limits are respected. Also tests that errors
    from `Web3Exception` are processed correctly in the logs logic.

    We had an issue where the error was not handled properly and block_range
    was getting reset after every successful query.
    """
    provider = HTTPProvider(
        endpoint_uri='https://1rpc.io/gnosis',
        request_kwargs={'timeout': 10},
    )
    web3 = Web3(provider=provider)
    address = '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'
    count = 0
    make_request = web3.HTTPProvider.make_request
    start_block, end_block = 50000, 60000

    def wrapper(*args, **kwargs):
        nonlocal count
        count += 1
        return make_request(*args, **kwargs)

    _, filter_args = construct_event_filter_params(
        event_abi=find_matching_event_abi(abi=ADDED_RECEIVER_ABI, event_name='AddedReceiver'),
        abi_codec=Web3().codec,
        contract_address=BLOCKREWARDS_ADDRESS,
        argument_filters={'receiver': address},
        from_block=start_block,
        to_block=end_block,
    )
    with patch.object(web3.HTTPProvider, 'make_request', new=wrapper):
        _query_web3_get_logs(
            web3=web3,
            filter_args=filter_args,
            from_block=start_block,
            to_block=end_block,
            contract_address=BLOCKREWARDS_ADDRESS,
            event_name='AddedReceiver',
            argument_filters={'receiver': address},
            initial_block_range=20000,
        )
        assert count == math.ceil((end_block - start_block) / 999) + 1  # + 1 is the failed request


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_bsq_price(inquirer: 'Inquirer') -> None:
    """Test that we can query bisq for market prices"""
    btc_price = Inquirer.find_usd_price(A_BTC)
    bsq_price = Inquirer.find_usd_price(A_BSQ.resolve_to_crypto_asset())
    assert bsq_price.is_close(btc_price * BTC_PER_BSQ)
