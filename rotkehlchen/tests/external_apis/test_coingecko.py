from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

import gevent
import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.assets import A_BTC, A_DAI, A_ETH, A_EUR, A_YFI
from rotkehlchen.errors.asset import UnsupportedAsset
from rotkehlchen.externalapis.coingecko import Coingecko, CoingeckoAssetData
from rotkehlchen.fval import FVal
from rotkehlchen.icons import IconManager
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Price


@pytest.fixture(name='icon_manager')
def fixture_icon_manager(data_dir, greenlet_manager):
    return IconManager(data_dir=data_dir, coingecko=Coingecko(), greenlet_manager=greenlet_manager)


def assert_coin_data_same(given, expected, compare_description=False):
    if compare_description:
        assert given == expected

    # else
    assert given.identifier == expected.identifier
    assert given.symbol == expected.symbol
    assert given.name == expected.name
    assert given.image_url == expected.image_url


def test_asset_data(session_coingecko):
    expected_data = CoingeckoAssetData(
        identifier='bitcoin',
        symbol='btc',
        name='Bitcoin',
        image_url='https://assets.coingecko.com/coins/images/1/small/bitcoin.png?1696501400',
    )
    data = session_coingecko.asset_data(A_BTC.resolve_to_asset_with_oracles().to_coingecko())
    assert_coin_data_same(data, expected_data)

    expected_data = CoingeckoAssetData(
        identifier='yearn-finance',
        symbol='yfi',
        name='yearn.finance',
        image_url='https://assets.coingecko.com/coins/images/11849/small/yearn.jpg?1696511720',  # noqa: E501
    )
    data = session_coingecko.asset_data(A_YFI.resolve_to_asset_with_oracles().to_coingecko())
    assert_coin_data_same(data, expected_data, compare_description=False)

    with pytest.raises(UnsupportedAsset):
        session_coingecko.asset_data(EvmToken('eip155:1/erc20:0x1844b21593262668B7248d0f57a220CaaBA46ab9').to_coingecko())  # PRL, a token without coingecko page  # noqa: E501


def test_coingecko_historical_price(session_coingecko):
    price = session_coingecko.query_historical_price(
        from_asset=A_ETH,
        to_asset=A_EUR,
        timestamp=1483056100,
    )
    assert price == Price(FVal('7.7478028375650725'))


def test_assets_with_icons(icon_manager):
    """Checks that _assets_with_coingecko_id returns a proper result"""
    x = icon_manager._assets_with_coingecko_id()
    assert len(x) > 1000


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_asset_icons_for_collections(icon_manager: IconManager) -> None:
    """
    Test that for assets in the same collection only one file is saved and
    is later used by all the assets in the same collection
    """
    dai_op = Asset('eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1').resolve()
    dai_main = A_DAI.resolve()
    eth = A_ETH.resolve()
    times_api_was_queried = 0

    # make sure that the icon asset doesn't exist
    icon_path = icon_manager.iconfile_path(dai_main)
    assert icon_path.exists() is False

    # mock coingecko response
    def mock_coingecko(url, timeout):  # pylint: disable=unused-argument
        nonlocal times_api_was_queried
        times_api_was_queried += 1
        test_data_folder = Path(__file__).resolve().parent.parent / 'data' / 'mocks' / 'test_coingecko'  # noqa: E501
        if 'https://api.coingecko.com/api/v3/coins/dai' in url:
            with open(test_data_folder / 'coins' / 'dai.json') as f:
                return MockResponse(HTTPStatus.OK, f.read())
        elif 'https://api.coingecko.com/api/v3/coins/ethereum' in url:
            with open(test_data_folder / 'coins' / 'ethereum.json') as f:
                return MockResponse(HTTPStatus.OK, f.read())
        elif url in {
            'https://assets.coingecko.com/coins/images/9956/small/4943.png?1636636734',
            'https://assets.coingecko.com/coins/images/279/small/ethereum.png?1595348880',
        }:
            icon_name = '4943.png'
            if '279' in url:
                icon_name = '279.png'
            with open(test_data_folder / 'icons' / icon_name, 'rb') as f:
                return MockResponse(
                    status_code=HTTPStatus.OK,
                    text=str(f.read()),
                    headers={'Content-Type': 'image/png'},
                )

        raise AssertionError(f'Unexpected url {url} in asset collection icons test')

    with patch.object(icon_manager.coingecko.session, 'get', wraps=mock_coingecko):
        icon_dai_op, processed = icon_manager.get_icon(dai_op)
        gevent.joinall(icon_manager.greenlet_manager.greenlets)

    # check that the asset was correctly created
    assert icon_dai_op is None
    assert processed is True
    assert icon_path.exists() is True
    assert times_api_was_queried == 2

    # Try to get the icon for an asset in the same collection
    with patch.object(icon_manager.coingecko.session, 'get', wraps=mock_coingecko):
        icon_dai_eth, processed = icon_manager.get_icon(dai_main)
        gevent.joinall(icon_manager.greenlet_manager.greenlets)

    # check that the api was not queried again and the fail returned is the same
    assert processed is False
    assert times_api_was_queried == 2
    assert icon_path == icon_dai_eth

    # try to get an asset without collection
    with patch.object(icon_manager.coingecko.session, 'get', wraps=mock_coingecko):
        icon_manager.get_icon(eth)
        gevent.joinall(icon_manager.greenlet_manager.greenlets)

    assert icon_manager.iconfile_path(eth).exists()
    assert times_api_was_queried == 4
