from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_1INCH, A_BTC, A_DOGE, A_ETH, A_LINK, A_USDC, A_WETH
from rotkehlchen.constants.misc import ONE, ZERO_PRICE
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.price import PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, EvmTokenKind, Price

if TYPE_CHECKING:
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_asset_to_asset(inquirer_defi, socket_enabled):  # pylint: disable=unused-argument  # noqa: E501
    """
    Test that the uniswap oracles return a price close to the one reported by
    coingecko.
    """
    inch_price = inquirer_defi.find_usd_price(A_1INCH)
    link_price = inquirer_defi.find_usd_price(A_LINK)

    for oracle in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3):
        if oracle == CurrentPriceOracle.UNISWAPV2:
            price_instance = inquirer_defi._uniswapv2
        else:
            price_instance = inquirer_defi._uniswapv3
        inquirer_defi.set_oracles_order(oracles=[oracle])
        price, _ = price_instance.query_current_price(A_1INCH, A_LINK, False)
        assert price != ZERO_PRICE
        assert (inch_price / link_price).is_close(price, max_diff='0.01')
        defi_price = inquirer_defi.find_usd_price(A_LINK, ignore_cache=True)
        assert abs(defi_price - link_price) / link_price < FVal(0.1), f'{defi_price=} and {link_price=} have more than 10% difference'  # noqa: E501

        # test with ethereum tokens but as assets instead of instance of the EvmToken class
        a1inch = Asset(A_1INCH.identifier)
        alink = Asset(A_LINK.identifier)
        price_as_assets, _ = price_instance.query_current_price(a1inch, alink, False)
        assert price_as_assets.is_close(price, max_diff='0.01')


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_special_cases(inquirer_defi, socket_enabled):  # pylint: disable=unused-argument  # noqa: E501
    """
    Test special cases for the uniswap oracles
    """
    # ETH/WETH is handled correctly
    for oracle in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3):
        inquirer_defi.set_oracles_order(oracles=[oracle])
        inch_weth, _ = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_WETH, False)
        inch_eth, _ = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_ETH, False)
        assert inch_eth.is_close(inch_weth)
        # Non eth tokens
        with pytest.raises(PriceQueryUnsupportedAsset):
            inquirer_defi._uniswapv2.query_current_price(A_BTC, A_DOGE, False)
        # Same asset
        assert inquirer_defi._uniswapv2.query_current_price(A_ETH, A_WETH, False)[0] == Price(ONE)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_no_decimals(inquirer_defi, socket_enabled):  # pylint: disable=unused-argument
    """Test that if a token has no information about the number of decimals a proper error
    is raised"""
    asset_resolver = AssetResolver()
    original_getter = asset_resolver.resolve_asset

    def fake_weth_token():
        """Make sure that the weth token has no decimals fields and any other token
        is loaded properly
        """
        resolved_weth = A_WETH.resolve_to_evm_token()

        def mocked_asset_getter(identifier):
            if identifier == resolved_weth.identifier:
                fake_weth = EvmToken.initialize(
                    address=resolved_weth.evm_address,
                    chain_id=resolved_weth.chain_id,
                    token_kind=resolved_weth.token_kind,
                    decimals=None,
                    name=resolved_weth.name,
                    symbol=resolved_weth.symbol,
                    started=resolved_weth.started,
                    forked=resolved_weth.forked.identifier if resolved_weth.forked is not None else None,  # noqa: E501
                    swapped_for=resolved_weth.swapped_for.identifier if resolved_weth.swapped_for is not None else None,  # noqa: E501
                    coingecko=resolved_weth.coingecko,
                    cryptocompare=resolved_weth.cryptocompare,
                    protocol=resolved_weth.protocol,
                )
                return fake_weth
            return original_getter(identifier)
        return patch.object(asset_resolver, 'resolve_asset', wraps=mocked_asset_getter)

    with fake_weth_token():
        weth = EvmToken(A_WETH.identifier)
        assert weth.decimals is None
        with pytest.raises(DefiPoolError):
            inquirer_defi._uniswapv2.query_current_price(weth, A_USDC, False)
        with pytest.raises(DefiPoolError):
            inquirer_defi._uniswapv3.query_current_price(weth, A_USDC, False)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_pool_with_no_liquidity(inquirer_defi: 'Inquirer'):
    """
    Test that a pool with no liquidity on range is skipped when using uni-v3 oracle
    """
    old_stream = EvmToken('eip155:1/erc20:0x0Cf0Ee63788A0849fE5297F3407f701E122cC023')

    def mock_requests_get(_url, timeout):  # pylint: disable=unused-argument
        response = """{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f2aa4700000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000003000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000"}"""  # noqa: E501
        return MockResponse(200, response)

    ethereum_inquirer = inquirer_defi.get_ethereum_manager().node_inquirer
    assert ethereum_inquirer is not None
    assert inquirer_defi._uniswapv3 is not None

    etherscan_patch = patch.object(
        target=ethereum_inquirer.etherscan.session,
        attribute='get',
        wraps=mock_requests_get,
    )
    with etherscan_patch:
        path = inquirer_defi._uniswapv3.get_pool(old_stream, A_USDC.resolve_to_evm_token())
    assert path == []


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_invalid_token_kind_price_query(inquirer_defi: 'Inquirer'):
    """
    Test that if we pass something that is not an ERC20 the inquirer raises an error
    """
    nft_token = EvmToken.initialize(
        address=string_to_evm_address('0xC36442b4a4522E871399CD717aBDD847Ab11FE88'),
        chain_id=ChainID.ETHEREUM,
        name='Uniswap V3: Positions NFT',
        symbol='UNI-V3-POS',
        decimals=18,
        token_kind=EvmTokenKind.ERC721,
    )
    GlobalDBHandler().add_asset(
        asset_id=nft_token.identifier,
        asset_type=AssetType.EVM_TOKEN,
        data=nft_token,
    )
    ethereum_inquirer = inquirer_defi.get_ethereum_manager().node_inquirer
    assert ethereum_inquirer is not None
    assert inquirer_defi._uniswapv3 is not None

    with pytest.raises(PriceQueryUnsupportedAsset):
        inquirer_defi._uniswapv3.query_current_price(
            from_asset=nft_token,
            to_asset=A_USDC.resolve_to_evm_token(),
            match_main_currency=False,
        )
