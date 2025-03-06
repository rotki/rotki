import random
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_EUR, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.types import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.inquirer import CurrentPriceOracle, Inquirer
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_response_with_result,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Price
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('mocked_current_prices_with_oracles', [{
    ('BTC', 'USD'): (FVal('33183.98'), CurrentPriceOracle.BLOCKCHAIN),
    ('GBP', 'USD'): (FVal('1.367'), CurrentPriceOracle.FIAT),
}])
@pytest.mark.parametrize('ignore_mocked_prices_for', [['USD']])
def test_get_current_assets_price_in_usd(rotkehlchen_api_server: 'APIServer') -> None:
    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': ['BTC', 'USD', 'GBP'],
            'target_asset': 'USD',
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert len(result) == 3
    assert result['assets']['BTC'] == ['33183.98', CurrentPriceOracle.BLOCKCHAIN.value]
    assert result['assets']['GBP'] == ['1.367', CurrentPriceOracle.FIAT.value]
    assert result['assets']['USD'] == ['1', CurrentPriceOracle.MANUALCURRENT.value]
    assert result['target_asset'] == 'USD'
    assert result['oracles'] == {str(oracle): oracle.value for oracle in CurrentPriceOracle}


@pytest.mark.parametrize('mocked_current_prices_with_oracles', [{
    ('USD', 'BTC'): (FVal('0.00003013502298398202988309419184'), CurrentPriceOracle.COINGECKO),
    ('GBP', 'BTC'): (FVal('0.00004119457641910343485018976024'), CurrentPriceOracle.COINGECKO),
}])
@pytest.mark.parametrize('ignore_mocked_prices_for', [['BTC']])
def test_get_current_assets_price_in_btc(rotkehlchen_api_server: 'APIServer') -> None:

    async_query = random.choice([False, True])
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': ['BTC', 'USD', 'GBP'],
            'target_asset': 'BTC',
            'async_query': async_query,
        },
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=async_query,
    )

    assert len(result) == 3
    assert result['assets']['BTC'] == ['1', CurrentPriceOracle.MANUALCURRENT.value]
    assert result['assets']['GBP'] == ['0.00004119457641910343485018976024', CurrentPriceOracle.COINGECKO.value]  # noqa: E501
    assert result['assets']['USD'] == ['0.00003013502298398202988309419184', CurrentPriceOracle.COINGECKO.value]  # noqa: E501
    assert result['target_asset'] == 'BTC'


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_get_current_assets_price_with_replacements(rotkehlchen_api_server: 'APIServer') -> None:
    """Regression test for a problem where the logic for replacing collection assets with the
    main asset was failing with a KeyError when the main asset was not included in the query.
    """
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': (assets := [  # Several WBTC variants, but not BTC itself
                'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
                'eip155:10/erc20:0x73E0C0d45E048D25Fc26Fa3159b0aA04BfA4Db98',
                'eip155:137/erc20:0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
            ]),
            'target_asset': 'USD',
        },
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
    )
    for asset in assets:
        assert asset in result['assets']


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_add_manual_latest_price(rotkehlchen_api_server: 'APIServer') -> None:
    """Check that addition of manual current prices work fine."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    get_or_create_evm_token(  # create a specific token in base
        userdb=rotki.data.db,
        evm_address=string_to_evm_address('0xe66E3A37C3274Ac24FE8590f7D84A2427194DC17'),
        chain_id=ChainID.BASE,
    )
    response = requests.put(  # add a latest price for it
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': 'eip155:8453/erc20:0xe66E3A37C3274Ac24FE8590f7D84A2427194DC17',
            'to_asset': A_ETH.identifier,
            'price': '42',
        },
    )  # make sure it's there
    assert GlobalDBHandler.get_manual_current_price(Asset('eip155:8453/erc20:0xe66E3A37C3274Ac24FE8590f7D84A2427194DC17')) == (A_ETH, Price(FVal(42)))  # noqa: E501
    response = requests.put(  # now
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': A_ETH.identifier,
            'to_asset': A_EUR.identifier,
            'price': '100',
        },
    )
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'target_asset': A_EUR.identifier,
            'assets': [A_ETH.identifier, A_USD.identifier],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['assets']['ETH'] == ['100', CurrentPriceOracle.MANUALCURRENT.value]  # check that manual current price was used  # noqa: E501
    assert result['assets']['USD'][0] != '100'

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'target_asset': A_ETH.identifier,
            'assets': [A_EUR.identifier],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['assets']['EUR'][0] != '0.01'  # should not work vice versa
    assert result['assets']['EUR'][0] != '100'

    # Check that if we have two manual current prices, both are used
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': A_USD.identifier,
            'to_asset': A_EUR.identifier,
            'price': '23',
        },
    )
    assert_proper_response(response)
    assert GlobalDBHandler.get_manual_current_price(A_USD) == (A_EUR, Price(FVal(23)))

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'target_asset': A_EUR.identifier,
            'assets': [A_ETH.identifier, A_USD.identifier],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['assets']['ETH'] == ['100', CurrentPriceOracle.MANUALCURRENT.value]
    assert result['assets']['USD'] == ['23', CurrentPriceOracle.MANUALCURRENT.value]

    # check that if the from and to assets are the same, an error is thrown.
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': A_EUR.identifier,
            'to_asset': A_EUR.identifier,
            'price': '23',
        },
    )
    assert_error_response(response, 'The from and to assets must be different')


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_edit_manual_current_price(rotkehlchen_api_server: 'APIServer') -> None:
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(10)),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_USD,
        to_asset=A_EUR,
        price=Price(FVal(25)),
    )
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': A_ETH.identifier,
            'to_asset': A_EUR.identifier,
            'price': '45',
        },
    )
    assert_proper_response(response)
    # After putting new manual current price, the previous one should have become historical
    assert GlobalDBHandler.get_manual_prices(from_asset=A_ETH, to_asset=A_EUR)[0]['price'] == '10'

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'target_asset': A_EUR.identifier,
            'assets': [A_ETH.identifier, A_USD.identifier],
        },
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['assets']['ETH'][0] == '45'
    assert result['assets']['USD'][0] == '25'

    # Now check that if there is a manual historical price entry at the same timestamp as our
    # manual current price, proper error is returned.
    with GlobalDBHandler().conn.read_ctx() as cursor:
        manual_current_timestamp = cursor.execute(
            'SELECT timestamp FROM price_history WHERE source_type=? AND from_asset=?',
            (HistoricalPriceOracle.MANUAL_CURRENT.serialize_for_db(), A_ETH.identifier),
        ).fetchone()[0]

    GlobalDBHandler.add_single_historical_price(entry=HistoricalPrice(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=manual_current_timestamp,
        price=Price(ONE),
        source=HistoricalPriceOracle.MANUAL,
    ))
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
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


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_remove_manual_current_price(rotkehlchen_api_server: 'APIServer') -> None:
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(10)),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_USD,
        to_asset=A_EUR,
        price=Price(FVal(25)),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_BTC,
        to_asset=A_ETH,
        price=Price(FVal(100)),
    )
    # add the prices to the inquirer cache
    eth_eur_price = Inquirer().find_price(from_asset=A_ETH, to_asset=A_EUR)
    assert eth_eur_price == Price(FVal(10))
    btc_eth_price = Inquirer().find_price(from_asset=A_BTC, to_asset=A_ETH)
    assert btc_eth_price == Price(FVal(100))

    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'asset': A_ETH.identifier,
        },
    )
    assert_proper_response(response)
    response = requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
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
    assert GlobalDBHandler.get_manual_current_price(A_USD) == (A_EUR, Price(FVal(25)))
    # Check that the cache in the inquirer has been invalidated
    assert (A_ETH, A_EUR) not in Inquirer()._cached_current_price
    assert (A_BTC, A_ETH) not in Inquirer()._cached_current_price


@pytest.mark.vcr
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_manual_current_prices_loop(inquirer: 'Inquirer') -> None:
    """Check that if we got a loop of manual current prices
    (e.g. 1 ETH costs 2 BTC and 1 BTC costs 5 ETH), it is handled properly.

    This test is mocked because we were seeing cases of tests failing due to
    an exception from coingecko API.
    """
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_ETH,
        to_asset=A_USD,
        price=Price(ONE),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_USD,
        to_asset=A_BTC,
        price=Price(ONE),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_BTC,
        to_asset=A_ETH,
        price=Price(ONE),
    )
    price = inquirer.find_price(
        from_asset=A_ETH.resolve_to_asset_with_oracles(),
        to_asset=A_EUR.resolve_to_asset_with_oracles(),
    )
    assert price == FVal('1570.92')  # it must be equal to the mocked price at the time


@pytest.mark.vcr
@pytest.mark.parametrize('ignore_mocked_prices_for', ['ETH'])
def test_inquirer_oracles_does_not_affect_manual_price(inquirer: 'Inquirer') -> None:
    """Checks that change of oracles order does not affect manual current price usage.

    This test is mocked because we were seeing cases of tests failing due to
    an exception from coingecko API.
    """
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(2)),
    )
    assert inquirer.find_usd_price(A_ETH) == 3  # (2 EUR per ETH) * (1.5 USD per EUR)
    inquirer.set_oracles_order(
        oracles=[CurrentPriceOracle.COINGECKO, CurrentPriceOracle.MANUALCURRENT],
    )
    assert inquirer.find_usd_price(A_ETH) == 3  # Should remain the same since cache should be hit
    Inquirer._cached_current_price.remove((A_ETH, A_USD))
    assert inquirer.find_usd_price(A_ETH) == 3  # manual price is still prioritized


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_get_all_current_prices(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the endpoint to fetch all manual input returns the correct prices results"""
    # Check that when there are no entries in the database the result is empty
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == []

    # Add prices to the database and one that overwrites another with the same from/to
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(10)),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        price=Price(FVal(5)),
    )
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_EUR,
        to_asset=A_USD,
        price=Price(FVal(1.01)),
    )

    # Check that the old ETH -> EUR price has become historical
    with GlobalDBHandler().conn.read_ctx() as cursor:
        cursor.execute(
            'SELECT source_type FROM price_history WHERE from_asset=? AND price=?',
            ('ETH', '10'),
        )
        assert cursor.fetchone()[0] == HistoricalPriceOracle.MANUAL.serialize_for_db()

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    expected_response = [
        {'from_asset': 'ETH', 'to_asset': 'EUR', 'price': '5'},
        {'from_asset': 'EUR', 'to_asset': 'USD', 'price': '1.01'},
    ]
    assert result == expected_response

    # try filtering by to asset
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
        json={'to_asset': 'USD'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [{'from_asset': 'EUR', 'to_asset': 'USD', 'price': '1.01'}]

    # try filtering by from asset
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
        json={'from_asset': 'ETH'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [{'from_asset': 'ETH', 'to_asset': 'EUR', 'price': '5'}]

    # try filtering both fields
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
        json={'from_asset': 'ETH', 'to_asset': 'EUR'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [{'from_asset': 'ETH', 'to_asset': 'EUR', 'price': '5'}]

    # try empty search
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
        json={'from_asset': 'ETH', 'to_asset': 'USD'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 0


@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_prices_cache_invalidation_for_manual_prices(rotkehlchen_api_server: 'APIServer') -> None:
    """
    Check that the prices cache are properly invalidated upon addition
    and deletion of manual prices.

    Prices are not mocked in order to get the latest prices
    and not a constant value when adjustments are made to the amount.
    """
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': 'ETH',
            'to_asset': 'BTC',
            'price': '1',
        },
    )
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': 'AVAX',
            'to_asset': 'ETH',
            'price': '1',
        },
    )

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': ['ETH'],
            'target_asset': 'USD',
            'ignore_cache': False,
        },
    )
    old_result = assert_proper_sync_response_with_result(response)

    # now update the btc price of eth manually and see that usd price returned is
    # the latest price when `ignore_cache` is False.
    requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'from_asset': 'ETH',
            'to_asset': 'BTC',
            'price': '10',
        },
    )
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': ['ETH'],
            'target_asset': 'USD',
        },
    )
    result = assert_proper_sync_response_with_result(response)
    # the max diff is to account for price changes between the requests interval
    assert FVal(result['assets']['ETH'][0]).is_close(FVal(old_result['assets']['ETH'][0]) * 10, max_diff='100')  # noqa: E501
    assert result['target_asset'] == 'USD'

    # now delete the price of ETH to verify that
    # the price of AVAX -> USD == actual ETH -> USD
    requests.delete(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={'asset': 'ETH'},
    )
    # now get the price of AVAX
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': ['AVAX'],
            'target_asset': 'USD',
        },
    )
    avax_result = assert_proper_sync_response_with_result(response)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'latestassetspriceresource',
        ),
        json={
            'assets': ['ETH'],
            'target_asset': 'USD',
        },
    )
    eth_result = assert_proper_sync_response_with_result(response)
    # # the max diff is to account for price changes between the requests interval
    assert FVal(avax_result['assets']['AVAX'][0]).is_close(FVal(eth_result['assets']['ETH'][0]), max_diff='10')  # noqa: E501
    assert result['target_asset'] == 'USD'


@pytest.mark.parametrize('should_mock_current_price_queries', [True])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('ethereum_modules', [['nfts']])
def test_get_manual_prices_with_nfts(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that the endpoint to fetch all manual input returns the correct prices results
    when there are prices for normal assets and nfts
    """
    # Add prices to the database
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    GlobalDBHandler.add_manual_latest_price(
        from_asset=A_BTC,
        to_asset=A_ETH,
        price=Price(FVal(10)),
    )

    with rotki.data.db.user_write() as cursor:
        nft_id_1 = '_nft_custom'
        nft_id_2 = '_nft_custom2'
        cursor.executemany(
            'INSERT OR IGNORE INTO assets(identifier) VALUES(?)',
            [(nft_id_1,), (nft_id_2,)],
        )
        cursor.executemany(
            'INSERT OR IGNORE INTO nfts('
            'identifier, name, last_price, last_price_asset, manual_price, owner_address, is_lp, image_url, collection_name'  # noqa: E501
            ') VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                (nft_id_1, 'Custom NFT', '1', 'ETH', 1, ethereum_accounts[0], 0, '', 'custom'),
                (nft_id_2, 'Custom NFT', '2', 'BTC', 1, ethereum_accounts[0], 0, '', 'custom'),
            ],
        )

    # test a response with NFTs and non NFTs assets
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
        json={'to_asset': 'ETH'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [
        {
            'from_asset': 'BTC',
            'to_asset': 'ETH',
            'price': '10',
        },
        {
            'from_asset': '_nft_custom',
            'to_asset': 'ETH',
            'price': '1',
        },
    ]

    # test a response with only NFTs
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'alllatestassetspriceresource',
        ),
        json={'to_asset': 'BTC'},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == [
        {
            'from_asset': '_nft_custom2',
            'to_asset': 'BTC',
            'price': '2',
        },
    ]
