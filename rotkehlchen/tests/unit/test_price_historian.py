import logging
from contextlib import ExitStack
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken, UnderlyingToken
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_POL_HARDFORK
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BTC,
    A_CRV,
    A_ETH,
    A_ETH_MATIC,
    A_ETH_POL,
    A_LINK,
    A_POL,
    A_USD,
    A_WETH_ARB,
)
from rotkehlchen.constants.misc import NFT_DIRECTIVE, ONE, ZERO
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.birdeye import Birdeye
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.externalapis.moralis import Moralis
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import (
    HISTORICAL_PRICE_MISS_TTL_SECONDS,
    _prioritize_manual_balances_query,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import (
    DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER,
    HistoricalPrice,
    HistoricalPriceOracle,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE
from rotkehlchen.types import (
    ChainID,
    Price,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import timestamp_to_daystart_timestamp, ts_now

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import FiatAsset
    from rotkehlchen.globaldb.handler import GlobalDBHandler
    from rotkehlchen.inquirer import Inquirer


mocked_prices = {
    strethaddress_to_identifier('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'): {
        'USD': {
            1742814047: ONE,
            1742829743: ONE,
        },
    },
    strethaddress_to_identifier('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'): {
        'USD': {
            1742814047: FVal('2080'),
            1742829743: FVal('2085.21'),
        },
    },
}


@pytest.fixture(name='fake_price_historian')
def fixture_fake_price_historian(historical_price_oracles_order):
    # NB: custom fixture for quick unit testing. Do not export.
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    PriceHistorian._PriceHistorian__instance = None
    price_historian = PriceHistorian(
        data_directory=MagicMock(spec=Path),
        cryptocompare=MagicMock(spec=Cryptocompare),
        coingecko=MagicMock(spec=Coingecko),
        defillama=MagicMock(spec=Defillama),
        alchemy=MagicMock(spec=Alchemy),
        moralis=MagicMock(spec=Moralis),
        birdeye=MagicMock(spec=Birdeye),
        uniswapv2=MagicMock(spec=UniswapV2Oracle),
        uniswapv3=MagicMock(spec=UniswapV3Oracle),
    )
    price_historian.set_oracles_order(historical_price_oracles_order)
    return price_historian


def test_all_common_methods_implemented():
    """Test all historical price oracles implement the expected methods.
    """
    for oracle in DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER:
        if oracle == HistoricalPriceOracle.COINGECKO:
            instance = Coingecko
        elif oracle == HistoricalPriceOracle.CRYPTOCOMPARE:
            instance = Cryptocompare
        elif oracle == HistoricalPriceOracle.DEFILLAMA:
            instance = Defillama
        elif oracle == HistoricalPriceOracle.UNISWAPV2:
            instance = UniswapV2Oracle
        elif oracle == HistoricalPriceOracle.UNISWAPV3:
            instance = UniswapV3Oracle
        elif oracle == HistoricalPriceOracle.ALCHEMY:
            instance = Alchemy
        else:
            raise AssertionError(
                f'Unexpected historical price oracle: {oracle}. Update this test',
            )

        # Check 'can_query_history' method exists
        assert hasattr(instance, 'can_query_history')
        assert callable(instance.can_query_history)
        # Check 'query_historical_price' method exists
        assert hasattr(instance, 'query_historical_price')
        assert callable(instance.query_historical_price)


def test_set_oracles_custom_order(fake_price_historian):
    price_historian = fake_price_historian

    price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])

    assert price_historian._oracles == (HistoricalPriceOracle.COINGECKO,)
    assert price_historian._oracle_instances == [price_historian._coingecko]


def test_fiat_to_fiat(
        fake_price_historian: PriceHistorian,
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """Test the price is returned via exchangerates API when requesting the
    historical price from fiat to fiat.
    """
    price_historian = fake_price_historian
    call_count = 0
    expected_price = Price(FVal('1.25'))
    query_timestamp = Timestamp(1611595466)

    def mock_price_query(
            _cls,
            from_fiat_currency: FiatAsset,
            to_fiat_currency: FiatAsset,
            timestamp: Timestamp,
    ) -> Price | None:
        """
        Mock query for price checking that the assets are the expected and so is
        the timestamp queried.
        """
        nonlocal query_timestamp, expected_price, call_count
        call_count += 1
        assert from_fiat_currency == A_USD
        assert to_fiat_currency == A_GBP
        assert timestamp == query_timestamp
        return expected_price

    with patch('rotkehlchen.history.price.Inquirer.query_historical_fiat_exchange_rates', mock_price_query):  # noqa: E501
        price = price_historian.query_historical_price(
            from_asset=A_USD,
            to_asset=A_GBP,
            timestamp=query_timestamp,
        )

    assert price == expected_price
    assert call_count == 1


def test_token_to_fiat_all_can_query_history_no_price_found_exception(fake_price_historian):
    """Test NoPriceForGivenTimestamp is raised when all the oracles can't query
    the history.
    """
    price_historian = fake_price_historian

    for oracle_instance in price_historian._oracle_instances:
        oracle_instance.can_query_history.return_value = False

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1611595466),
        )
    for oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.can_query_history.call_count == 1
        assert oracle_instance.query_historical_price.call_count == 0


def test_token_to_fiat_no_price_found_exception(fake_price_historian):
    """Test NoPriceForGivenTimestamp is raised when the all the oracles fail
    requesting the historical price from token to fiat.
    """
    price_historian = fake_price_historian

    for oracle_instance in price_historian._oracle_instances:
        oracle_instance.query_historical_price.side_effect = NoPriceForGivenTimestamp(from_asset=A_BTC, to_asset=A_USD, time=1614556800)  # noqa: E501  # make sure they all fail

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1611595466),
        )
    for oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.query_historical_price.call_count == 1


def test_token_to_fiat_via_second_oracle(fake_price_historian):
    """Test price is returned via the second oracle when the first oracle fails
    requesting the historical price from token to fiat.
    """
    price_historian = fake_price_historian

    expected_price = Price(FVal('30000'))
    oracle_instances = price_historian._oracle_instances
    oracle_instances[0].query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')
    oracle_instances[1].query_historical_price.return_value = expected_price

    price = price_historian.query_historical_price(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=Timestamp(1611595466),
    )
    assert price == expected_price
    for oracle_instance in price_historian._oracle_instances[0:2]:
        assert oracle_instance.query_historical_price.call_count == 1


def _oracles_only_price_eth_in_usd(price_historian, eth_usd):
    """Make every oracle answer ETH in USD with `eth_usd` (a price, or an exception to raise)
    and find no price for anything else."""
    def query_historical_price(from_asset, to_asset, timestamp):
        if (from_asset, to_asset) != (A_ETH, A_USD):
            raise NoPriceForGivenTimestamp(
                from_asset=from_asset,
                to_asset=to_asset,
                time=timestamp,
            )
        if isinstance(eth_usd, Exception):
            raise eth_usd
        return eth_usd

    for oracle_instance in price_historian._oracle_instances:
        oracle_instance.query_historical_price.side_effect = query_historical_price


def test_fiat_to_crypto_inverts_crypto_to_fiat_price(fake_price_historian, inquirer):  # pylint: disable=unused-argument
    """Oracles price crypto in fiat but not fiat in crypto, so the price of USD in ETH
    is the inverse of the price of ETH in USD."""
    _oracles_only_price_eth_in_usd(fake_price_historian, Price(FVal('2000')))
    assert fake_price_historian.query_historical_price(
        from_asset=A_USD,
        to_asset=A_ETH,
        timestamp=Timestamp(1611595466),
    ) == Price(FVal('0.0005'))


def test_fiat_to_crypto_without_inverse_price_keeps_rate_limit(fake_price_historian, inquirer):  # pylint: disable=unused-argument
    """When the inverse price can't be found either, the missing price is raised and
    keeps the rate limit hit on the inverse query, so the user is asked to retry."""
    _oracles_only_price_eth_in_usd(fake_price_historian, RemoteError(
        'rate limited',
        cause=FailureCause.NETWORK,
        error_code=HTTPStatus.TOO_MANY_REQUESTS,
    ))
    with pytest.raises(NoPriceForGivenTimestamp) as error:
        fake_price_historian.query_historical_price(
            from_asset=A_USD,
            to_asset=A_ETH,
            timestamp=Timestamp(1611595466),
        )
    assert error.value.rate_limited is True


def test_cached_price_returns_without_oracle_calls(globaldb, fake_price_historian):
    price_historian = fake_price_historian
    globaldb.add_single_historical_price(  # store a manual price in the DB.
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=(expected_price := Price(FVal('30000'))),
            timestamp=Timestamp(1611595470),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    assert price_historian.query_historical_price(  # query price, should return the manual price
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=Timestamp(1611595466),
    ) == expected_price
    for oracle_instance in price_historian._oracle_instances:  # assert no oracles were queried.
        assert oracle_instance.query_historical_price.call_count == 0

    # simulate failure for all external oracles and assert no cached price is returned
    for oracle in price_historian._oracle_instances:
        oracle.query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1610595466),
        )


def test_disabled_historical_oracle_cache_is_ignored(
        globaldb,
        fake_price_historian,
        inquirer,  # pylint: disable=unused-argument
):
    """Cached values from disabled historical oracles should not be used."""
    price_historian = fake_price_historian
    query_timestamp = Timestamp(1611595466)
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=Price(FVal('30000')),
            timestamp=query_timestamp,
            source=HistoricalPriceOracle.ALCHEMY,
        ),
    )

    # In runtime the oracle order is synced from settings via set_oracles_order.
    # Simulate that by switching active historical oracles to COINGECKO only.
    price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])

    for oracle_instance in price_historian._oracle_instances:
        oracle_instance.can_query_history.return_value = False

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=query_timestamp,
        )


def test_daily_oracle_price_reused_for_whole_day(
        globaldb,
        fake_price_historian,
        inquirer,  # pylint: disable=unused-argument
):
    """Prices from daily-granularity oracles (coingecko) are cached at the UTC
    day-start timestamp and reused by any other query in the same UTC day,
    instead of re-querying the remote oracle for every distinct timestamp.
    """
    price_historian = fake_price_historian
    price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])
    coingecko = price_historian._oracle_instances[0]
    coingecko.can_query_history.return_value = True
    coingecko.query_historical_price.return_value = (expected_price := Price(FVal('2080')))

    morning_ts = Timestamp(1611567600)  # 25/01/2021 09:00 UTC
    assert price_historian.query_historical_price(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=morning_ts,
    ) == expected_price
    assert coingecko.query_historical_price.call_count == 1
    assert globaldb.get_historical_price(  # the price got stored at the day start
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=timestamp_to_daystart_timestamp(morning_ts),
        max_seconds_distance=0,
    ).price == expected_price

    # queries at other times of the same UTC day are served from the cache
    for hours_later in (4, 13):
        assert price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(morning_ts + hours_later * HOUR_IN_SECONDS),
        ) == expected_price
    assert coingecko.query_historical_price.call_count == 1

    # while a query on the next day hits the remote oracle again
    assert price_historian.query_historical_price(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=Timestamp(morning_ts + DAY_IN_SECONDS),
    ) == expected_price
    assert coingecko.query_historical_price.call_count == 2


def test_get_historical_prices(globaldb: GlobalDBHandler) -> None:
    ts1 = Timestamp(1611595470)
    price1, price2, price3, price4 = Price(FVal(30000)), Price(FVal(35000)), Price(FVal(45000)), Price(FVal(77000))  # noqa: E501
    # Add price at timestamp
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price1,
            timestamp=Timestamp(ts1),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price2,
            timestamp=Timestamp(ts1 + 3600 * 4),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price3,
            timestamp=Timestamp(ts1 + DAY_IN_SECONDS + 3600),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price4,
            timestamp=Timestamp(ts1 + 4 * DAY_IN_SECONDS + 3600),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )

    result = globaldb.get_historical_prices(
        query_data=[
            (A_BTC, A_USD, Timestamp(ts1 - 3600)),
            (A_BTC, A_USD, Timestamp(ts1 + 3600 * 6)),
            (A_BTC, A_USD, Timestamp(ts1 + DAY_IN_SECONDS - 3600 * 2)),
            (A_BTC, A_USD, Timestamp(ts1 + 2 * DAY_IN_SECONDS + 3600 * 4)),
            (A_BTC, A_USD, Timestamp(ts1 + 4 * DAY_IN_SECONDS - 3600)),
        ],
        max_seconds_distance=DAY_IN_SECONDS,
    )
    assert [price1, price2, price3, None, price4] == [x.price if x is not None else None for x in result]  # noqa: E501

    # check that we prioritize the manual price
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_AAVE,
            to_asset=A_USD,
            price=Price(ONE),
            timestamp=Timestamp(ts1),
            source=HistoricalPriceOracle.COINGECKO,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_AAVE,
            to_asset=A_USD,
            price=Price(FVal(3)),
            timestamp=Timestamp(ts1),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    single_price = globaldb.get_historical_price(
        from_asset=A_AAVE,
        to_asset=A_USD,
        timestamp=Timestamp(ts1),
        max_seconds_distance=DAY_IN_SECONDS,
    )
    batch_result = globaldb.get_historical_prices(
        query_data=[(A_AAVE, A_USD, Timestamp(ts1))],
        max_seconds_distance=DAY_IN_SECONDS,
    )
    assert single_price is not None
    assert batch_result[0] is not None
    assert single_price.price == batch_result[0].price == FVal(3)
    assert batch_result[0].source == HistoricalPriceOracle.MANUAL

    # check that source filtering in batch lookup returns only the requested source
    source_filtered_result = globaldb.get_historical_prices(
        query_data=[(A_AAVE, A_USD, Timestamp(ts1))],
        max_seconds_distance=DAY_IN_SECONDS,
        source=HistoricalPriceOracle.COINGECKO,
    )
    assert source_filtered_result[0] is not None
    assert source_filtered_result[0].price == ONE
    assert source_filtered_result[0].source == HistoricalPriceOracle.COINGECKO

    missing_source_result = globaldb.get_historical_prices(
        query_data=[(A_AAVE, A_USD, Timestamp(ts1))],
        max_seconds_distance=DAY_IN_SECONDS,
        source=HistoricalPriceOracle.CRYPTOCOMPARE,
    )
    assert missing_source_result == [None]


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_oracle_instance_caches_price(price_historian):
    """Test that an oracle saves the historical price after a successful price query"""
    expected_price, expected_timestamp = Price(FVal('100')), Timestamp(1611595466)
    for oracle_instance in price_historian._oracle_instances:
        oracle_instance.query_historical_price = MagicMock(return_value=expected_price)

    with (
        patch('rotkehlchen.history.price.GlobalDBHandler.get_historical_price', return_value=None),
        patch('rotkehlchen.history.price.GlobalDBHandler.add_historical_prices') as mock_add,
    ):
        result = price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=expected_timestamp,
        )
        assert result == expected_price
        mock_add.assert_called_with([HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            source=HistoricalPriceOracle.DEFILLAMA,
            timestamp=expected_timestamp,
            price=expected_price,
        )])


def test_price_priority_order():
    """Test to ensure that we detect changes on the constant value returned"""
    order_clause, order_bindings = _prioritize_manual_balances_query()
    assert order_clause.startswith(' ORDER BY ABS(timestamp - ?),')
    assert order_bindings == [HistoricalPriceOracle.MANUAL.serialize_for_db()]

    # With explicit sources, closeness is still first and source order is tie-breaker
    sources = (
        HistoricalPriceOracle.CRYPTOCOMPARE,
        HistoricalPriceOracle.COINGECKO,
        HistoricalPriceOracle.DEFILLAMA,
    )
    order_clause, order_bindings = _prioritize_manual_balances_query(sources=sources)
    assert order_clause.startswith(' ORDER BY ABS(timestamp - ?),')
    assert order_bindings[0] == HistoricalPriceOracle.MANUAL.serialize_for_db()
    assert HistoricalPriceOracle.CRYPTOCOMPARE.serialize_for_db() in order_bindings
    assert HistoricalPriceOracle.COINGECKO.serialize_for_db() in order_bindings
    assert HistoricalPriceOracle.DEFILLAMA.serialize_for_db() in order_bindings


def test_price_priority_distance_then_source(globaldb: GlobalDBHandler) -> None:
    """Prefer closest timestamp across oracles (cryptocompare over manual/defillama),
    then use source priority as tie-breaker (manual over cryptocompare)."""
    query_timestamp = Timestamp(100)
    max_seconds_distance = 20
    sources = (
        HistoricalPriceOracle.MANUAL,
        HistoricalPriceOracle.CRYPTOCOMPARE,
        HistoricalPriceOracle.DEFILLAMA,
    )

    # Closest timestamp wins even if another source has higher source priority.
    # Here cryptocompare is preferred over manual and defillama because it is closer.
    globaldb.add_historical_prices([
        HistoricalPrice(
            from_asset=A_LINK,
            to_asset=A_GBP,
            source=HistoricalPriceOracle.MANUAL,
            timestamp=Timestamp(90),
            price=Price(ONE),
        ),
        HistoricalPrice(
            from_asset=A_LINK,
            to_asset=A_GBP,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
            timestamp=Timestamp(99),
            price=Price(FVal('2')),
        ),
        HistoricalPrice(
            from_asset=A_LINK,
            to_asset=A_GBP,
            source=HistoricalPriceOracle.DEFILLAMA,
            timestamp=Timestamp(110),
            price=Price(FVal('5')),
        ),
    ])
    result = globaldb.get_historical_price(
        from_asset=A_LINK,
        to_asset=A_GBP,
        timestamp=query_timestamp,
        max_seconds_distance=max_seconds_distance,
        sources=sources,
    )
    assert result is not None
    assert result.source == HistoricalPriceOracle.CRYPTOCOMPARE
    assert result.timestamp == Timestamp(99)

    # If distance is tied, source priority picks manual first.
    globaldb.add_historical_prices([
        HistoricalPrice(
            from_asset=A_AAVE,
            to_asset=A_GBP,
            source=HistoricalPriceOracle.MANUAL,
            timestamp=Timestamp(101),
            price=Price(FVal('3')),
        ),
        HistoricalPrice(
            from_asset=A_AAVE,
            to_asset=A_GBP,
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
            timestamp=Timestamp(99),
            price=Price(FVal('4')),
        ),
    ])
    result = globaldb.get_historical_price(
        from_asset=A_AAVE,
        to_asset=A_GBP,
        timestamp=query_timestamp,
        max_seconds_distance=max_seconds_distance,
        sources=sources,
    )
    assert result is not None
    assert result.source == HistoricalPriceOracle.MANUAL
    assert result.timestamp == Timestamp(101)


@pytest.mark.vcr(filter_query_parameters=['apikey', 'api_key'])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_uniswap_v2_position_price_query(price_historian: PriceHistorian):
    price = price_historian.query_uniswap_position_price(
        pool_token=EvmToken.initialize(
            address=string_to_evm_address('0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc'),
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            protocol=CPT_UNISWAP_V2,
            decimals=18,
        ),
        pool_token_amount=FVal('0.015374510179577256'),
        to_asset=A_USD,
        timestamp=Timestamp(1742814047),
    )

    assert price.is_close('3606838.214124')


@pytest.mark.vcr(filter_query_parameters=['apikey', 'api_key'])
@pytest.mark.parametrize('mocked_price_queries', [mocked_prices])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_uniswap_v3_position_price_query(price_historian: PriceHistorian):
    price = price_historian.query_uniswap_position_price(
        pool_token=EvmToken.initialize(
            address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC721,
            protocol=CPT_UNISWAP_V3,
            collectible_id='953465',
        ),
        pool_token_amount=ZERO,
        to_asset=A_USD,
        timestamp=Timestamp(1742829743),
    )

    assert price.is_close('91.901195')


@pytest.mark.vcr(filter_query_parameters=['api_key'])
@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_matic_pol_hardforked_price(price_historian: PriceHistorian) -> None:
    """Test that pol/matic tokens all get proper prices before/after the hardfork."""
    for timestamp, expected_price in (
            (Timestamp(POLYGON_POS_POL_HARDFORK - 1000000), '0.543'),
            (Timestamp(POLYGON_POS_POL_HARDFORK + 1000000), '0.381'),
    ):
        for asset in (A_POL, A_ETH_POL, A_ETH_MATIC):
            assert price_historian.query_historical_price(
                from_asset=asset,
                to_asset=A_USD,
                timestamp=timestamp,
            ).is_close(expected_price, max_diff='0.003')


def test_historical_price_underlying_tokens(globaldb: GlobalDBHandler) -> None:
    """Test that querying a historical price for a token with underlying tokens
    resolves the price from the underlying tokens weighted by their proportions."""
    aave_weight, link_weight, crv_weight = FVal('0.6'), FVal('0.2'), FVal('0.2')
    address = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
    token = EvmToken.initialize(
        address=address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='Test',
        symbol='YAB',
        underlying_tokens=[
            UnderlyingToken(address=A_AAVE.resolve_to_evm_token().evm_address, token_kind=TokenKind.ERC20, weight=aave_weight),  # noqa: E501
            UnderlyingToken(address=A_LINK.resolve_to_evm_token().evm_address, token_kind=TokenKind.ERC20, weight=link_weight),  # noqa: E501
            UnderlyingToken(address=A_CRV.resolve_to_evm_token().evm_address, token_kind=TokenKind.ERC20, weight=crv_weight),  # noqa: E501
        ],
    )
    globaldb.add_asset(token)

    query_timestamp = Timestamp(1710719119)
    # Add manual historical prices for each underlying token
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_AAVE, to_asset=A_USD, price=Price(FVal('100')),
        timestamp=query_timestamp, source=HistoricalPriceOracle.MANUAL,
    ))
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_LINK, to_asset=A_USD, price=Price(FVal('25')),
        timestamp=query_timestamp, source=HistoricalPriceOracle.MANUAL,
    ))
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_CRV, to_asset=A_USD, price=Price(FVal('10')),
        timestamp=query_timestamp, source=HistoricalPriceOracle.MANUAL,
    ))

    # expected = 100*0.6 + 25*0.2 + 10*0.2 = 60 + 5 + 2 = 67
    price = PriceHistorian.get_price_for_special_asset(
        from_asset=token,
        to_asset=A_USD,
        timestamp=query_timestamp,
        max_seconds_distance=3600,
    )
    assert price == Price(FVal('67'))


def test_historical_price_underlying_tokens_unpriced_when_a_leg_is_missing(
        globaldb: GlobalDBHandler,
) -> None:
    """Regression test: a token valued from its underlying tokens must be reported as
    unpriced when any underlying leg has no historical price, instead of returning a
    too-low partial sum that the user would mistake for the real value."""
    aave_weight, link_weight, crv_weight = FVal('0.6'), FVal('0.2'), FVal('0.2')
    address = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
    token = EvmToken.initialize(
        address=address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='Test',
        symbol='YAB',
        underlying_tokens=[
            UnderlyingToken(address=A_AAVE.resolve_to_evm_token().evm_address, token_kind=TokenKind.ERC20, weight=aave_weight),  # noqa: E501
            UnderlyingToken(address=A_LINK.resolve_to_evm_token().evm_address, token_kind=TokenKind.ERC20, weight=link_weight),  # noqa: E501
            UnderlyingToken(address=A_CRV.resolve_to_evm_token().evm_address, token_kind=TokenKind.ERC20, weight=crv_weight),  # noqa: E501
        ],
    )
    globaldb.add_asset(token)

    # add historical prices for every underlying token except A_LINK, which stays unpriced
    query_timestamp = Timestamp(1710719119)
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_AAVE, to_asset=A_USD, price=Price(FVal('100')),
        timestamp=query_timestamp, source=HistoricalPriceOracle.MANUAL,
    ))
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_CRV, to_asset=A_USD, price=Price(FVal('10')),
        timestamp=query_timestamp, source=HistoricalPriceOracle.MANUAL,
    ))

    # before the fix this returned the partial sum 100*0.6 + 10*0.2 = 62
    price = PriceHistorian.get_price_for_special_asset(
        from_asset=token,
        to_asset=A_USD,
        timestamp=query_timestamp,
        max_seconds_distance=3600,
    )
    assert price is None


def test_historical_price_collection_member_uses_main_asset(
        globaldb: GlobalDBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """Test that a non-main collection member is priced as the collection's main asset.

    WETH on arbitrum is in the same collection as ETH, but its own cryptocompare mapping
    points at the thin WETH ticker instead of ETH, so prices cached against the token
    itself can be wildly off. Regression test: the main asset's price must win.
    """
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_ETH, to_asset=A_USD, price=Price(FVal('2561.88')),
        timestamp=(query_timestamp := Timestamp(1726869600)),
        source=HistoricalPriceOracle.MANUAL,
    ))
    globaldb.add_single_historical_price(HistoricalPrice(  # the bad price seen in the wild
        from_asset=A_WETH_ARB, to_asset=A_USD, price=Price(FVal('1013.49')),
        timestamp=query_timestamp, source=HistoricalPriceOracle.CRYPTOCOMPARE,
    ))

    assert PriceHistorian.get_price_for_special_asset(
        from_asset=A_WETH_ARB,
        to_asset=A_USD,
        timestamp=query_timestamp,
        max_seconds_distance=HOUR_IN_SECONDS,
    ) == Price(FVal('2561.88'))


def test_historical_price_collection_main_asset_is_not_redirected_to_itself(
        globaldb: GlobalDBHandler,
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """Test that the main asset of a collection is not redirected to itself.

    get_collection_main_asset returns the main asset for every member, the main asset
    included, so an unguarded redirect would make ETH query its own price through here
    and recurse endlessly once a cache miss escalates to a remote query.
    """
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=A_ETH, to_asset=A_USD, price=Price(FVal('2561.88')),
        timestamp=(query_timestamp := Timestamp(1726869600)),
        source=HistoricalPriceOracle.MANUAL,
    ))
    assert PriceHistorian.get_price_for_special_asset(  # ETH needs no special handling,
        from_asset=A_ETH,  # so this must decline instead of resolving its own price
        to_asset=A_USD,
        timestamp=query_timestamp,
        max_seconds_distance=HOUR_IN_SECONDS,
    ) is None


def _make_miss(
        from_asset: Asset,
        timestamp: Timestamp,
        to_asset: Asset = A_USD,
        *,
        cacheable_miss: bool = True,
        rate_limited: bool = False,
) -> NoPriceForGivenTimestamp:
    return NoPriceForGivenTimestamp(
        from_asset=from_asset,
        to_asset=to_asset,
        time=timestamp,
        rate_limited=rate_limited,
        cacheable_miss=cacheable_miss,
    )


def test_historical_price_misses_caching_granularity_and_flushing(
        globaldb: GlobalDBHandler,
        fake_price_historian,
        inquirer: Inquirer,  # pylint: disable=unused-argument
):
    """Confirmed misses are cached at the exact timestamp (point-in-time) and UTC-day (daily)
    granularity, so a later timestamp within the same hour retries point-in-time oracles, and
    flushed selectively when a later oracle succeeds (point-in-time misses skipped; daily
    misses persisted).
    """
    fake_price_historian.set_oracles_order([
        HistoricalPriceOracle.DEFILLAMA,
        HistoricalPriceOracle.COINGECKO,
    ])
    defillama, coingecko = fake_price_historian._oracle_instances
    defillama.can_query_history.return_value = True
    coingecko.can_query_history.return_value = True

    morning_ts = Timestamp(1611565242)  # 25/01/2021 09:00:42 UTC
    daystart_ts = timestamp_to_daystart_timestamp(morning_ts)
    defillama.query_historical_price.side_effect = _make_miss(A_BTC, morning_ts)
    coingecko.query_historical_price.side_effect = _make_miss(A_BTC, morning_ts)

    with pytest.raises(NoPriceForGivenTimestamp) as exc_info:
        fake_price_historian.query_historical_price(A_BTC, A_USD, morning_ts)
    assert exc_info.value.rate_limited is False
    assert defillama.query_historical_price.call_count == 1
    assert coingecko.query_historical_price.call_count == 1
    assert globaldb.get_historical_price_misses(A_BTC, (morning_ts, daystart_ts)) == {
        (HistoricalPriceOracle.DEFILLAMA, morning_ts),
        (HistoricalPriceOracle.COINGECKO, daystart_ts),
    }

    # The exact same timestamp reuses both misses
    with pytest.raises(NoPriceForGivenTimestamp):
        fake_price_historian.query_historical_price(A_BTC, A_USD, morning_ts)
    assert defillama.query_historical_price.call_count == 1
    assert coingecko.query_historical_price.call_count == 1

    # A later timestamp in the same UTC hour retries DefiLlama (the token may have started
    # trading since) while still skipping the daily CoinGecko miss
    defillama.query_historical_price.side_effect = None
    defillama.query_historical_price.return_value = (btc_price := Price(FVal('32000')))
    assert fake_price_historian.query_historical_price(
        A_BTC, A_USD, Timestamp(morning_ts + 600),
    ) == btc_price
    assert defillama.query_historical_price.call_count == 2
    assert coingecko.query_historical_price.call_count == 1

    # Point-in-time miss is NOT flushed when a later oracle succeeds
    defillama.query_historical_price.side_effect = _make_miss(A_LINK, morning_ts)
    coingecko.query_historical_price.side_effect = None
    coingecko.query_historical_price.return_value = (link_price := Price(FVal('25')))
    assert fake_price_historian.query_historical_price(A_LINK, A_USD, morning_ts) == link_price
    assert globaldb.get_historical_price_misses(A_LINK, (morning_ts, daystart_ts)) == set()

    # Daily-granularity miss IS flushed when a later point-in-time oracle succeeds, so a
    # later query on the same UTC day skips the daily oracle
    fake_price_historian.set_oracles_order([
        HistoricalPriceOracle.COINGECKO,
        HistoricalPriceOracle.DEFILLAMA,
    ])
    coingecko, defillama = fake_price_historian._oracle_instances
    coingecko.query_historical_price.reset_mock()
    defillama.query_historical_price.reset_mock()
    coingecko.query_historical_price.side_effect = _make_miss(A_ETH, morning_ts)
    defillama.query_historical_price.side_effect = None
    defillama.query_historical_price.return_value = (eth_price := Price(FVal('1400')))

    assert fake_price_historian.query_historical_price(A_ETH, A_USD, morning_ts) == eth_price
    assert globaldb.get_historical_price_misses(A_ETH, (morning_ts, daystart_ts)) == {
        (HistoricalPriceOracle.COINGECKO, daystart_ts),
    }
    later_ts = Timestamp(morning_ts + 3 * HOUR_IN_SECONDS)
    assert fake_price_historian.query_historical_price(A_ETH, A_USD, later_ts) == eth_price
    assert coingecko.query_historical_price.call_count == 1
    assert defillama.query_historical_price.call_count == 2


def test_historical_price_misses_selective_recording_recency_and_ttl(
        globaldb: GlobalDBHandler,
        fake_price_historian,
        inquirer: Inquirer,  # pylint: disable=unused-argument
):
    """Only definitive remote misses for old-enough timestamps are recorded; rate limits,
    can_query_history skips, local unsupported-asset errors, intermediate conversion misses,
    and recent/current-day timestamps are not cached, and expired misses are retried/refreshed.
    """
    fake_price_historian.set_oracles_order([
        HistoricalPriceOracle.DEFILLAMA,
        HistoricalPriceOracle.COINGECKO,
        HistoricalPriceOracle.UNISWAPV3,
        HistoricalPriceOracle.UNISWAPV2,
        HistoricalPriceOracle.ALCHEMY,
        HistoricalPriceOracle.MORALIS,
    ])
    defillama, coingecko, uniswapv3, uniswapv2, alchemy, moralis = (
        fake_price_historian._oracle_instances
    )
    ts = Timestamp(1611595466)
    daystart_ts = timestamp_to_daystart_timestamp(ts)

    for oracle in (defillama, uniswapv3, uniswapv2, alchemy, moralis):
        oracle.can_query_history.return_value = True
    coingecko.can_query_history.return_value = False

    defillama.query_historical_price.side_effect = _make_miss(A_BTC, ts, A_GBP)
    uniswapv3.query_historical_price.side_effect = RemoteError(
        'rate limited',
        cause=FailureCause.RATE_LIMITED,
        error_code=HTTPStatus.TOO_MANY_REQUESTS,
    )
    uniswapv2.query_historical_price.side_effect = _make_miss(A_USD, ts, A_GBP)
    alchemy.query_historical_price.side_effect = _make_miss(A_BTC, ts, A_GBP, rate_limited=True)
    moralis.query_historical_price.side_effect = PriceQueryUnsupportedAsset(A_BTC.identifier)

    with pytest.raises(NoPriceForGivenTimestamp) as exc_info:
        fake_price_historian.query_historical_price(A_BTC, A_GBP, ts)
    assert exc_info.value.rate_limited is True
    assert globaldb.get_historical_price_misses(A_BTC, (ts, daystart_ts)) == {
        (HistoricalPriceOracle.DEFILLAMA, ts),
    }

    # On retry, DefiLlama is skipped while previously uncached oracles are tried
    coingecko.can_query_history.return_value = True
    coingecko.query_historical_price.return_value = (gbp_price := Price(FVal('22000')))
    assert fake_price_historian.query_historical_price(A_BTC, A_GBP, ts) == gbp_price
    assert defillama.query_historical_price.call_count == 1
    assert coingecko.query_historical_price.call_count == 1

    # Recent / today's UTC day misses are never cached
    fake_price_historian.set_oracles_order([
        HistoricalPriceOracle.DEFILLAMA,
        HistoricalPriceOracle.COINGECKO,
    ])
    defillama, coingecko = fake_price_historian._oracle_instances
    now = ts_now()
    recent_ts = Timestamp(now - 600)
    recent_day = timestamp_to_daystart_timestamp(recent_ts)
    defillama.query_historical_price.side_effect = _make_miss(A_BTC, recent_ts)
    coingecko.query_historical_price.side_effect = _make_miss(A_BTC, recent_ts)
    with pytest.raises(NoPriceForGivenTimestamp):
        fake_price_historian.query_historical_price(A_BTC, A_USD, recent_ts)
    assert globaldb.get_historical_price_misses(A_BTC, (recent_ts, recent_day)) == set()

    # Expired misses (checked_at older than TTL) are ignored on read and refreshed on re-miss
    old_ts = Timestamp(1611565200)
    old_day = timestamp_to_daystart_timestamp(old_ts)
    globaldb.add_historical_price_misses(
        from_asset=A_BTC,
        misses=[(HistoricalPriceOracle.DEFILLAMA, old_ts)],
        checked_at=Timestamp(now - HISTORICAL_PRICE_MISS_TTL_SECONDS - 60),
    )
    assert globaldb.get_historical_price_misses(A_BTC, (old_ts,)) == set()

    defillama.query_historical_price.reset_mock()
    coingecko.query_historical_price.reset_mock()
    defillama.query_historical_price.side_effect = _make_miss(A_BTC, old_ts)
    coingecko.query_historical_price.side_effect = _make_miss(A_BTC, old_ts)
    with pytest.raises(NoPriceForGivenTimestamp):
        fake_price_historian.query_historical_price(A_BTC, A_USD, old_ts)
    assert defillama.query_historical_price.call_count == 1
    assert coingecko.query_historical_price.call_count == 1
    assert globaldb.get_historical_price_misses(A_BTC, (old_ts, old_day)) == {
        (HistoricalPriceOracle.DEFILLAMA, old_ts),
        (HistoricalPriceOracle.COINGECKO, old_day),
    }


def test_historical_price_misses_invalidation_and_fk_safety(
        globaldb: GlobalDBHandler,
        caplog: pytest.LogCaptureFixture,
) -> None:
    """Cached misses are cleared on asset/protocol/price edits and deletions (scoped for
    price deletions), cascade on asset deletion, and ignore non-existent assets without FK errors.
    """
    ts = Timestamp(1611595200)
    other_ts = Timestamp(ts + 2 * DAY_IN_SECONDS)
    token = EvmToken.initialize(
        address=string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='Test Token',
        symbol='TST',
        coingecko='test-token',
    )
    globaldb.add_asset(token)

    def assert_clears_miss(asset: Asset, action) -> None:
        globaldb.add_historical_price_misses(asset, [(HistoricalPriceOracle.DEFILLAMA, ts)])
        assert globaldb.get_historical_price_misses(asset, (ts,)) == {
            (HistoricalPriceOracle.DEFILLAMA, ts),
        }
        action()
        assert globaldb.get_historical_price_misses(asset, (ts,)) == set()

    assert_clears_miss(A_BTC, lambda: globaldb.edit_user_asset(A_BTC.resolve_to_crypto_asset()))
    assert_clears_miss(token, lambda: globaldb.edit_evm_token(token))
    assert_clears_miss(token, lambda: globaldb.edit_token_fields(token, {'coingecko'}))
    assert_clears_miss(token, lambda: globaldb.set_tokens_protocol_if_missing([token], CPT_UNISWAP_V2))  # noqa: E501

    # delete_historical_price clears only the affected timestamp/day misses
    globaldb.add_historical_price_misses(
        token,
        [(HistoricalPriceOracle.DEFILLAMA, ts), (HistoricalPriceOracle.DEFILLAMA, other_ts)],
    )
    globaldb.add_single_historical_price(HistoricalPrice(
        from_asset=token,
        to_asset=A_USD,
        source=HistoricalPriceOracle.MANUAL,
        timestamp=ts,
        price=Price(ONE),
    ))
    assert globaldb.delete_historical_price(token, A_USD, ts, HistoricalPriceOracle.MANUAL) is True
    assert globaldb.get_historical_price_misses(token, (ts, other_ts)) == {
        (HistoricalPriceOracle.DEFILLAMA, other_ts),
    }

    # delete_historical_prices scoped by source only clears that source; source=None clears all
    globaldb.add_historical_price_misses(
        token,
        [(HistoricalPriceOracle.DEFILLAMA, ts), (HistoricalPriceOracle.COINGECKO, ts)],
    )
    globaldb.delete_historical_prices(token, A_USD, source=HistoricalPriceOracle.DEFILLAMA)
    assert globaldb.get_historical_price_misses(token, (ts,)) == {
        (HistoricalPriceOracle.COINGECKO, ts),
    }
    globaldb.delete_historical_prices(token, A_USD)
    assert globaldb.get_historical_price_misses(token, (ts, other_ts)) == set()

    # Deleting the asset cascades to historical_price_misses
    assert_clears_miss(token, lambda: globaldb.delete_asset_by_identifier(token.identifier))

    # Assets absent from globaldb.assets (e.g. NFTs) must not log FK IntegrityError
    nft_asset = Asset(f'{NFT_DIRECTIVE}0x0000000000000000000000000000000000000001_1')
    with caplog.at_level(logging.ERROR):
        globaldb.add_historical_price_misses(nft_asset, [(HistoricalPriceOracle.DEFILLAMA, ts)])
    assert not any(
        'Failed to add historical price misses' in rec.message for rec in caplog.records
    )


def test_in_flight_miss_not_written_after_concurrent_invalidation(
        globaldb: GlobalDBHandler,
        fake_price_historian,
        inquirer: Inquirer,  # pylint: disable=unused-argument
):
    """When an asset edit or case-insensitive miss invalidation commits while an oracle query
    is in flight, the stale in-flight response must not write a new miss.
    """
    ts = Timestamp(1611565200)
    daystart_ts = timestamp_to_daystart_timestamp(ts)
    address = string_to_evm_address('0xc37b40ABdB939635068d3c5f13E7faF686F03B65')
    token = EvmToken.initialize(
        address=address,
        chain_id=ChainID.ETHEREUM,
        token_kind=TokenKind.ERC20,
        decimals=18,
        name='Test Token',
        symbol='TST',
        coingecko='wrong-coingecko-id',
    )
    globaldb.add_asset(token)
    globaldb.add_historical_price_misses(token, [(HistoricalPriceOracle.DEFILLAMA, ts)])

    fake_price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])
    coingecko = fake_price_historian._oracle_instances[0]
    coingecko.can_query_history.return_value = True

    def edit_during_query(from_asset, to_asset, timestamp):
        globaldb.edit_evm_token(EvmToken.initialize(
            address=address,
            chain_id=ChainID.ETHEREUM,
            token_kind=TokenKind.ERC20,
            decimals=18,
            name='Test Token',
            symbol='TST',
            coingecko='corrected-coingecko-id',
        ))
        raise _make_miss(from_asset, timestamp, to_asset)

    coingecko.query_historical_price.side_effect = edit_during_query
    with pytest.raises(NoPriceForGivenTimestamp):
        fake_price_historian.query_historical_price(token, A_USD, ts)
    assert globaldb.get_historical_price_misses(token, (ts, daystart_ts)) == set()

    coingecko.query_historical_price.side_effect = None
    coingecko.query_historical_price.return_value = (expected_price := Price(FVal('42')))
    assert fake_price_historian.query_historical_price(
        Asset(token.identifier),
        A_USD,
        ts,
    ) == expected_price
    assert coingecko.query_historical_price.call_count == 2

    # Case-insensitive invalidation (Asset('eth') query vs A_ETH delete) also drops stale miss
    def invalidate_uppercase_eth(from_asset, to_asset, timestamp):
        globaldb.delete_historical_price_misses(A_ETH)
        raise _make_miss(from_asset, timestamp, to_asset)

    coingecko.query_historical_price.side_effect = invalidate_uppercase_eth
    with pytest.raises(NoPriceForGivenTimestamp):
        fake_price_historian.query_historical_price(Asset('eth'), A_USD, ts)
    assert globaldb.get_historical_price_misses(A_ETH, (ts, daystart_ts)) == set()


@pytest.mark.parametrize('should_mock_price_queries', [False])
def test_unsupported_quote_and_pair_specific_misses_do_not_poison_base_asset_cache(
        globaldb: GlobalDBHandler,
        price_historian: PriceHistorian,
        inquirer: Inquirer,  # pylint: disable=unused-argument
) -> None:
    """Unsupported quote currencies (BTC/AAVE) and quote-specific misses (BTC/GBP when USD is
    present) must not record a base-asset miss for BTC that would suppress BTC/USD on the same day.
    """
    price_historian.set_oracles_order([HistoricalPriceOracle.COINGECKO])
    coingecko = price_historian._coingecko
    ts = Timestamp(1611565200)
    daystart_ts = timestamp_to_daystart_timestamp(ts)

    with (
        patch.object(coingecko, 'can_query_history', return_value=True),
        patch.object(
            coingecko,
            '_query',
            return_value={'id': 'bitcoin', 'market_data': {'current_price': {'usd': 32500.0}}},
        ) as mock_cg_query,
    ):
        with pytest.raises(NoPriceForGivenTimestamp) as exc_info:
            price_historian.query_historical_price(A_BTC, A_AAVE, ts)
        assert exc_info.value.cacheable_miss is False
        assert mock_cg_query.call_count == 0
        assert globaldb.get_historical_price_misses(A_BTC, (ts, daystart_ts)) == set()

        with pytest.raises(NoPriceForGivenTimestamp):
            price_historian.query_historical_price(A_BTC, A_GBP, ts)
        assert mock_cg_query.call_count == 1
        assert globaldb.get_historical_price_misses(A_BTC, (ts, daystart_ts)) == set()

        assert price_historian.query_historical_price(A_BTC, A_USD, ts) == Price(FVal('32500.0'))
        assert mock_cg_query.call_count == 2


@pytest.mark.parametrize('should_mock_price_queries', [False])
@pytest.mark.parametrize(
    ('oracle', 'from_asset', 'payload', 'expect_cached'),
    [
        # DefiLlama
        pytest.param(HistoricalPriceOracle.DEFILLAMA, A_BTC, {}, False, id='defillama-no-coins'),
        pytest.param(HistoricalPriceOracle.DEFILLAMA, A_BTC, {'coins': {'coingecko:bitcoin': {}}}, False, id='defillama-no-price'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.DEFILLAMA, A_BTC, {'coins': {'coingecko:bitcoin': {'price': 'bad'}}}, False, id='defillama-bad-price'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.DEFILLAMA, A_BTC, {'coins': {}}, True, id='defillama-empty'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.DEFILLAMA, A_BTC, {'coins': {'coingecko:bitcoin': {'price': 1.5, 'confidence': 0.1}}}, True, id='defillama-low-confidence'),  # noqa: E501
        # CoinGecko
        pytest.param(HistoricalPriceOracle.COINGECKO, A_BTC, {}, False, id='coingecko-no-id'),
        pytest.param(HistoricalPriceOracle.COINGECKO, A_BTC, {'id': 'other-coin'}, False, id='coingecko-wrong-id'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.COINGECKO, A_BTC, {'id': 'bitcoin', 'market_data': {}}, False, id='coingecko-missing-current-price'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.COINGECKO, A_BTC, {'id': 'bitcoin', 'market_data': {'current_price': {'usd': 'bad'}}}, False, id='coingecko-bad-price'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.COINGECKO, A_BTC, {'id': 'bitcoin', 'symbol': 'btc'}, True, id='coingecko-no-market-data'),  # noqa: E501
        # Alchemy
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'symbol': 'WRONG', 'currency': 'usd', 'data': []}, False, id='alchemy-wrong-symbol'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'symbol': 'BTC', 'currency': 'eur', 'data': []}, False, id='alchemy-non-usd'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'symbol': 'BTC', 'currency': 'usd'}, False, id='alchemy-no-data-key'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'symbol': 'BTC', 'currency': 'usd', 'data': [{'timestamp': 'bad', 'value': '1'}]}, False, id='alchemy-bad-ts'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'address': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'currency': 'usd', 'data': []}, False, id='alchemy-address-for-symbol'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_AAVE, {'address': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'currency': 'usd', 'data': []}, False, id='alchemy-missing-network'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'symbol': 'BTC', 'currency': 'usd', 'data': []}, True, id='alchemy-empty-data'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.ALCHEMY, A_BTC, {'symbol': 'BTC', 'currency': 'usd', 'data': [{'timestamp': '2021-01-25T09:00:00Z', 'value': '0'}]}, True, id='alchemy-zero-price'),  # noqa: E501
        # Moralis
        pytest.param(HistoricalPriceOracle.MORALIS, A_AAVE, {}, False, id='moralis-missing-price'),
        pytest.param(HistoricalPriceOracle.MORALIS, A_AAVE, {'usdPrice': 'bad'}, False, id='moralis-bad-price'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.MORALIS, A_BTC, None, False, id='moralis-local-unsupported'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.MORALIS, A_AAVE, {'usdPrice': 0}, True, id='moralis-zero-price'),  # noqa: E501
        # Birdeye
        pytest.param(HistoricalPriceOracle.BIRDEYE, A_AAVE, {}, False, id='birdeye-no-items'),
        pytest.param(HistoricalPriceOracle.BIRDEYE, A_AAVE, {'items': [{'unixTime': 'bad', 'value': 100}]}, False, id='birdeye-bad-ts'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.BIRDEYE, A_AAVE, {'items': [{'unixTime': 1611565200}]}, False, id='birdeye-no-value'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.BIRDEYE, A_AAVE, {'items': [{'unixTime': 1611565200, 'value': 'bad'}]}, False, id='birdeye-bad-value'),  # noqa: E501
        pytest.param(HistoricalPriceOracle.BIRDEYE, A_AAVE, {'items': []}, True, id='birdeye-empty-items'),  # noqa: E501
    ],
)
def test_oracle_response_miss_classification(
        globaldb: GlobalDBHandler,
        price_historian: PriceHistorian,
        inquirer: Inquirer,  # pylint: disable=unused-argument
        oracle: HistoricalPriceOracle,
        from_asset: Asset,
        payload: dict[str, Any] | None,
        expect_cached: bool,
) -> None:
    """Malformed oracle payloads and local UnsupportedAsset rejections must not be cached,
    whereas confirmed no-data / zero / low-confidence responses are cached as misses.
    """
    ts = Timestamp(1611565200)  # 25/01/2021 09:00:00 UTC
    daystart_ts = timestamp_to_daystart_timestamp(ts)
    price_historian.set_oracles_order([oracle])
    assert price_historian._oracle_instances is not None
    oracle_instance = price_historian._oracle_instances[0]

    with ExitStack() as stack:
        stack.enter_context(patch.object(oracle_instance, 'can_query_history', return_value=True))
        if oracle == HistoricalPriceOracle.MORALIS:
            stack.enter_context(patch.object(oracle_instance, '_timestamp_to_block', return_value=123456))  # noqa: E501
        if payload is not None:
            stack.enter_context(patch.object(oracle_instance, '_query', return_value=payload))
        with pytest.raises(NoPriceForGivenTimestamp):
            price_historian.query_historical_price(from_asset, A_USD, ts)

    expected_ts = daystart_ts if oracle == HistoricalPriceOracle.COINGECKO else ts
    expected = {(oracle, expected_ts)} if expect_cached else set()
    assert globaldb.get_historical_price_misses(from_asset, (ts, daystart_ts)) == expected
