from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.oracles.constants import (
    A_ARBITRUM_USDC,
    A_BASE_USDC,
    A_BSC_USDT,
    A_OPTIMISM_USDT,
    A_POLYGON_USDC,
)
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import (
    A_1INCH,
    A_BSC_BNB,
    A_BTC,
    A_DOGE,
    A_ETH,
    A_LINK,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_WETH,
)
from rotkehlchen.constants.prices import ZERO_PRICE
from rotkehlchen.errors.defi import DefiPoolError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import CurrentPriceOracle
from rotkehlchen.tests.utils.ethereum import INFURA_ETH_NODE
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ChainID, EvmTokenKind, Price, SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.inquirer import Inquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_asset_to_asset(inquirer_defi, socket_enabled):  # pylint: disable=unused-argument
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
        price = price_instance.query_current_price(A_1INCH, A_LINK)
        assert price != ZERO_PRICE
        assert (inch_price / link_price).is_close(price, max_diff='0.01')
        defi_price = inquirer_defi.find_usd_price(A_LINK, ignore_cache=True)
        assert abs(defi_price - link_price) / link_price < FVal(0.1), f'{defi_price=} and {link_price=} have more than 10% difference'  # noqa: E501

        # test with ethereum tokens but as assets instead of instance of the EvmToken class
        a1inch = Asset(A_1INCH.identifier)
        alink = Asset(A_LINK.identifier)
        price_as_assets = price_instance.query_current_price(a1inch, alink)
        assert price_as_assets.is_close(price, max_diff='0.01')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('ethereum_manager_connect_at_start', [(INFURA_ETH_NODE,)])
def test_uniswap_oracles_historic_price(inquirer_defi, socket_enabled):  # pylint: disable=unused-argument
    """Test that the uniswap oracles return correct historical prices."""
    inquirer_defi.set_oracles_order(oracles=[CurrentPriceOracle.UNISWAPV3])
    assert inquirer_defi._uniswapv3.query_historical_price(
        from_asset=A_1INCH,
        to_asset=A_LINK,
        timestamp=1653454800,
    ) == Price(FVal('0.138028273714701208394300881476926660441297470010798769978393676678931896933043'))  # noqa: E501

    with pytest.raises(NoPriceForGivenTimestamp):
        inquirer_defi._uniswapv3.query_historical_price(
            from_asset=A_WETH,
            to_asset=A_USDC,
            timestamp=1601557200,  # before V3 contract was created
        )

    inquirer_defi.set_oracles_order(oracles=[CurrentPriceOracle.UNISWAPV2])
    assert inquirer_defi._uniswapv2.query_historical_price(
        from_asset=A_WETH,
        to_asset=A_USDC,
        timestamp=1610150400,
    ) == Price(FVal('1218.87080719990345367447708023135690417334776916278271419773639287665690749300'))  # noqa: E501

    with pytest.raises(NoPriceForGivenTimestamp):
        inquirer_defi._uniswapv2.query_historical_price(
            from_asset=A_WETH,
            to_asset=A_USDC,
            timestamp=1571230800,  # before V2 contract was created
        )

    with pytest.raises(PriceQueryUnsupportedAsset):
        inquirer_defi._uniswapv2.query_historical_price(
            from_asset=A_BTC,  # non eth tokens
            to_asset=A_DOGE,
            timestamp=1653454800,
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('base_manager_connect_at_start', [(WeightedNode(node_info=NodeName(name='llama', endpoint='https://base.llamarpc.com', owned=True, blockchain=SupportedBlockchain.BASE), active=True, weight=ONE),)])  # noqa: E501
@pytest.mark.parametrize('polygon_pos_manager_connect_at_start', [(WeightedNode(node_info=NodeName(name='polygon', endpoint='https://polygon.drpc.org', owned=True, blockchain=SupportedBlockchain.POLYGON_POS), active=True, weight=ONE),)])  # noqa: E501
def test_uniswap_oracles_evm(inquirer_defi: 'Inquirer') -> None:
    """Test that Uniswap V2 and V3 oracles return correct prices in evm chains"""
    assert inquirer_defi._uniswapv2 is not None
    assert inquirer_defi._uniswapv3 is not None

    # v2 historical on base
    assert inquirer_defi._uniswapv2.query_historical_price(
        from_asset=A_ETH,
        to_asset=A_BASE_USDC,
        timestamp=Timestamp(1725944400),
    ) == Price(FVal('2340.829327449607'))

    # v2 current on arbitrum
    assert inquirer_defi._uniswapv2.query_current_price(
        from_asset=A_ETH,
        to_asset=A_ARBITRUM_USDC,
    ) == Price(FVal('3212.0656284514484'))

    # v3 historical on polygon
    assert inquirer_defi._uniswapv3.query_historical_price(
        from_asset=A_POLYGON_POS_MATIC,
        to_asset=A_POLYGON_USDC,
        timestamp=Timestamp(1725944400),
    ) == Price(FVal('0.3785896756190174'))

    # v3 current on optimism
    assert inquirer_defi._uniswapv3.query_current_price(
        from_asset=A_ETH,
        to_asset=A_OPTIMISM_USDT,
    ) == Price(FVal('3214.5282531850976'))

    # v3 current on bsc
    assert inquirer_defi._uniswapv3.query_current_price(
        from_asset=A_BSC_USDT,
        to_asset=A_BSC_BNB,
    ) == Price(FVal('0.001433422881060733'))


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_oracles_special_cases(inquirer_defi, socket_enabled):  # pylint: disable=unused-argument
    """
    Test special cases for the uniswap oracles
    """
    # ETH/WETH is handled correctly
    for oracle in (CurrentPriceOracle.UNISWAPV2, CurrentPriceOracle.UNISWAPV3):
        inquirer_defi.set_oracles_order(oracles=[oracle])
        inch_weth = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_WETH)
        inch_eth = inquirer_defi._uniswapv2.query_current_price(A_1INCH, A_ETH)
        assert inch_eth.is_close(inch_weth)
        # Non eth tokens
        with pytest.raises(PriceQueryUnsupportedAsset):
            inquirer_defi._uniswapv2.query_current_price(A_BTC, A_DOGE)
        # Same asset
        assert inquirer_defi._uniswapv2.query_current_price(A_ETH, A_WETH) == Price(ONE)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
def test_uniswap_no_decimals(inquirer_defi: 'Inquirer'):
    """Test that if a token has no information about the number of decimals a proper error
    is raised"""
    asset_resolver = AssetResolver()
    original_getter = asset_resolver.resolve_asset
    original_resolver_to_class = asset_resolver.resolve_asset_to_class
    resolved_weth = A_WETH.resolve_to_evm_token()
    resolved_usdc = A_USDC.resolve_to_evm_token()

    def mocked_asset_getter(identifier, **kwargs):
        if identifier == resolved_weth.identifier:
            return EvmToken.initialize(
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

        if len(kwargs) == 0:
            return original_getter(identifier, **kwargs)
        return original_resolver_to_class(identifier, **kwargs)

    with (
        patch.object(asset_resolver, 'resolve_asset', wraps=mocked_asset_getter),
        patch.object(asset_resolver, 'resolve_asset_to_class', wraps=mocked_asset_getter),
    ):
        weth = EvmToken(A_WETH.identifier)
        assert weth.decimals is None
        assert inquirer_defi._uniswapv2 is not None
        assert inquirer_defi._uniswapv3 is not None
        with pytest.raises(DefiPoolError):
            inquirer_defi._uniswapv2.query_current_price(weth, resolved_usdc)
        with pytest.raises(DefiPoolError):
            inquirer_defi._uniswapv3.query_current_price(weth, resolved_usdc)


@pytest.mark.parametrize('use_clean_caching_directory', [True])
def test_pool_with_no_liquidity(inquirer_defi: 'Inquirer'):
    """
    Test that a pool with no liquidity on range is skipped when using uni-v3 oracle
    """
    old_stream = EvmToken('eip155:1/erc20:0x0Cf0Ee63788A0849fE5297F3407f701E122cC023')

    def mock_requests_get(*args, **kwargs):  # pylint: disable=unused-argument
        response = """{"jsonrpc":"2.0","id":1,"result":"0x0000000000000000000000000000000000000000000000000000000000f2aa4700000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000003000000000000000000000000000000000000000000000000000000000000006000000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000000"}"""  # noqa: E501
        return MockResponse(200, response)

    ethereum_inquirer = inquirer_defi.get_evm_manager(chain_id=ChainID.ETHEREUM).node_inquirer
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
    GlobalDBHandler().add_asset(nft_token)
    ethereum_inquirer = inquirer_defi.get_evm_manager(chain_id=ChainID.ETHEREUM).node_inquirer
    assert ethereum_inquirer is not None
    assert inquirer_defi._uniswapv3 is not None

    with pytest.raises(PriceQueryUnsupportedAsset):
        inquirer_defi._uniswapv3.query_current_price(
            from_asset=nft_token,
            to_asset=A_USDC.resolve_to_evm_token(),
        )
