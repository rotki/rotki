from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.constants.assets import A_BTC, A_GBP, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset, RemoteError
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.fval import FVal
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.typing import (
    DEFAULT_HISTORICAL_PRICE_ORACLE_ORDER,
    HistoricalPriceOracle,
    HistoricalPriceOracleProperties,
)
from rotkehlchen.typing import Price, Timestamp


@pytest.fixture(name='oracle_order')
def fixture_oracle_order():
    return DEFAULT_HISTORICAL_PRICE_ORACLE_ORDER


@pytest.fixture(name='price_historian')
def fixture_price_historian(oracle_order):
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    PriceHistorian._PriceHistorian__instance = None
    price_historian = PriceHistorian(
        data_directory=MagicMock(spec=Path),
        cryptocompare=MagicMock(spec=Cryptocompare),
        coingecko=MagicMock(spec=Coingecko),
        oracle_order=oracle_order,
    )
    return price_historian


def test_all_common_methods_implemented():
    """Test all historical price oracles implement the expected methods.
    """
    for oracle in DEFAULT_HISTORICAL_PRICE_ORACLE_ORDER:
        if oracle == HistoricalPriceOracle.COINGECKO:
            instance = Coingecko
        elif oracle == HistoricalPriceOracle.CRYPTOCOMPARE:
            instance = Cryptocompare
        else:
            raise AssertionError(
                f'Unexpected historical price oracle: {oracle}. Update this test',
            )

        # Check 'rate_limited_in_last' method exists
        assert hasattr(instance, 'rate_limited_in_last')
        assert callable(instance.rate_limited_in_last)
        # Check 'query_historical_price' method exists
        assert hasattr(instance, 'query_historical_price')
        assert callable(instance.query_historical_price)


def test_oracle_instances_default_order(price_historian):
    expected_oracle_instances = [
        (HistoricalPriceOracle.CRYPTOCOMPARE, price_historian._cryptocompare),
        (HistoricalPriceOracle.COINGECKO, price_historian._coingecko),
    ]
    assert price_historian._oracle_instances == expected_oracle_instances


@pytest.mark.parametrize('oracle_order', [
    [HistoricalPriceOracle.COINGECKO, HistoricalPriceOracle.CRYPTOCOMPARE],
])
def test_oracle_instances_custom_order(price_historian):
    expected_oracle_instances = [
        (HistoricalPriceOracle.COINGECKO, price_historian._coingecko),
        (HistoricalPriceOracle.CRYPTOCOMPARE, price_historian._cryptocompare),
    ]
    assert price_historian._oracle_instances == expected_oracle_instances


def test_fiat_to_fiat(price_historian):
    """Test the price is returned via exchangerates API when requesting the
    historical price from fiat to fiat.
    """
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


def test_fiat_to_fiat_no_price_found_exception(price_historian):
    """Test NoPriceForGivenTimestamp is raised when requesting the historical
    price from fiat to fiat and:
      - Inquirer returns None.
      - The other oracles don't support fiat to fiat.

    FakeHistoricalPriceOracle sets 'has_fiat_to_fiat' to False.
    """
    class FakeHistoricalPriceOracle(Enum):
        COINGECKO = 1
        CRYPTOCOMPARE = 2

        def properties(self):
            if self == FakeHistoricalPriceOracle.COINGECKO:
                return HistoricalPriceOracleProperties(has_fiat_to_fiat=False)
            if self == FakeHistoricalPriceOracle.CRYPTOCOMPARE:
                return HistoricalPriceOracleProperties(has_fiat_to_fiat=False)
            raise AssertionError(f'Unexpected HistoricalPriceOracle: {self}')

    price_historian._oracle_instances = [
        (FakeHistoricalPriceOracle.CRYPTOCOMPARE, price_historian._cryptocompare),
        (FakeHistoricalPriceOracle.COINGECKO, price_historian._coingecko),
    ]
    expected_price = None
    mock_inquirer = MagicMock()
    mock_inquirer.query_historical_fiat_exchange_rates.return_value = expected_price

    with patch('rotkehlchen.history.price.Inquirer', return_value=mock_inquirer):
        with pytest.raises(NoPriceForGivenTimestamp):
            price_historian.query_historical_price(
                from_asset=A_USD,
                to_asset=A_GBP,
                timestamp=Timestamp(1611595466),
            )

    assert mock_inquirer.query_historical_fiat_exchange_rates.call_count == 1
    for _, oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.query_historical_price.call_count == 0


def test_fiat_to_fiat_via_second_oracle(price_historian):
    """Test the price is returned via the second oracle when requesting the
    historical price from fiat to fiat and:
      - Inquirer returns None.
      - The first oracle fails with an exception.

    FakeHistoricalPriceOracle sets 'has_fiat_to_fiat' to True.
    """
    class FakeHistoricalPriceOracle(Enum):
        COINGECKO = 1
        CRYPTOCOMPARE = 2

        def properties(self):
            if self == FakeHistoricalPriceOracle.COINGECKO:
                return HistoricalPriceOracleProperties(has_fiat_to_fiat=True)
            if self == FakeHistoricalPriceOracle.CRYPTOCOMPARE:
                return HistoricalPriceOracleProperties(has_fiat_to_fiat=True)
            raise AssertionError(f'Unexpected HistoricalPriceOracle: {self}')

    price_historian._oracle_instances = [
        (FakeHistoricalPriceOracle.CRYPTOCOMPARE, price_historian._cryptocompare),
        (FakeHistoricalPriceOracle.COINGECKO, price_historian._coingecko),
    ]
    expected_price = Price(FVal('1.25'))
    price_historian._oracle_instances[0][1].query_historical_price.side_effect = RemoteError
    price_historian._oracle_instances[1][1].query_historical_price.return_value = expected_price
    mock_inquirer = MagicMock()
    mock_inquirer.query_historical_fiat_exchange_rates.return_value = None

    with patch('rotkehlchen.history.price.Inquirer', return_value=mock_inquirer):
        price = price_historian.query_historical_price(
            from_asset=A_USD,
            to_asset=A_GBP,
            timestamp=Timestamp(1611595466),
        )
    assert price == expected_price
    assert mock_inquirer.query_historical_fiat_exchange_rates.call_count == 1
    for _, oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.query_historical_price.call_count == 1


def test_token_to_fiat_all_rate_limited_in_last_no_price_found_exception(price_historian):
    """Test NoPriceForGivenTimestamp is raised when all the oracles have
    exceeded the rate limits. This test also applies to "from fiat to fiat".
    """
    for _, oracle_instance in price_historian._oracle_instances:
        oracle_instance.rate_limited_in_last.return_value = True

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1611595466),
        )
    for _, oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.rate_limited_in_last.call_count == 1
        assert oracle_instance.query_historical_price.call_count == 0


def test_token_to_fiat_no_price_found_exception(price_historian):
    """Test NoPriceForGivenTimestamp is raised when the all the oracles fail
    requesting the historical price from token to fiat.
    """
    oracle_instances = price_historian._oracle_instances
    oracle_instances[0][1].query_historical_price.return_value = Price(ZERO)
    oracle_instances[1][1].query_historical_price.return_value = Price(ZERO)

    with pytest.raises(NoPriceForGivenTimestamp):
        price_historian.query_historical_price(
            from_asset=A_BTC,
            to_asset=A_USD,
            timestamp=Timestamp(1611595466),
        )
    for _, oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.query_historical_price.call_count == 1


def test_token_to_fiat_via_second_oracle(price_historian):
    """Test price is returned via the second oracle when the first oracle fails
    requesting the historical price from token to fiat.
    """
    expected_price = Price(FVal('30000'))
    oracle_instances = price_historian._oracle_instances
    oracle_instances[0][1].query_historical_price.side_effect = PriceQueryUnsupportedAsset('bitcoin')  # noqa: E501
    oracle_instances[1][1].query_historical_price.return_value = expected_price

    price = price_historian.query_historical_price(
        from_asset=A_BTC,
        to_asset=A_USD,
        timestamp=Timestamp(1611595466),
    )
    assert price == expected_price
    for _, oracle_instance in price_historian._oracle_instances:
        assert oracle_instance.query_historical_price.call_count == 1
