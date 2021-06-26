import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.manager import NodeName
from rotkehlchen.chain.ethereum.modules.uniswap import UniswapPoolEvent, UniswapPoolEventsBalance
from rotkehlchen.chain.ethereum.modules.uniswap.typing import UNISWAP_EVENTS_PREFIX, EventType
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.assets import A_ADAI_V1, A_DAI, A_LEND, A_USDC, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.aave import AAVE_TEST_ACC_1
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_DOLLAR_BASED, A_YAM_V1
from rotkehlchen.tests.utils.ethereum import INFURA_TEST
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp, TradeType

# Addresses
# DAI/WETH pool: 0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11
# From that pool find a holder and test
LP_HOLDER_ADDRESS = string_to_ethereum_address('0xc4d15CbE36BE26596fA676Ff1B21421541d7e8e6')
# Uniswap Factory contract
TEST_ADDRESS_FACTORY_CONTRACT = (
    string_to_ethereum_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
)


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='uniswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


UNISWAP_TEST_OPTIONS = [
    # Test with infura (as own node), many open nodes, and premium + graph
    (False, INFURA_TEST, (NodeName.OWN, NodeName.MYCRYPTO)),
    (False, '', (NodeName.MYCRYPTO, NodeName.BLOCKSCOUT, NodeName.AVADO_POOL)),
    (True, '', ()),
]
# Skipped infura and many open nodes for now in the CI. Fails flakily due to timeouts
# from time to time. We should run locally to make sure that it still works.
SKIPPED_UNISWAP_TEST_OPTIONS = [UNISWAP_TEST_OPTIONS[-1]]


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize(
    'start_with_valid_premium,ethrpc_endpoint,ethereum_manager_connect_at_start',
    SKIPPED_UNISWAP_TEST_OPTIONS,
)
def test_get_balances(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,
        start_with_valid_premium,
):
    """Check querying the uniswap balances endpoint works. Uses real data

    Checks the functionality both for the graph queries (when premium) and simple
    onchain queries (without premium)

    THIS IS SUPER FREAKING SLOW. BE WARNED.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    # Set module premium attribute
    uniswap = rotki.chain_manager.get_module('uniswap')
    uniswap.premium = premium

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
        json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(
            server=rotkehlchen_api_server,
            task_id=task_id,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 10,
        )
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    if LP_HOLDER_ADDRESS not in result or len(result[LP_HOLDER_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {LP_HOLDER_ADDRESS} has no uniswap balances'),
        )
        return

    address_balances = result[LP_HOLDER_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['assets']) == 2
        if start_with_valid_premium:
            assert lp['total_supply'] is not None
        else:
            assert lp['total_supply'] is None
        assert lp['user_balance']['amount']
        assert lp['user_balance']['usd_value']

        # LiquidityPoolAsset attributes
        for lp_asset in lp['assets']:
            lp_asset_type = type(lp_asset['asset'])

            assert lp_asset_type in (str, dict)

            # Unknown asset, at least contains token address
            if lp_asset_type is dict:
                assert lp_asset['asset']['ethereum_address'].startswith('0x')
            # Known asset, contains identifier
            else:
                assert not lp_asset['asset'].startswith('0x')

            if start_with_valid_premium:
                assert lp_asset['total_amount'] is not None
            else:
                assert lp_asset['total_amount'] is None
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']


def get_expected_trades():
    """Function so no price (unknown) assets can be resolved only when existing in the DB"""
    return [AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_WETH,
        quote_asset=A_YAM_V1,
        amount=AssetAmount(FVal('1.170318698476688004')),
        rate=Price(FVal('10.74584229464304934592083644')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x3a9013edd5d7554699c9edcb316d4658dbf673e1940061b6f9c95f91a2c2d0a9',
            log_index=113,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            timestamp=Timestamp(1597186835),
            location=Location.UNISWAP,
            token0=A_YAM_V1,
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('12.5760601683024')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('1.170318698476688004')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_WETH,
        quote_asset=A_YAM_V1,
        amount=AssetAmount(FVal('0.408291837660462176')),
        rate=Price(FVal('7.312663563501178473215709887')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x7293791b92306c2081432438fbf666c917577e373ba178d4232dbebc18875a78',
            log_index=54,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            timestamp=Timestamp(1597183725),
            location=Location.UNISWAP,
            token0=A_YAM_V1,
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('2.9857008445346')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('0.408291837660462176')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_WETH,
        quote_asset=A_YAM_V1,
        amount=AssetAmount(FVal('1.396503415128306884')),
        rate=Price(FVal('8.652682034981347560720977038')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x7e254511474ee9cb2ea033ebb6743845c3d44d9f31165e7f69aa6bfd768192d0',
            log_index=7,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            timestamp=Timestamp(1597182868),
            location=Location.UNISWAP,
            token0=A_YAM_V1,
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('12.0835000118708')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('1.396503415128306884')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_DAI,
        quote_asset=EthereumToken('0xC0134b5B924c2FCA106eFB33C45446c466FBe03e'),  # ALEPH
        amount=AssetAmount(FVal('3801.255053678779873244')),
        rate=Price(FVal('4.367565528950839496292511829')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0xe1ab3767684e9ae1859e78fc8dea00927b078be238b51426a5a01acbc3eabfa1',
            log_index=102,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1595787897),
            location=Location.UNISWAP,
            token0=EthereumToken('0xC0134b5B924c2FCA106eFB33C45446c466FBe03e'),  # ALEPH
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('16602.230539197612')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('16.759630910942965985')),
        ), AMMSwap(
            tx_hash='0xe1ab3767684e9ae1859e78fc8dea00927b078be238b51426a5a01acbc3eabfa1',
            log_index=108,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1595787897),
            location=Location.UNISWAP,
            token0=A_DAI,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('12.569723183207224488')),
            amount0_out=AssetAmount(FVal('3801.255053678779873244')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_LEND,
        quote_asset=A_WETH,
        amount=AssetAmount(FVal('783.815545775206396604')),
        rate=Price(FVal('0.001336937475067974904054378106')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x7070ac300cfe44f2791bb53a272eddb6c04cf5b2a34c7b30f223034bf0fbc9f5',
            log_index=88,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1595252547),
            location=Location.UNISWAP,
            token0=A_LEND,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('1.047912376687731144')),
            amount0_out=AssetAmount(FVal('783.815545775206396604')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_LEND,
        quote_asset=A_WETH,
        amount=AssetAmount(FVal('3818.889005228581791673')),
        rate=Price(FVal('0.001121122145540436399587918681')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x28f73d8691b0b448d3cf49292aafeccb0574d0ca25706e4998e37275eaf568c2',
            log_index=109,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1594917107),
            location=Location.UNISWAP,
            token0=A_DAI,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('4.281441035122650458')),
            amount0_out=AssetAmount(FVal('980.087534272890506353')),
            amount1_out=AssetAmount(ZERO),
        ), AMMSwap(
            tx_hash='0x28f73d8691b0b448d3cf49292aafeccb0574d0ca25706e4998e37275eaf568c2',
            log_index=113,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1594917107),
            location=Location.UNISWAP,
            token0=A_DAI,
            token1=A_LEND,
            amount0_in=AssetAmount(FVal('980.087534272890506353')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('3811.261176919173284002')),
        ), AMMSwap(
            tx_hash='0x28f73d8691b0b448d3cf49292aafeccb0574d0ca25706e4998e37275eaf568c2',
            log_index=118,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1594917107),
            location=Location.UNISWAP,
            token0=A_USDC,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('4.281441035122650458')),
            amount0_out=AssetAmount(FVal('998.970468')),
            amount1_out=AssetAmount(ZERO),
        ), AMMSwap(
            tx_hash='0x28f73d8691b0b448d3cf49292aafeccb0574d0ca25706e4998e37275eaf568c2',
            log_index=122,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            to_address=string_to_ethereum_address('0x9021C84f3900B610ab8625d26d739e3B7bFf86aB'),
            timestamp=Timestamp(1594917107),
            location=Location.UNISWAP,
            token0=A_LEND,
            token1=A_USDC,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('998.970468')),
            amount0_out=AssetAmount(FVal('3818.889005228581791673')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_LEND,
        quote_asset=A_WETH,
        amount=AssetAmount(FVal('21928.266845570798012768')),
        rate=Price(FVal('0.0005748315837851012488579182153')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0xefaf420db6bc00e007724c9f109cc2513886bf572cec52ce5c4fc4ea0c6691d6',
            log_index=108,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x9Ca13029232C8f4AAC1D42FaA54A36aDE41aA10d'),
            to_address=string_to_ethereum_address('0x9Ca13029232C8f4AAC1D42FaA54A36aDE41aA10d'),
            timestamp=Timestamp(1592944381),
            location=Location.UNISWAP,
            token0=A_LEND,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('12.605060360501788046')),
            amount0_out=AssetAmount(FVal('21928.266845570798012768')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_WETH,
        quote_asset=A_DAI,
        amount=AssetAmount(FVal('4.136051879013406343')),
        rate=Price(FVal('232.4798219165320015500724464')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x983676d8ff7568f2502d73cdca96150be26dd033da86c4e05ea3a2c4ecb66182',
            log_index=43,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0x09e3B36DbDc641d73c38656605538C4B666dB82B'),
            to_address=string_to_ethereum_address('0x09e3B36DbDc641d73c38656605538C4B666dB82B'),
            timestamp=Timestamp(1592398831),
            location=Location.UNISWAP,
            token0=A_DAI,
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('961.548604270574270408')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('4.136051879013406343')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_LEND,
        quote_asset=A_DAI,
        amount=AssetAmount(FVal('2340.535105624007589249')),
        rate=Price(FVal('0.09658784621963269841181632766')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0xb41eeed3fde0b6376bba43523d1f8e18127587ffa269b343b7155805bda27270',
            log_index=124,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0xc3037b2A1a9E9268025FF6d45Fe7095436446D52'),
            to_address=string_to_ethereum_address('0xc3037b2A1a9E9268025FF6d45Fe7095436446D52'),
            timestamp=Timestamp(1592090465),
            location=Location.UNISWAP,
            token0=A_DAI,
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('226.067244853663419909')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('0.947308435652157362')),
        ), AMMSwap(
            tx_hash='0xb41eeed3fde0b6376bba43523d1f8e18127587ffa269b343b7155805bda27270',
            log_index=128,
            address=string_to_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
            from_address=string_to_ethereum_address('0xc3037b2A1a9E9268025FF6d45Fe7095436446D52'),
            to_address=string_to_ethereum_address('0xc3037b2A1a9E9268025FF6d45Fe7095436446D52'),
            timestamp=Timestamp(1592090465),
            location=Location.UNISWAP,
            token0=A_LEND,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('0.947308435652157362')),
            amount0_out=AssetAmount(FVal('2340.535105624007589249')),
            amount1_out=AssetAmount(ZERO),
        )],
    )]


def _query_and_assert_simple_uniswap_trades(setup, api_server, async_query):
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            'uniswaptradeshistoryresource',
        ), json={'async_query': async_query, 'to_timestamp': 1597186900})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    expected_trades = get_expected_trades()
    for idx, trade in enumerate(result[AAVE_TEST_ACC_1]):
        if idx == len(expected_trades):
            break  # test up to last expected_trades trades from 1597186900
        assert trade == expected_trades[idx].serialize()


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_1]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_uniswap_trades_history(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test that the last 11/23 uniswap trades of the account since 1605437542
    are parsed and returned correctly

    Also test that data are written in the DB and properly retrieved afterwards
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    _query_and_assert_simple_uniswap_trades(setup, rotkehlchen_api_server, async_query)
    # make sure data are written in the DB
    db_trades = rotki.data.db.get_amm_swaps()
    assert len(db_trades) == 14
    # Query a 2nd time to make sure that when retrieving from the database everything works fine
    _query_and_assert_simple_uniswap_trades(setup, rotkehlchen_api_server, async_query)


CRAZY_UNISWAP_ADDRESS = string_to_ethereum_address('0xc61288821b4722Ce29249F0BA03b633F0bE46a5A')
CRAZY_UNISWAP_ADDRESS2 = string_to_ethereum_address('0x4cB251099BaE191d0faE838CC5ac85C67FE6D419')


def get_expected_crazy_trades():
    """Function so no price (unknown) assets can be resolved only when existing in the DB"""
    A_MOONYIELD = EthereumToken('0xc2C11C4F315a99976AD8A6Ff2b46D8bf69FC8177')  # noqa: N806
    A_PENGUIN_PARTY = EthereumToken('0x30BCd71b8d21FE830e493b30e90befbA29de9114')  # noqa: N806
    A_FMK = EthereumToken('0x86B0Aa51eB489585D88d2e671E5ee1b9e457Be60')  # noqa: N806
    return [AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_MOONYIELD,
        quote_asset=A_WETH,
        amount=AssetAmount(FVal('15.4')),
        rate=Price(FVal('0.007309082368793852662337662338')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0xe4a6a3759abeba7fe5d79bd77955b3ce6545f593efb445137b2eb29d3b685a55',
            log_index=217,
            address=CRAZY_UNISWAP_ADDRESS,
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=CRAZY_UNISWAP_ADDRESS,
            timestamp=Timestamp(1605423297),
            location=Location.UNISWAP,
            token0=A_WETH,
            token1=A_MOONYIELD,
            amount0_in=AssetAmount(FVal('0.112559868479425331')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('15.4')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_PENGUIN_PARTY,
        quote_asset=A_FMK,
        amount=AssetAmount(FVal('5.311132913120564692')),
        rate=Price(FVal('0.2482572293550899816477686816')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f',
            log_index=20,
            address=CRAZY_UNISWAP_ADDRESS,
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=string_to_ethereum_address('0xB1637bE0173330664adecB343faF112Ca837dA06'),
            timestamp=Timestamp(1605420918),
            location=Location.UNISWAP,
            token0=A_FMK,
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('1.318527141747939222')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('0.023505635029170072')),
        ), AMMSwap(
            tx_hash='0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f',
            log_index=143,
            address=CRAZY_UNISWAP_ADDRESS,
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=CRAZY_UNISWAP_ADDRESS,
            timestamp=Timestamp(1605420918),
            location=Location.UNISWAP,
            token0=A_PENGUIN_PARTY,
            token1=A_WETH,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('0.023505635029170072')),
            amount0_out=AssetAmount(FVal('5.311132913120564692')),
            amount1_out=AssetAmount(ZERO),
        )],
    )]


def get_bothin_trades():
    """
    Should be trade index 41 in the returned array
    This is a multi token trade. At log index 166 both amount0In and amount1In are
    positive. Test that we handle it in some way. Still not 100% sure this is the right way
    https://etherscan.io/tx/0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017
    """
    return [AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_WETH,
        quote_asset=A_WETH,
        amount=AssetAmount(FVal('0.106591333983182783')),
        rate=Price(FVal('1.744688945746953393022811238')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
            log_index=166,
            address=CRAZY_UNISWAP_ADDRESS2,
            from_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            to_address=string_to_ethereum_address('0x5aBC567A74983Dff7f0185731e5043F77CDEEbd4'),
            timestamp=Timestamp(1604657395),
            location=Location.UNISWAP,
            token0=A_WETH,
            token1=A_ADAI_V1,
            amount0_in=AssetAmount(FVal('0.185968722112880576')),
            amount1_in=AssetAmount(FVal('0.150214308402939121')),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('77.422341021064126448')),
        ), AMMSwap(
            tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
            log_index=169,
            address=CRAZY_UNISWAP_ADDRESS2,
            from_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            to_address=string_to_ethereum_address('0xB1637bE0173330664adecB343faF112Ca837dA06'),
            timestamp=Timestamp(1604657395),
            location=Location.UNISWAP,
            token0=EthereumToken('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # Penguin Party
            token1=A_ADAI_V1,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('77.451074341665209573')),
            amount0_out=AssetAmount(FVal('105.454952420015590185')),
            amount1_out=AssetAmount(ZERO),
        ), AMMSwap(
            tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
            log_index=172,
            address=CRAZY_UNISWAP_ADDRESS2,
            from_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            to_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            timestamp=Timestamp(1604657395),
            location=Location.UNISWAP,
            token0=EthereumToken('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # Penguin Party
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('105.454952420015590185')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('0.213182667966365566')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=A_WETH,
        quote_asset=A_ADAI_V1,
        amount=AssetAmount(FVal('0.106591333983182783')),
        rate=Price(FVal('1.409254418625053124546000710')),
        trade_index=1,
        swaps=[AMMSwap(
            tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
            log_index=166,
            address=CRAZY_UNISWAP_ADDRESS2,
            from_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            to_address=string_to_ethereum_address('0x5aBC567A74983Dff7f0185731e5043F77CDEEbd4'),
            timestamp=Timestamp(1604657395),
            location=Location.UNISWAP,
            token0=A_WETH,
            token1=A_ADAI_V1,
            amount0_in=AssetAmount(FVal('0.185968722112880576')),
            amount1_in=AssetAmount(FVal('0.150214308402939121')),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('77.422341021064126448')),
        ), AMMSwap(
            tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
            log_index=169,
            address=CRAZY_UNISWAP_ADDRESS,
            from_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            to_address=string_to_ethereum_address('0xB1637bE0173330664adecB343faF112Ca837dA06'),
            timestamp=Timestamp(1604657395),
            location=Location.UNISWAP,
            token0=EthereumToken('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # Penguin Party
            token1=A_ADAI_V1,
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('77.451074341665209573')),
            amount0_out=AssetAmount(FVal('105.454952420015590185')),
            amount1_out=AssetAmount(ZERO),
        ), AMMSwap(
            tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
            log_index=172,
            address=CRAZY_UNISWAP_ADDRESS,
            from_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            to_address=string_to_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
            timestamp=Timestamp(1604657395),
            location=Location.UNISWAP,
            token0=EthereumToken('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # Penguin Party
            token1=A_WETH,
            amount0_in=AssetAmount(FVal('105.454952420015590185')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('0.213182667966365566')),
        )],
    )]


@pytest.mark.parametrize('ethereum_accounts', [[CRAZY_UNISWAP_ADDRESS, CRAZY_UNISWAP_ADDRESS2]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_uniswap_exotic_history(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test a uniswap trading address with exotic token swaps (unicode symbol names)"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003', '23322222222'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            'uniswaptradeshistoryresource',
        ), json={'async_query': async_query, 'to_timestamp': 1605437542})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    expected_crazy_trades = get_expected_crazy_trades()
    for idx, trade in enumerate(result[CRAZY_UNISWAP_ADDRESS]):
        if idx == len(expected_crazy_trades) - 1:
            break  # test up to last expected_crazy_trades trades from 1605437542
        assert trade == expected_crazy_trades[idx].serialize()

    found_idx = -1
    for idx, trade in enumerate(result[CRAZY_UNISWAP_ADDRESS2]):
        if trade['tx_hash'] == '0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017':  # noqa: E501
            found_idx = idx
            break
    assert found_idx != -1, 'Could not find the transaction hash index'

    # Also test for the swaps that have both tokens at amountIn or amountOut
    both_in_trades = get_bothin_trades()
    for idx, trade in enumerate(both_in_trades):
        assert trade.serialize() == result[CRAZY_UNISWAP_ADDRESS2][found_idx + idx]

    # Make sure they end up in the DB
    assert len(rotki.data.db.get_amm_swaps()) != 0
    # test uniswap data purging from the db works
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'namedethereummoduledataresource',
        module_name='uniswap',
    ))
    assert_simple_ok_response(response)
    assert len(rotki.data.db.get_amm_swaps()) == 0


# Get events history tests

TEST_EVENTS_ADDRESS_1 = '0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F'
EXPECTED_EVENTS_BALANCES_1 = [
    UniswapPoolEventsBalance(
        address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
        pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),
        token0=A_DOLLAR_BASED,
        token1=A_WETH,
        events=[
            UniswapPoolEvent(
                tx_hash='0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824',
                log_index=263,
                address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1604273256),
                event_type=EventType.MINT,
                pool_address=string_to_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
                token0=A_DOLLAR_BASED,
                token1=A_WETH,
                amount0=AssetAmount(FVal('605.773209925184996494')),
                amount1=AssetAmount(FVal('1.106631443395672732')),
                usd_price=Price(FVal('872.4689300619698095220125311431804')),
                lp_amount=AssetAmount(FVal('1.220680531244355402')),
            ),
            UniswapPoolEvent(
                tx_hash='0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa',
                log_index=66,
                address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1604283808),
                event_type=EventType.BURN,
                pool_address=string_to_ethereum_address('0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89'),  # noqa: E501
                token0=A_DOLLAR_BASED,
                token1=A_WETH,
                amount0=AssetAmount(FVal('641.26289347330654345')),
                amount1=AssetAmount(FVal('1.046665027131675546')),
                usd_price=Price(FVal('837.2737746532695970921908229899852')),
                lp_amount=AssetAmount(FVal('1.220680531244355402')),
            ),
        ],
        profit_loss0=AssetAmount(FVal('35.489683548121546956')),
        profit_loss1=AssetAmount(FVal('-0.059966416263997186')),
        usd_profit_loss=Price(FVal('-35.19515540870021242982170811')),
    ),
]


def get_expected_events_balances_2():
    """Function so no price (unknown) assets can be resolved only when existing in the DB"""
    A_DICE = EthereumToken('0xCF67CEd76E8356366291246A9222169F4dBdBe64')  # noqa: N806
    return [
        # Response index 0
        UniswapPoolEventsBalance(
            address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
            pool_address=string_to_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),
            token0=A_WETH,
            token1=A_DICE,
            events=[
                UniswapPoolEvent(
                    tx_hash='0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4',
                    log_index=99,
                    address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1598270334),
                    event_type=EventType.MINT,
                    pool_address=string_to_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
                    token0=A_WETH,
                    token1=A_DICE,
                    amount0=AssetAmount(FVal('1.580431277572006656')),
                    amount1=AssetAmount(FVal('3')),
                    usd_price=Price(FVal('1281.249386421513581165086356450817')),
                    lp_amount=AssetAmount(FVal('2.074549918528068811')),
                ),
                UniswapPoolEvent(
                    tx_hash='0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa',
                    log_index=208,
                    address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1599000975),
                    event_type=EventType.BURN,
                    pool_address=string_to_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
                    token0=A_WETH,
                    token1=A_DICE,
                    amount0=AssetAmount(FVal('0.970300671842796406')),
                    amount1=AssetAmount(FVal('4.971799615456732408')),
                    usd_price=Price(FVal('928.8590296681781753390482605315881')),
                    lp_amount=AssetAmount(FVal('2.074549918528068811')),
                ),
            ],
            profit_loss0=AssetAmount(FVal('-0.610130605729210250')),
            profit_loss1=AssetAmount(FVal('1.971799615456732408')),
            usd_profit_loss=Price(FVal('-352.3903567533354058260380955')),
        ),
        # Response index 3
        UniswapPoolEventsBalance(
            address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
            pool_address=string_to_ethereum_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
            token0=EthereumToken('0x26E43759551333e57F073bb0772F50329A957b30'),  # DGVC
            token1=A_WETH,
            events=[
                UniswapPoolEvent(
                    tx_hash='0xc612f05bf9f3d814ffbe3649feacbf5bda213297bf7af53a56956814652fe9cc',
                    log_index=171,
                    address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1598391968),
                    event_type=EventType.MINT,
                    pool_address=string_to_ethereum_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
                    token0=EthereumToken('0x26E43759551333e57F073bb0772F50329A957b30'),  # DGVC
                    token1=A_WETH,
                    amount0=AssetAmount(FVal('322.230285353834005677')),
                    amount1=AssetAmount(FVal('1.247571217823345601')),
                    usd_price=Price(FVal('945.2160925652988117900888961551871')),
                    lp_amount=AssetAmount(FVal('18.297385821424685079')),
                ),
                UniswapPoolEvent(
                    tx_hash='0x597f8790a3b9353114b364777c9d32373930e5ad6b8c8f97a58cd2dd58f12b89',
                    log_index=201,
                    address=string_to_ethereum_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1598607431),
                    event_type=EventType.BURN,
                    pool_address=string_to_ethereum_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
                    token0=EthereumToken('0x26E43759551333e57F073bb0772F50329A957b30'),  # DGVC
                    token1=A_WETH,
                    amount0=AssetAmount(FVal('224.7799861151427733')),
                    amount1=AssetAmount(FVal('1.854907037058682998')),
                    usd_price=Price(FVal('1443.169924855633931959022716230101')),
                    lp_amount=AssetAmount(FVal('18.297385821424685079')),
                ),
            ],
            profit_loss0=AssetAmount(FVal('-97.450299238691232377')),
            profit_loss1=AssetAmount(FVal('0.607335819235337397')),
            usd_profit_loss=Price(FVal('497.9538322903351201689338200')),
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [[TEST_EVENTS_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_filtering_by_timestamp_case1(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test the events balances from 1604273256 to 1604283808 (both included).

    LPs involved by the address within this time range: 1, $BASED-WETH

    By calling the endpoint with a specific time range:
      - Not all the events are queried.
      - The events balances do not factorise the current balances in the
      protocol (meaning the response amounts should be assertable).
    """
    # Call time range
    from_timestamp = 1604273256
    to_timestamp = 1604283808

    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    # Force insert address' last used query range, for avoiding query all
    rotki.data.db.update_used_query_range(
        name=f'{UNISWAP_EVENTS_PREFIX}_{TEST_EVENTS_ADDRESS_1}',
        start_ts=Timestamp(0),
        end_ts=from_timestamp,
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'uniswapeventshistoryresource',
            ),
            json={
                'async_query': async_query,
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    events_balances = result[TEST_EVENTS_ADDRESS_1]

    assert len(events_balances) == 1
    assert EXPECTED_EVENTS_BALANCES_1[0].serialize() == events_balances[0]

    # Make sure they end up in the DB
    assert len(rotki.data.db.get_uniswap_events()) != 0
    # test uniswap data purging from the db works
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'namedethereummoduledataresource',
        module_name='uniswap',
    ))
    assert_simple_ok_response(response)
    assert len(rotki.data.db.get_uniswap_events()) == 0


@pytest.mark.parametrize('ethereum_accounts', [[TEST_EVENTS_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_filtering_by_timestamp_case2(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test the events balances from 1598270334 to 1599000975 (both included).

    LPs involved by the address within this time range: 4, only 2 tested.
      - 0: WETH-DICE (tested)
      - 1: DAI-ZOMBIE
      - 2: SHRIMP-WETH
      - 3: DGVC-WETH (tested)

    By calling the endpoint with a specific time range:
      - Not all the events are queried.
      - The events balances do not factorise the current balances in the
      protocol (meaning the response amounts should be assertable).
    """
    # Call time range
    from_timestamp = 1598270334
    to_timestamp = 1599000975

    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    # Force insert address' last used query range, for avoiding query all
    rotki.data.db.update_used_query_range(
        name=f'{UNISWAP_EVENTS_PREFIX}_{TEST_EVENTS_ADDRESS_1}',
        start_ts=Timestamp(0),
        end_ts=from_timestamp,
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'uniswapeventshistoryresource',
            ),
            json={
                'async_query': async_query,
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp,
            },
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    events_balances = result[TEST_EVENTS_ADDRESS_1]

    assert len(events_balances) == 4
    expected_events_balances_2 = get_expected_events_balances_2()
    assert expected_events_balances_2[0].serialize() == events_balances[0]
    assert expected_events_balances_2[1].serialize() == events_balances[3]

    # Make sure they end up in the DB
    assert len(rotki.data.db.get_uniswap_events()) != 0
    # test all data purging from the db works and also deletes uniswap data
    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'ethereummoduledataresource',
    ))
    assert_simple_ok_response(response)
    assert len(rotki.data.db.get_uniswap_events()) == 0


PNL_TEST_ACC = '0x1F9fbD2F6a8754Cd56D4F56ED35338A63C5Bfd1f'


@pytest.mark.parametrize('ethereum_accounts', [[PNL_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_events_pnl(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test the uniswap events history profit and loss calculation"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Set module premium is required for calling `get_balances()`
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    uniswap = rotki.chain_manager.get_module('uniswap')
    uniswap.premium = premium

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    json_data = {
        'async_query': async_query,
        'from_timestamp': 0,
        'to_timestamp': 1609282296,  # time until which pnl was checked
    }
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'uniswapeventshistoryresource'),
            json=json_data,
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    events_balances = result[PNL_TEST_ACC]
    assert len(events_balances) == 3
    # Assert some event details
    assert events_balances[0]['events'][0]['amount0'] == '42.247740079122297434'
    assert events_balances[0]['events'][0]['amount1'] == '0.453409755976350622'
    assert events_balances[0]['events'][0]['event_type'] == 'mint'
    assert events_balances[0]['events'][1]['amount0'] == '64.052160560025177012'
    assert events_balances[0]['events'][1]['amount1'] == '0.455952395125600548'
    assert events_balances[0]['events'][1]['event_type'] == 'burn'
    # Most importantly assert the profit loss
    assert FVal(events_balances[0]['profit_loss0']) >= FVal('21.8')
    assert FVal(events_balances[0]['profit_loss1']) >= FVal('0.00254')
    assert FVal(events_balances[1]['profit_loss0']) >= FVal('-0.0013')
    assert FVal(events_balances[1]['profit_loss1']) >= FVal('0.054')
    assert FVal(events_balances[2]['profit_loss0']) >= FVal('50.684')
    assert FVal(events_balances[2]['profit_loss1']) >= FVal('-0.04')


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_FACTORY_CONTRACT]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_get_all_events_empty(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,  # pylint: disable=unused-argument
        start_with_valid_premium,  # pylint: disable=unused-argument
):
    """Test get all the events balances for an address without events.
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    # Set module premium is required for calling `get_balances()`
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    uniswap = rotki.chain_manager.get_module('uniswap')
    uniswap.premium = premium

    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'uniswapeventshistoryresource'),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert result == {}


@pytest.mark.parametrize('ethereum_accounts', [["0x3ba6eb0e4327b96ade6d4f3b578724208a590cef"]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_uniswap_trades_history_v3(rotkehlchen_api_server):
    """Test that the last 11/23 uniswap trades of the account since 1605437542
    are parsed and returned correctly

    Also test that data are written in the DB and properly retrieved afterwards
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    trades = rotki.chain_manager.get_module('uniswap').get_trades_history(
        addresses=['0x000e62ea8bf5f69e1e32920600839f56313c490f'],
        reset_db_data=True,
        from_timestamp=1620065527,
        to_timestamp=1620670327,
    )
    expected_trades = [AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EthereumToken('0x467Bccd9d29f223BcE8043b84E8C8B282827790F'),
        quote_asset=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        amount=AssetAmount(FVal('22504.57')),
        rate=Price(FVal('0.00001404159244100198315275519594')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0xbfb58e9f11484d1cdf0a6f13fe437c2db273663f8711586ca81f2c43cfafef52',
            log_index=375,
            address=string_to_ethereum_address('0x000e62eA8Bf5F69E1e32920600839f56313C490F'),
            from_address=string_to_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
            to_address=string_to_ethereum_address('0x000e62eA8Bf5F69E1e32920600839f56313C490F'),
            timestamp=Timestamp(1620606134),
            location=Location.UNISWAP,
            token0=EthereumToken('0x467Bccd9d29f223BcE8043b84E8C8B282827790F'),
            token1=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('0.316')),
            amount0_out=AssetAmount(FVal('22504.57')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EthereumToken('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'),
        quote_asset=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        amount=AssetAmount(FVal('19902976.398493988867801422')),
        rate=Price(FVal('3.768280607802713997319461775E-9')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x6c94a0c25739863fd4cfc40cacf32b5a74d9d4a04b675e72c01dd71e4b3113d1',
            log_index=133,
            address=string_to_ethereum_address('0x000e62eA8Bf5F69E1e32920600839f56313C490F'),
            from_address=string_to_ethereum_address('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
            to_address=string_to_ethereum_address('0x000e62eA8Bf5F69E1e32920600839f56313C490F'),
            timestamp=Timestamp(1620516124),
            location=Location.UNISWAP,
            token0=EthereumToken('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'),
            token1=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('0.075')),
            amount0_out=AssetAmount(FVal('19902976.398493988867801422')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EthereumToken('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'),
        quote_asset=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        amount=AssetAmount(FVal('56219942.782018870681977432')),
        rate=Price(FVal('3.913202132791280491969510435E-9')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash='0x0007999335475071899b18de7226d32b5ff83a182d37485faac0e8050e2fec14',
            log_index=179,
            address=string_to_ethereum_address('0x000e62eA8Bf5F69E1e32920600839f56313C490F'),
            from_address=string_to_ethereum_address('0xE592427A0AEce92De3Edee1F18E0157C05861564'),
            to_address=string_to_ethereum_address('0x000e62eA8Bf5F69E1e32920600839f56313C490F'),
            timestamp=Timestamp(1620515287),
            location=Location.UNISWAP,
            token0=EthereumToken('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'),
            token1=EthereumToken('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('0.22')),
            amount0_out=AssetAmount(FVal('56219942.782018870681977432')),
            amount1_out=AssetAmount(ZERO),
        )],
    )]
    assert len(trades) == 1
    assert '0x000e62ea8bf5f69e1e32920600839f56313c490f' in trades.keys()
    assert trades['0x000e62ea8bf5f69e1e32920600839f56313c490f'] == expected_trades
