import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.chain.ethereum.manager import NodeName
from rotkehlchen.chain.ethereum.modules.uniswap import UniswapPoolEvent, UniswapPoolEventsBalance
from rotkehlchen.chain.ethereum.modules.uniswap.typing import UNISWAP_EVENTS_PREFIX, EventType
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
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
from rotkehlchen.tests.utils.ethereum import INFURA_TEST
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp, TradeType

# Addresses
# DAI/WETH pool: 0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11
# From that pool find a holder and test
LP_HOLDER_ADDRESS = deserialize_ethereum_address('0x631fdEF0781c00ADd20176f254F5ae5C26Da1c99')
# Uniswap Factory contract
TEST_ADDRESS_FACTORY_CONTRACT = (
    deserialize_ethereum_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
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


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize(
    'start_with_valid_premium,ethrpc_endpoint,ethereum_manager_connect_at_start',
    [  # Test with infura (as own node), many open nodes, and premium + graph
        (False, INFURA_TEST, (NodeName.OWN, NodeName.MYCRYPTO)),
        (False, '', (NodeName.MYCRYPTO, NodeName.BLOCKSCOUT, NodeName.AVADO_POOL)),
        (True, '', ()),
    ],
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

    if len(result) != 1:
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


EXPECTED_TRADES = [AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('USDT'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('20632.012923')),
    rate=Price(FVal('0.002665760253508154513092246380')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x13723c8b286ec56e95b00e091557e6a76f723d20a52503d2e08df5867d942b51',
        log_index=319,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1603180607),
        location=Location.UNISWAP,
        token0=EthereumToken('WETH'),
        token1=EthereumToken('USDT'),
        amount0_in=AssetAmount(FVal(55)),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('20632.012923')),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('1411.453463704718081611')),
    rate=Price(FVal('0.002692260210992670573731568435')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0xf6272151d26f391886232263a384d1d9fb84c54e33119d014bc0b556dc27e900',
        log_index=90,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1603056982),
        location=Location.UNISWAP,
        token0=EthereumToken('DAI'),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('3.8')),
        amount0_out=AssetAmount(FVal('1411.453463704718081611')),
        amount1_out=AssetAmount(ZERO),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('ALEPH'),
    amount=AssetAmount(FVal('904.171423330858608178')),
    rate=Price(FVal('6.231222126465350944166830285')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6',
        log_index=98,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
        timestamp=Timestamp(1602796833),
        location=Location.UNISWAP,
        token0=EthereumToken('ALEPH'),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(FVal('5634.092979176915803392')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('2.411679959413889526')),
    ), AMMSwap(
        tx_hash='0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6',
        log_index=101,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1602796833),
        location=Location.UNISWAP,
        token0=EthereumToken('DAI'),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('2.411679959413889526')),
        amount0_out=AssetAmount(FVal('904.171423330858608178')),
        amount1_out=AssetAmount(ZERO),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('1211.13639188704153712')),
    rate=Price(FVal('0.002666916807748974669759705026')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x96531b9f02bbb9b3f97e0a761eb49c8fd0752d8cc934dda4c5296e1e35d2b91e',
        log_index=32,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1602796676),
        location=Location.UNISWAP,
        token0=EthereumToken('DAI'),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('3.23')),
        amount0_out=AssetAmount(FVal('1211.13639188704153712')),
        amount1_out=AssetAmount(ZERO),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('USDC'),
    amount=AssetAmount(FVal('27.555943016050019506')),
    rate=Price(FVal('1.016768396700517467316300829')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x0b9b335b5a805dc58e330413ef6de52fc13369247978d90bb0436a9aadf98c86',
        log_index=198,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1601858969),
        location=Location.UNISWAP,
        token0=EthereumToken('DAI'),
        token1=EthereumToken('USDC'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('28.018012')),
        amount0_out=AssetAmount(FVal('27.555943016050019506')),
        amount1_out=AssetAmount(ZERO),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('yyDAI+yUSDC+yUSDT+yTUSD'),
    quote_asset=EthereumToken('yDAI+yUSDC+yUSDT+yTUSD'),
    amount=AssetAmount(FVal('49.398809059381378894')),
    rate=Price(FVal('1.112781958313352583115667770')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0xf3a3be42927fafb244e3968537491c8c5b1e789237e633ae972073726bf185f0',
        log_index=169,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1601851402),
        location=Location.UNISWAP,
        token0=EthereumToken('yyDAI+yUSDC+yUSDT+yTUSD'),
        token1=EthereumToken('yDAI+yUSDC+yUSDT+yTUSD'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('54.970103483445793496')),
        amount0_out=AssetAmount(FVal('49.398809059381378894')),
        amount1_out=AssetAmount(ZERO),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('yyDAI+yUSDC+yUSDT+yTUSD'),
    quote_asset=EthereumToken('YAM'),
    amount=AssetAmount(FVal('43.559866604727594889')),
    rate=Price(FVal('1.377414686423491971126255967')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x99a50afa868558ed1a854a124cf3abb1cba3a0bb86a4e0ceef23246154387247',
        log_index=292,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1601847584),
        location=Location.UNISWAP,
        token0=EthereumToken('YAM'),
        token1=EthereumToken('yyDAI+yUSDC+yUSDT+yTUSD'),
        amount0_in=AssetAmount(FVal('60')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('43.559866604727594889')),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0xEfc1C73A3D8728Dc4Cf2A18ac5705FE93E5914AC'),  # noqa: E501
        symbol='METRIC',
        name='Metric.exchange',
    ),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('208.229580065011456795')),
    rate=Price(FVal('0.04802391666389518346374466944')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x648ddb305ae1c5b4185bdff50fa81e2f4757d2957c2a369269712529881d41c9',
        log_index=122,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1601547546),
        location=Location.UNISWAP,
        token0=EthereumToken('WETH'),
        token1=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0xEfc1C73A3D8728Dc4Cf2A18ac5705FE93E5914AC'),  # noqa: E501
            symbol='METRIC',
            name='Metric.exchange',
        ),
        amount0_in=AssetAmount(FVal('10')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('208.229580065011456795')),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0xEfc1C73A3D8728Dc4Cf2A18ac5705FE93E5914AC'),  # noqa: E501
        symbol='METRIC',
        name='Metric.exchange',
    ),
    amount=AssetAmount(FVal('82.850917596149392912')),
    rate=Price(FVal('0.04076606448519512519987536529')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0xa1cc9423122b91a688d030dbe640eadf778c3d35c65deb032abebcba853387f5',
        log_index=74,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
        timestamp=Timestamp(1601481706),
        location=Location.UNISWAP,
        token0=EthereumToken('WETH'),
        token1=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0xEfc1C73A3D8728Dc4Cf2A18ac5705FE93E5914AC'),  # noqa: E501
            symbol='METRIC',
            name='Metric.exchange',
        ),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('3.377505849382213641')),
        amount0_out=AssetAmount(FVal('0.235217404883028274')),
        amount1_out=AssetAmount(ZERO),
    ), AMMSwap(
        tx_hash='0xa1cc9423122b91a688d030dbe640eadf778c3d35c65deb032abebcba853387f5',
        log_index=77,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        timestamp=Timestamp(1601481706),
        location=Location.UNISWAP,
        token0=EthereumToken('DAI'),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('0.235217404883028274')),
        amount0_out=AssetAmount(FVal('82.850917596149392912')),
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
        ), json={'async_query': async_query, 'to_timestamp': 1605437542})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    for idx, trade in enumerate(result[AAVE_TEST_ACC_1]):
        if idx == len(EXPECTED_TRADES):
            break  # test up to last EXPECTED_TRADES trades from 1605437542
        assert trade == EXPECTED_TRADES[idx].serialize()


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
    assert len(db_trades) == 36
    # Query a 2nd time to make sure that when retrieving from the database everything works fine
    _query_and_assert_simple_uniswap_trades(setup, rotkehlchen_api_server, async_query)


CRAZY_UNISWAP_ADDRESS = deserialize_ethereum_address('0xB1637bE0173330664adecB343faF112Ca837dA06')
EXPECTED_CRAZY_TRADES = [AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('WETH'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('0.088104479651219417')),
    rate=Price(FVal('0.9584427736363110293711465160')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x06d91cb3501019ac9f01f5e48d4790cfc69c1aa0593a7c4e80d83aaba3539578',
        log_index=140,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21aD02e972E968D9c76a7081a483d782001d6558'),
        timestamp=Timestamp(1605431265),
        location=Location.UNISWAP,
        token0=EthereumToken('SLP'),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('0.084443101846698663')),
        amount0_out=AssetAmount(FVal('876')),
        amount1_out=AssetAmount(ZERO),
    ), AMMSwap(
        tx_hash='0x06d91cb3501019ac9f01f5e48d4790cfc69c1aa0593a7c4e80d83aaba3539578',
        log_index=143,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=CRAZY_UNISWAP_ADDRESS,
        timestamp=Timestamp(1605431265),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('SLP'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('876')),
        amount0_out=AssetAmount(FVal('20.085448793024895802')),
        amount1_out=AssetAmount(ZERO),
    ), AMMSwap(
        tx_hash='0x06d91cb3501019ac9f01f5e48d4790cfc69c1aa0593a7c4e80d83aaba3539578',
        log_index=146,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0xB8db34F834E9dF42F2002CeB7B829DaD89d08E14'),
        timestamp=Timestamp(1605431265),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(FVal('20.085448793024895802')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('0.088104479651219417')),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
        symbol='🐟',
        name='Penguin Party Fish',
    ),
    quote_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x86B0Aa51eB489585D88d2e671E5ee1b9e457Be60'),  # noqa: E501
        symbol='FMK',
        name='https://t.me/fomok',
    ),
    amount=AssetAmount(FVal('5.311132913120564692')),
    rate=Price(FVal('0.2482572293550899816477686816')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f',
        log_index=20,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=CRAZY_UNISWAP_ADDRESS,
        timestamp=Timestamp(1605420918),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x86B0Aa51eB489585D88d2e671E5ee1b9e457Be60'),  # noqa: E501
            symbol='FMK',
            name='https://t.me/fomok',
        ),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(FVal('1.318527141747939222')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('0.023505635029170072')),
    ), AMMSwap(
        tx_hash='0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f',
        log_index=23,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0xc61288821b4722Ce29249F0BA03b633F0bE46a5A'),
        timestamp=Timestamp(1605420918),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('0.023505635029170072')),
        amount0_out=AssetAmount(FVal('5.311132913120564692')),
        amount1_out=AssetAmount(ZERO),
    )],
)]

# Should be trade index 41 in the returned array
# This is a multi token trade. At log index 166 both amount0In and amount1In are
# positive. Test that we handle it in some way. Still not 100% sure this is the right way
# https://etherscan.io/tx/0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017
BOTH_IN_TRADES = [AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('WETH'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('0.106591333983182783')),
    rate=Price(FVal('1.744688945746953393022811238')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
        log_index=166,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        to_address=deserialize_ethereum_address('0x5aBC567A74983Dff7f0185731e5043F77CDEEbd4'),
        timestamp=Timestamp(1604657395),
        location=Location.UNISWAP,
        token0=EthereumToken('WETH'),
        token1=EthereumToken('aDAI'),
        amount0_in=AssetAmount(FVal('0.185968722112880576')),
        amount1_in=AssetAmount(FVal('0.150214308402939121')),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('77.422341021064126448')),
    ), AMMSwap(
        tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
        log_index=169,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        to_address=CRAZY_UNISWAP_ADDRESS,
        timestamp=Timestamp(1604657395),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('aDAI'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('77.451074341665209573')),
        amount0_out=AssetAmount(FVal('105.454952420015590185')),
        amount1_out=AssetAmount(ZERO),
    ), AMMSwap(
        tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
        log_index=172,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        to_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        timestamp=Timestamp(1604657395),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(FVal('105.454952420015590185')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('0.213182667966365566')),
    )],
), AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('WETH'),
    quote_asset=EthereumToken('aDAI'),
    amount=AssetAmount(FVal('0.106591333983182783')),
    rate=Price(FVal('1.409254418625053124546000710')),
    trade_index=1,
    swaps=[AMMSwap(
        tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
        log_index=166,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        to_address=deserialize_ethereum_address('0x5aBC567A74983Dff7f0185731e5043F77CDEEbd4'),
        timestamp=Timestamp(1604657395),
        location=Location.UNISWAP,
        token0=EthereumToken('WETH'),
        token1=EthereumToken('aDAI'),
        amount0_in=AssetAmount(FVal('0.185968722112880576')),
        amount1_in=AssetAmount(FVal('0.150214308402939121')),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('77.422341021064126448')),
    ), AMMSwap(
        tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
        log_index=169,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        to_address=CRAZY_UNISWAP_ADDRESS,
        timestamp=Timestamp(1604657395),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('aDAI'),
        amount0_in=AssetAmount(ZERO),
        amount1_in=AssetAmount(FVal('77.451074341665209573')),
        amount0_out=AssetAmount(FVal('105.454952420015590185')),
        amount1_out=AssetAmount(ZERO),
    ), AMMSwap(
        tx_hash='0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017',
        log_index=172,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        to_address=deserialize_ethereum_address('0xfe7f0897239ce9cc6645D9323E6fE428591b821c'),
        timestamp=Timestamp(1604657395),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
            symbol='🐟',
            name='Penguin Party Fish',
        ),
        token1=EthereumToken('WETH'),
        amount0_in=AssetAmount(FVal('105.454952420015590185')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('0.213182667966365566')),
    )],
)]


@pytest.mark.parametrize('ethereum_accounts', [[CRAZY_UNISWAP_ADDRESS]])
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
        eth_balances=['33000030003'],
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

    for idx, trade in enumerate(result[CRAZY_UNISWAP_ADDRESS]):
        if idx == len(EXPECTED_CRAZY_TRADES):
            break  # test up to last EXPECTED_CRAZY_TRADES trades from 1605437542
        assert trade == EXPECTED_CRAZY_TRADES[idx].serialize()

    found_idx = -1
    for idx, trade in enumerate(result[CRAZY_UNISWAP_ADDRESS]):
        if trade['tx_hash'] == '0x09f6c9863a97053ecbc4e4aeece3284f1d983473ef0e351fe69188adc52af017':  # noqa: E501
            found_idx = idx
            break
    assert found_idx != -1, 'Could not find the transaction hash index'

    # Also test for the swaps that have both tokens at amountIn or amountOut
    for idx, trade in enumerate(BOTH_IN_TRADES):
        assert trade.serialize() == result[CRAZY_UNISWAP_ADDRESS][found_idx + idx]

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

TEST_EVENTS_ADDRESS_1 = "0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F"
EXPECTED_EVENTS_BALANCES_1 = [
    UniswapPoolEventsBalance(
        address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
        pool_address=deserialize_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),
        token0=EthereumToken('$BASED'),
        token1=EthereumToken('WETH'),
        events=[
            UniswapPoolEvent(
                tx_hash='0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824',
                log_index=263,
                address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1604273256),
                event_type=EventType.MINT,
                pool_address=deserialize_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
                token0=EthereumToken('$BASED'),
                token1=EthereumToken('WETH'),
                amount0=AssetAmount(FVal('605.773209925184996494')),
                amount1=AssetAmount(FVal('1.106631443395672732')),
                usd_price=Price(FVal('872.4689300619698095220125311431804')),
                lp_amount=AssetAmount(FVal('1.220680531244355402')),
            ),
            UniswapPoolEvent(
                tx_hash='0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa',
                log_index=66,
                address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1604283808),
                event_type=EventType.BURN,
                pool_address=deserialize_ethereum_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
                token0=EthereumToken('$BASED'),
                token1=EthereumToken('WETH'),
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
EXPECTED_EVENTS_BALANCES_2 = [
    # Response index 0
    UniswapPoolEventsBalance(
        address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
        pool_address=deserialize_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),
        token0=EthereumToken('WETH'),
        token1=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0xCF67CEd76E8356366291246A9222169F4dBdBe64'),  # noqa: E501
            symbol='DICE',
            name='DICE.FINANCE TOKEN',
        ),
        events=[
            UniswapPoolEvent(
                tx_hash='0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4',
                log_index=99,
                address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1598270334),
                event_type=EventType.MINT,
                pool_address=deserialize_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
                token0=EthereumToken('WETH'),
                token1=UnknownEthereumToken(
                    ethereum_address=deserialize_ethereum_address('0xCF67CEd76E8356366291246A9222169F4dBdBe64'),  # noqa: E501
                    symbol='DICE',
                    name='DICE.FINANCE TOKEN',
                ),
                amount0=AssetAmount(FVal('1.580431277572006656')),
                amount1=AssetAmount(FVal('3')),
                usd_price=Price(FVal('1281.249386421513581165086356450817')),
                lp_amount=AssetAmount(FVal('2.074549918528068811')),
            ),
            UniswapPoolEvent(
                tx_hash='0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa',
                log_index=208,
                address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1599000975),
                event_type=EventType.BURN,
                pool_address=deserialize_ethereum_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
                token0=EthereumToken('WETH'),
                token1=UnknownEthereumToken(
                    ethereum_address=deserialize_ethereum_address('0xCF67CEd76E8356366291246A9222169F4dBdBe64'),  # noqa: E501
                    symbol='DICE',
                    name='DICE.FINANCE TOKEN',
                ),
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
        address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
        pool_address=deserialize_ethereum_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x26E43759551333e57F073bb0772F50329A957b30'),  # noqa: E501
            symbol='DGVC',
            name='DegenVC',
        ),
        token1=EthereumToken('WETH'),
        events=[
            UniswapPoolEvent(
                tx_hash='0xc612f05bf9f3d814ffbe3649feacbf5bda213297bf7af53a56956814652fe9cc',
                log_index=171,
                address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1598391968),
                event_type=EventType.MINT,
                pool_address=deserialize_ethereum_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
                token0=UnknownEthereumToken(
                    ethereum_address=deserialize_ethereum_address('0x26E43759551333e57F073bb0772F50329A957b30'),  # noqa: E501
                    symbol='DGVC',
                    name='DegenVC',
                ),
                token1=EthereumToken('WETH'),
                amount0=AssetAmount(FVal('322.230285353834005677')),
                amount1=AssetAmount(FVal('1.247571217823345601')),
                usd_price=Price(FVal('945.2160925652988117900888961551871')),
                lp_amount=AssetAmount(FVal('18.297385821424685079')),
            ),
            UniswapPoolEvent(
                tx_hash='0x597f8790a3b9353114b364777c9d32373930e5ad6b8c8f97a58cd2dd58f12b89',
                log_index=201,
                address=deserialize_ethereum_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1598607431),
                event_type=EventType.BURN,
                pool_address=deserialize_ethereum_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
                token0=UnknownEthereumToken(
                    ethereum_address=deserialize_ethereum_address('0x26E43759551333e57F073bb0772F50329A957b30'),  # noqa: E501
                    symbol='DGVC',
                    name='DegenVC',
                ),
                token1=EthereumToken('WETH'),
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
    assert EXPECTED_EVENTS_BALANCES_2[0].serialize() == events_balances[0]
    assert EXPECTED_EVENTS_BALANCES_2[1].serialize() == events_balances[3]

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
