import random
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response,
    assert_proper_response_with_result,
    wait_for_async_task_with_result,
)
from rotkehlchen.types import Price
from rotkehlchen.utils.misc import timestamp_to_date


@pytest.mark.parametrize('mocked_current_prices', [{
    ('BTC', 'USD'): FVal('33183.98'),
    ('GBP', 'USD'): FVal('1.367'),
}])
def test_get_current_assets_price_in_usd(rotkehlchen_api_server):
    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'assets': ['BTC', 'USD', 'GBP'],
            'target_asset': 'USD',
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['assets']['BTC'] == '33183.98'
    assert result['assets']['GBP'] == '1.367'
    assert result['assets']['USD'] == '1'
    assert result['target_asset'] == 'USD'


@pytest.mark.parametrize('mocked_current_prices', [{
    ('USD', 'BTC'): FVal('0.00003013502298398202988309419184'),
    ('GBP', 'BTC'): FVal('0.00004119457641910343485018976024'),
}])
def test_get_current_assets_price_in_btc(rotkehlchen_api_server):

    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'assets': ['BTC', 'USD', 'GBP'],
            'target_asset': 'BTC',
            'async_query': async_query,
        },
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        result = wait_for_async_task_with_result(rotkehlchen_api_server, task_id)
    else:
        result = assert_proper_response_with_result(response)

    assert len(result) == 2
    assert result['assets']['BTC'] == '1'
    assert result['assets']['GBP'] == '0.00004119457641910343485018976024'
    assert result['assets']['USD'] == '0.00003013502298398202988309419184'
    assert result['target_asset'] == 'BTC'


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_add_manual_current_price(rotkehlchen_api_server):
    """Check that addition of manual current prices work fine."""
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(100)),
    )
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'target_asset': A_EUR.identifier,
            'assets': [A_ETH.identifier, A_USD.identifier],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['assets']['ETH'] == '100'  # check that manual current price was used
    assert result['assets']['USD'] != '100'

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'target_asset': A_ETH.identifier,
            'assets': [A_EUR.identifier],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['assets']['EUR'] != '0.01'  # should not work vice versa
    assert result['assets']['EUR'] != '100'

    # Check that if we have two manual current prices, both are used
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'from_asset': A_USD.identifier,
            'to_asset': A_EUR.identifier,
            'price': '23',
        },
    )
    assert_proper_response(response)
    assert GlobalDBHandler().get_manual_current_price(A_USD) == (A_EUR, Price(FVal(23)))

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'target_asset': A_EUR.identifier,
            'assets': [A_ETH.identifier, A_USD.identifier],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['assets']['ETH'] == '100'
    assert result['assets']['USD'] == '23'


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_edit_manual_current_price(rotkehlchen_api_server):
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(10)),
    )
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_USD,
        to_asset=A_EUR,
        price=Price(FVal(25)),
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'from_asset': A_ETH.identifier,
            'to_asset': A_EUR.identifier,
            'price': '45',
        },
    )
    assert_proper_response(response)
    # After putting new manual current price, the previous one should have become historical
    assert GlobalDBHandler().get_manual_prices(from_asset=A_ETH, to_asset=A_EUR)[0]['price'] == '10'  # noqa: E501

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'target_asset': A_EUR.identifier,
            'assets': [A_ETH.identifier, A_USD.identifier],
        },
    )
    result = assert_proper_response_with_result(response)
    assert result['assets']['ETH'] == '45'
    assert result['assets']['USD'] == '25'

    # Now check that if there is a manual historical price entry at the same timestamp as our
    # manual current price, proper error is returned.
    with GlobalDBHandler().conn.read_ctx() as cursor:
        manual_current_timestamp = cursor.execute(
            'SELECT timestamp FROM price_history WHERE source_type=? AND from_asset=?',
            (HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(), A_ETH.identifier),
        ).fetchone()[0]

    GlobalDBHandler().add_single_historical_price(entry=HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=manual_current_timestamp,
        price=ONE,
        source=HistoricalPriceOracle.MANUAL,
    ))
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'from_asset': A_ETH.identifier,
            'to_asset': A_EUR.identifier,
            'price': '78',
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg=f'already exists at {timestamp_to_date(ts=manual_current_timestamp)}',
        status_code=HTTPStatus.CONFLICT,
    )


def test_remove_manual_current_price(rotkehlchen_api_server):
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(10)),
    )
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_USD,
        to_asset=A_EUR,
        price=Price(FVal(25)),
    )
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'asset': A_ETH.identifier,
        },
    )
    assert_proper_response(response)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'currentassetspriceresource',
        ),
        json={
            'asset': A_ETH.identifier,
        },
    )
    assert_error_response(
        response=response,
        contained_in_msg='Not found manual current price to delete',
        status_code=HTTPStatus.CONFLICT,
    )
    # usd manual current price should have not been touched
    assert GlobalDBHandler().get_manual_current_price(A_USD) == (A_EUR, Price(FVal(25)))


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_manual_current_prices_loop(inquirer):
    """Check that if we got a loop of manual current prices
    (e.g. 1 ETH costs 2 BTC and 1 BTC costs 5 ETH), it is handled properly."""
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_ETH,
        to_asset=A_USD,
        price=ONE,
    )
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_USD,
        to_asset=A_BTC,
        price=ONE,
    )
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_BTC,
        to_asset=A_ETH,
        price=ONE,
    )
    price = inquirer.find_price(from_asset=A_ETH, to_asset=A_EUR)
    assert price > 100  # should be real ETH price
    warnings = inquirer._msg_aggregator.consume_warnings()
    assert len(warnings) == 1
    assert 'from ETH(Ethereum) to EUR(Euro) since your manual latest' in warnings[0]


@pytest.mark.parametrize('ignore_mocked_prices_for', ['ETH'])
def test_inquirer_oracles_affect_manual_price(inquirer):
    """Checks that change of oracles order affects manual current price usage."""
    GlobalDBHandler().add_manual_current_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(2)),
    )
    assert inquirer.find_usd_price(A_ETH) == 3  # (2 EUR per ETH) * (1.5 USD per EUR)
    inquirer.set_oracles_order(
        oracles=[CurrentPriceOracle.COINGECKO, CurrentPriceOracle.MANUALCURRENT],
    )
    assert inquirer.find_usd_price(A_ETH) == 3  # Should remain the same since cache should be hit
    inquirer.remove_cached_current_price_entry(cache_key=(A_ETH, A_USD))
    assert inquirer.find_usd_price(A_ETH) > 100  # should have real price now
