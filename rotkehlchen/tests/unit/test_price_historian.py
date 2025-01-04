from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.manual_price_oracles import ManualPriceOracle
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import (
    DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER,
    HistoricalPrice,
    HistoricalPriceOracle,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.types import Price, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import FiatAsset
    from rotkehlchen.inquirer import Inquirer


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
        elif oracle == HistoricalPriceOracle.MANUAL:
            instance = ManualPriceOracle
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
        if not isinstance(oracle_instance, ManualPriceOracle):
            oracle_instance.can_query_history.return_value = False

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1611595466),
        )
    for oracle_instance in price_historian._oracle_instances:
        if not isinstance(oracle_instance, ManualPriceOracle):
            assert oracle_instance.can_query_history.call_count == 1
            assert oracle_instance.query_historical_price.call_count == 0


def test_token_to_fiat_no_price_found_exception(fake_price_historian):
    """Test NoPriceForGivenTimestamp is raised when the all the oracles fail
    requesting the historical price from token to fiat.
    """
    price_historian = fake_price_historian

    for oracle_instance in price_historian._oracle_instances:
        if not isinstance(oracle_instance, ManualPriceOracle):
            oracle_instance.query_historical_price.side_effect = NoPriceForGivenTimestamp(from_asset=A_BTC, to_asset=A_USD, time=1614556800)  # noqa: E501  # make sure they all fail

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1611595466),
        )
    for oracle_instance in price_historian._oracle_instances:
        if not isinstance(oracle_instance, ManualPriceOracle):
            assert oracle_instance.query_historical_price.call_count == 1


def test_token_to_fiat_via_second_oracle(fake_price_historian):
    """Test price is returned via the second oracle when the first oracle fails
    requesting the historical price from token to fiat.
    """
    price_historian = fake_price_historian

    expected_price = Price(FVal('30000'))
    oracle_instances = price_historian._oracle_instances
    oracle_instances[1].query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')
    oracle_instances[2].query_historical_price.return_value = expected_price

    price = price_historian.query_historical_price(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=Timestamp(1611595466),
    )
    assert price == expected_price
    for oracle_instance in price_historian._oracle_instances[1:3]:
        assert oracle_instance.query_historical_price.call_count == 1


def test_manual_oracle_correctly_returns_price(globaldb, fake_price_historian):
    """Test that the manual oracle correctly returns price for asset"""
    price_historian = fake_price_historian
    # Add price at timestamp
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=30000,
            timestamp=Timestamp(1611595470),
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    # Make the other oracles fail
    expected_price = Price(FVal('30000'))
    oracle_instances = price_historian._oracle_instances
    for i in range(1, len(oracle_instances)):
        oracle_instances[i].query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')  # noqa: E501
    # Query price, should return the manual price
    price = price_historian.query_historical_price(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=Timestamp(1611595466),
    )
    assert price == expected_price
    # Try to get manual price for a timestamp not in db
    with pytest.raises(NoPriceForGivenTimestamp):
        price = price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1610595466),
        )


def test_get_historical_prices(globaldb):
    ts1 = Timestamp(1611595470)
    price1, price2, price3, price4 = 30000, 35000, 45000, 77000
    # Add price at timestamp
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price1,
            timestamp=ts1,
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price2,
            timestamp=ts1 + 3600 * 4,
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price3,
            timestamp=ts1 + DAY_IN_SECONDS + 3600,
            source=HistoricalPriceOracle.MANUAL,
        ),
    )
    globaldb.add_single_historical_price(
        HistoricalPrice(
            from_asset=A_BTC,
            to_asset=A_USD,
            price=price4,
            timestamp=ts1 + 4 * DAY_IN_SECONDS + 3600,
            source=HistoricalPriceOracle.MANUAL,
        ),
    )

    result = globaldb.get_historical_prices(
        query_data=[
            (A_BTC, A_USD, ts1 - 3600),
            (A_BTC, A_USD, ts1 + 3600 * 6),
            (A_BTC, A_USD, ts1 + DAY_IN_SECONDS - 3600 * 2),
            (A_BTC, A_USD, ts1 + 2 * DAY_IN_SECONDS + 3600 * 4),
            (A_BTC, A_USD, ts1 + 4 * DAY_IN_SECONDS - 3600),
        ],
        max_seconds_distance=DAY_IN_SECONDS,
    )
    assert [price1, price2, price3, None, price4] == [x.price if x is not None else None for x in result]  # noqa: E501
