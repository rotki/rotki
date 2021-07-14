from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.manual_price_oracle import ManualPriceOracle
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.typing import (
    DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER,
    HistoricalPrice,
    HistoricalPriceOracle,
)
from rotkehlchen.tests.utils.constants import A_GBP
from rotkehlchen.typing import Price, Timestamp


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
        elif oracle == HistoricalPriceOracle.MANUAL:
            instance = ManualPriceOracle
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


def test_fiat_to_fiat(fake_price_historian):
    """Test the price is returned via exchangerates API when requesting the
    historical price from fiat to fiat.
    """
    price_historian = fake_price_historian

    expected_price = Price(FVal('1.25'))
    mock_inquirer = MagicMock()
    mock_inquirer.query_historical_fiat_exchange_rates.return_value = expected_price

    with patch('rotkehlchen.history.price.Inquirer', return_value=mock_inquirer):
        price = price_historian.query_historical_price(
            from_asset=A_USD,
            to_asset=A_GBP,
            timestamp=Timestamp(1611595466),
        )

    assert price == expected_price
    assert mock_inquirer.query_historical_fiat_exchange_rates.call_count == 1


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
            oracle_instance.query_historical_price.return_value = Price(ZERO)

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
    oracle_instances[1].query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')
    oracle_instances[2].query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')
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
