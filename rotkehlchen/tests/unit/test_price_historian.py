from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V2, CPT_UNISWAP_V3
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_POL_HARDFORK
from rotkehlchen.constants.assets import A_AAVE, A_BTC, A_ETH_MATIC, A_ETH_POL, A_POL, A_USD
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import _prioritize_manual_balances_query
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

    assert price_historian._oracles == [HistoricalPriceOracle.COINGECKO]
    assert price_historian._oracle_instances == [price_historian._coingecko]


def test_fiat_to_fiat(
        fake_price_historian: PriceHistorian,
        inquirer: 'Inquirer',  # pylint: disable=unused-argument
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
            from_fiat_currency: 'FiatAsset',
            to_fiat_currency: 'FiatAsset',
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


def test_get_historical_prices(globaldb: 'GlobalDBHandler') -> None:
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
            source=HistoricalPriceOracle.CRYPTOCOMPARE,
            timestamp=expected_timestamp,
            price=expected_price,
        )])


def test_price_priority_order():
    """Test to ensure that we detect changes on the constant value returned"""
    _, priority_value = _prioritize_manual_balances_query()
    assert priority_value == HistoricalPriceOracle.MANUAL.serialize_for_db()


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

    assert price.is_close('3591639.375183')


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

    assert price.is_close('91.707127')


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
