from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_ARB, A_DAI, A_ETH, A_EUR, A_LINK, A_USD, A_USDC, A_USDT
from rotkehlchen.errors.misc import RemoteError
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


@pytest.mark.vcr
def test_query_multiple_current_prices_handles_exceptions_and_chunking(session_defillama: 'Defillama'):  # noqa: E501
    """Regression test for query_multiple_current_prices to ensure it properly handles
    exceptions and chunking without failing the entire batch. This prevents the issue where
    large requests cause "413 content too large" errors or individual problematic chunks
    cause all price queries to fail.
    """
    # Test with 6 assets and chunk size of 2 to trigger chunking
    test_assets = [
        A_ETH.resolve_to_asset_with_oracles(),
        A_DAI.resolve_to_asset_with_oracles(),
        A_ARB.resolve_to_asset_with_oracles(),
        A_LINK.resolve_to_asset_with_oracles(),
        A_USDC.resolve_to_asset_with_oracles(),
        A_USDT.resolve_to_asset_with_oracles(),
    ]

    # Mock _query to fail for the first chunk but succeed for others
    original_query, call_count = session_defillama._query, 0

    def mock_query(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # Fail the first chunk to simulate "413 content too large"
            raise RemoteError('413 content too large')

        # Succeed for subsequent chunks
        return original_query(*args, **kwargs)

    with (
        patch('rotkehlchen.externalapis.defillama.DEFILLAMA_CHUNK_SIZE', 2),
        patch.object(session_defillama, '_query', side_effect=mock_query),
    ):
        # This should not raise an exception despite the first chunk failing
        # Instead, it should skip the failed chunk and return prices from successful chunks
        prices = session_defillama.query_multiple_current_prices(
            from_assets=test_assets,
            to_asset=A_USD.resolve_to_asset_with_oracles(),
        )

        # Should have 4 prices from the 2 successful chunks (chunks 2 and 3)
        assert len(prices) == 4
