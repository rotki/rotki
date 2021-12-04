import os
import shutil
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.chain.ethereum.interfaces.ammswap.typing import EventType, LiquidityPoolEvent
from rotkehlchen.chain.ethereum.modules.balancer.typing import BalancerBPTEventType, BalancerEvent
from rotkehlchen.chain.ethereum.trades import AMMSwap
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.assets import A_ETH, A_EUR, A_USD
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response_with_result,
)
from rotkehlchen.tests.utils.dataimport import (
    assert_bisq_trades_import_results,
    assert_blockfi_trades_import_results,
    assert_blockfi_transactions_import_results,
    assert_cointracking_import_results,
    assert_cryptocom_import_results,
    assert_cryptocom_special_events_import_results,
    assert_custom_cointracking,
    assert_nexo_results,
    assert_shapeshift_trades_import_results,
    assert_uphold_transactions_import_results,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ChecksumEthAddress,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_data_import_cointracking(rotkehlchen_api_server, file_upload):
    """Test that the data import endpoint works successfully for cointracking

    To test that data import works both with specifying filepath and uploading
    the file try both ways in this test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    if file_upload:
        files = {'file': open(filepath, 'rb')}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ),
            files=files,
            data={'source': 'cointracking.info'},
        )
    else:
        json_data = {'source': 'cointracking.info', 'file': str(filepath)}
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ), json=json_data,
        )

    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_cointracking_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_cryptocom(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for cryptocom"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cryptocom_trades_list.csv'

    json_data = {'source': 'cryptocom', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_cryptocom_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_cryptocom_special_types(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for cryptocom"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cryptocom_special_events.csv'

    json_data = {'source': 'cryptocom', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_cryptocom_special_events_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_blockfi_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for blockfi transactions"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-transactions.csv'

    json_data = {'source': 'blockfi-transactions', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_blockfi_transactions_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_blockfi_trades(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for blockfi trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'blockfi-trades.csv'

    json_data = {'source': 'blockfi-trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_blockfi_trades_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_nexo(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for nexo"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'nexo.csv'

    json_data = {'source': 'nexo', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_nexo_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_shapeshift_trades(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for shapeshift trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'shapeshift-trade-history.csv'

    json_data = {'source': 'shapeshift-trades', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_shapeshift_trades_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_uphold_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for uphold trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'uphold-transaction-history.csv'

    json_data = {'source': 'uphold', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_uphold_transactions_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_bisq_transactions(rotkehlchen_api_server):
    """Test that the data import endpoint works successfully for uphold trades"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'bisq_trades.csv'

    json_data = {'source': 'bisq', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported successfully
    assert_bisq_trades_import_results(rotki)


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_data_import_wrong_extension(rotkehlchen_api_server, file_upload):
    """Test that uploading a file without the proper extension fails"""
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    # Let's also try to upload a file without the csv prefix
    with TemporaryDirectory() as temp_directory:
        bad_filepath = Path(temp_directory) / 'somefile.bad'
        shutil.copyfile(filepath, bad_filepath)
        if file_upload:
            files = {'file': open(bad_filepath, 'rb')}
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ),
                files=files,
                data={'source': 'cointracking.info'},
            )
        else:
            json_data = {'source': 'cointracking.info', 'file': str(bad_filepath)}
            response = requests.put(
                api_url_for(
                    rotkehlchen_api_server,
                    'dataimportresource',
                ), json=json_data,
            )

    assert_error_response(
        response=response,
        contained_in_msg='does not end in any of .csv',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_data_import_errors(rotkehlchen_api_server, tmpdir_factory):
    """Test that errors in the data import endpoint are handled correctly"""
    dir_path = Path(__file__).resolve().parent.parent
    filepath = dir_path / 'data' / 'cointracking_trades_list.csv'

    # Test that if filepath is missing, an error is returned
    json_data = {'source': 'cointracking.info'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='file": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is missing, an error is returned
    json_data = {'filepath': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='source": ["Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is an invalid type an error is returned
    json_data = {'source': 55, 'filepath': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='source": ["Not a valid string."',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if source is invalid an error is returned
    json_data = {'source': 'somewhere', 'file': str(filepath)}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            "dataimportresource",
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='source": ["Must be one of: cointracking.info',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is invalid type an error is returned
    json_data = {'source': 'cointracking.info', 'file': 22}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Provided non string or file type for file',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is not a valid path an error is returned
    json_data = {'source': 'cointracking.info', 'file': '/not/a/valid/path'}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='Given path /not/a/valid/path does not exist',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test that if filepath is a directory an error is returned
    test_dir = str(tmpdir_factory.mktemp('test_dir'))
    json_data = {'source': 'cointracking.info', 'file': test_dir}
    response = requests.put(
        api_url_for(
            rotkehlchen_api_server,
            'dataimportresource',
        ), json=json_data,
    )
    assert_error_response(
        response=response,
        contained_in_msg='is not a file',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('file_upload', [True, False])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_data_import_custom_format(rotkehlchen_api_server, file_upload):
    """Test that the data import endpoint works successfully for cointracking
    when using custom date formats at the moment of making the import

    To test that data import works both with specifying filepath and uploading
    the file try both ways in this test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    dir_path = Path(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    filepath = dir_path / 'data' / 'cointracking_custom_dates.csv'

    if file_upload:
        files = {'file': open(filepath, 'rb')}
        response = requests.post(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ),
            files=files,
            data={'source': 'cointracking.info', 'timestamp_format': '%d/%m/%Y %H:%M'},
        )
    else:
        json_data = {
            'source': 'cointracking.info',
            'file': str(filepath),
            'timestamp_format': '%d/%m/%Y %H:%M',
        }
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'dataimportresource',
            ), json=json_data,
        )

    result = assert_proper_response_with_result(response)
    assert result is True
    # And also assert data was imported succesfully
    assert_custom_cointracking(rotki)


def test_associated_locations(database):
    """Test that locations imported in different places are correctly stored in database"""
    # Add trades from different locations
    trades = [Trade(
        timestamp=Timestamp(1595833195),
        location=Location.CRYPTOCOM,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1.0')),
        rate=Price(FVal('281.14')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1587825824),
        location=Location.CRYPTOCOM,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596014214),
        location=Location.BLOCKFI,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1565888464),
        location=Location.NEXO,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596014214),
        location=Location.NEXO,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1612051199),
        location=Location.BLOCKFI,
        base_asset=symbol_to_asset_or_token('USDC'),
        quote_asset=symbol_to_asset_or_token('LTC'),
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('6404.6')),
        rate=Price(FVal('151.6283999982779809352223797')),
        fee=None,
        fee_currency=None,
        link='',
        notes='One Time',
    ), Trade(
        timestamp=Timestamp(1595833195),
        location=Location.POLONIEX,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1.0')),
        rate=Price(FVal('281.14')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.00061475')),
        rate=Price(FVal('309.0687271248474989833265555')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.EXTERNAL,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    )]

    # Add multiple entries for same exchange + connected exchange
    database.add_trades(trades)
    kraken_api_key1 = ApiKey('kraken_api_key')
    kraken_api_secret1 = ApiSecret(b'kraken_api_secret')
    kraken_api_key2 = ApiKey('kraken_api_key2')
    kraken_api_secret2 = ApiSecret(b'kraken_api_secret2')
    binance_api_key = ApiKey('binance_api_key')
    binance_api_secret = ApiSecret(b'binance_api_secret')

    # add mock kraken and binance
    database.add_exchange('kraken1', Location.KRAKEN, kraken_api_key1, kraken_api_secret1)
    database.add_exchange('kraken2', Location.KRAKEN, kraken_api_key2, kraken_api_secret2)
    database.add_exchange('binance', Location.BINANCE, binance_api_key, binance_api_secret)

    # Add uniswap and sushiswap events
    database.add_amm_events([
        LiquidityPoolEvent(
            tx_hash='0x47ea26957ce09e84a51b51dfdab6a4ac1c3672a372eef77b15ef7677174ac847',
            log_index=23,
            address=ChecksumEthAddress('0x3163Bb273E8D9960Ce003fD542bF26b4C529f515'),
            timestamp=Timestamp(1590011534),
            event_type=EventType.MINT_SUSHISWAP,
            pool_address=ChecksumEthAddress('0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'),
            token0=EthereumToken('0x514910771AF9Ca656af840dff83E8264EcF986CA'),
            token1=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0=FVal('3.313676003468974932'),
            amount1=FVal('0.064189269269768657'),
            usd_price=FVal('26.94433946158740371839009166230438'),
            lp_amount=FVal('0.460858304063739927'),
        ),
    ])
    database.add_amm_swaps([
        AMMSwap(
            tx_hash='0xa54bf4c68d435e3c8f432fd7e62b7f8aca497a831a3d3fca305a954484ddd7b2',
            log_index=208,
            address=ChecksumEthAddress('0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'),
            from_address=string_to_ethereum_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_ethereum_address('0xC9cB53B48A2f3A9e75982685644c1870F1405CCb'),
            timestamp=Timestamp(1609301469),
            location=Location.UNISWAP,
            token0=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            token1=EthereumToken('0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(FVal('2.6455727132446468')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('1936.810111')),
        ),
    ])
    database.add_balancer_events([
        BalancerEvent(
            tx_hash='0xa54bf4c68d435e3c8f432fd7e62b7f8aca497a831a3d3fca305a954484ddd7b3',
            log_index=23,
            address=ChecksumEthAddress('0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'),
            timestamp=Timestamp(1609301469),
            event_type=BalancerBPTEventType.MINT,
            pool_address_token=EthereumToken('0x514910771AF9Ca656af840dff83E8264EcF986CA'),
            lp_balance=Balance(amount=FVal(2), usd_value=FVal(3)),
            amounts=[
                AssetAmount(FVal(1)),
                AssetAmount(FVal(2)),
            ],
        ),
    ])
    expected_locations = {
        Location.KRAKEN,
        Location.BINANCE,
        Location.BLOCKFI,
        Location.NEXO,
        Location.CRYPTOCOM,
        Location.POLONIEX,
        Location.COINBASE,
        Location.EXTERNAL,
        Location.SUSHISWAP,
        Location.UNISWAP,
        Location.BALANCER,
    }

    assert set(database.get_associated_locations()) == expected_locations
