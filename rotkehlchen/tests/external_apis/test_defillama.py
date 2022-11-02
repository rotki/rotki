import pytest

from rotkehlchen.constants.assets import A_DAI, A_ETH, A_EUR, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.types import Price

defillama_mocked_historical_prices = {
    'USD': {
        'EUR': {
            1597024800: FVal('1.007'),
        },
    },
}


@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('ignore_mocked_prices_for', ['ETH'])
@pytest.mark.parametrize('mocked_price_queries', [defillama_mocked_historical_prices])
def test_defillama_historical_price(price_historian, session_defillama):  # pylint: disable=unused-argument  # noqa: E501
    eth = A_ETH.resolve()
    usd = A_USD.resolve()
    dai = A_DAI.resolve()
    eur = A_EUR.resolve()

    # First query usd price
    price = session_defillama.query_historical_price(
        from_asset=eth,
        to_asset=usd,
        timestamp=1597024800,
    )
    assert price == Price(FVal('394.35727832860067'))

    # Query EUR price
    price = session_defillama.query_historical_price(
        from_asset=eth,
        to_asset=eur,
        timestamp=1597024800,
    )
    assert price == Price(FVal('394.35727832860067') * FVal('1.007'))

    # Query an evm token
    price = session_defillama.query_historical_price(
        from_asset=dai,
        to_asset=usd,
        timestamp=1597024800,
    )
    assert price == Price(FVal('1.0182482830027697'))


def test_defillama_current_price(inquirer, session_defillama, session_coingecko):  # pylint: disable=unused-argument  # noqa: E501
    eth = A_ETH.resolve()
    usd = A_USD.resolve()
    dai = A_DAI.resolve()
    eur = A_EUR.resolve()

    # Test cryptoasset
    price_defillama, _ = session_defillama.query_current_price(
        from_asset=eth,
        to_asset=usd,
        match_main_currency=False,
    )
    price_coingecko, _ = session_coingecko.query_current_price(
        from_asset=eth,
        to_asset=usd,
        match_main_currency=False,
    )
    assert price_coingecko.is_close(price_defillama, max_diff='10')

    # Test evm assets
    price_defillama, _ = session_defillama.query_current_price(
        from_asset=dai,
        to_asset=usd,
        match_main_currency=False,
    )
    price_coingecko, _ = session_coingecko.query_current_price(
        from_asset=dai,
        to_asset=usd,
        match_main_currency=False,
    )
    assert price_coingecko.is_close(price_defillama, max_diff='0.1')

    # Test a non usd pair
    # Test evm assets
    price_defillama, _ = session_defillama.query_current_price(
        from_asset=dai,
        to_asset=eur,
        match_main_currency=False,
    )
    price_coingecko, _ = session_coingecko.query_current_price(
        from_asset=dai,
        to_asset=eur,
        match_main_currency=False,
    )
    # Multiply by 1.5 because we are mocking rates queries
    assert (price_coingecko * FVal('1.5')).is_close(price_defillama, max_diff='0.1')
