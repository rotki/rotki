import pytest

from rotkehlchen.constants.assets import A_ARB, A_DAI, A_ETH, A_EUR, A_LINK, A_USD
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials, Price

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
def test_defillama_historical_price(price_historian, session_defillama):  # pylint: disable=unused-argument
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


@pytest.mark.vcr
@pytest.mark.freeze_time('2024-10-10 12:00:00 GMT')
def test_defillama_with_api_key(price_historian, database):  # pylint: disable=unused-argument
    with database.user_write() as write_cursor:  # add the api key to the DB
        database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.DEFILLAMA,
                api_key=(api_key := ApiKey('123totallyrealapikey123')),
            )],
        )

    # assure initialization with the database argument work
    llama = Defillama(database=database)
    assert llama._get_api_key() == api_key

    eth = A_ETH.resolve()
    usd = A_USD.resolve()
    dai = A_DAI.resolve()
    eur = A_EUR.resolve()

    # Check to see query is formulated correctly for current price in pro
    result = llama.query_current_price(
        from_asset=eth,
        to_asset=eur,
    )
    assert result == FVal('3598.5')
    # similar for historical
    result = llama.query_historical_price(
        from_asset=dai,
        to_asset=usd,
        timestamp=1597024800,
    )
    assert result == FVal('1.0182482830027697')


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_query_multiple_current_prices(session_defillama: 'Defillama', inquirer):
    assert session_defillama.query_multiple_current_prices(
        from_assets=[
            A_ARB.resolve_to_asset_with_oracles(),
            A_DAI.resolve_to_asset_with_oracles(),
            A_LINK.resolve_to_asset_with_oracles(),
        ],
        to_asset=A_ETH.resolve_to_asset_with_oracles(),
    ) == {A_ARB: FVal(0.0001843520256), A_DAI: FVal(0.000443575764), A_LINK: FVal(0.007640514)}
