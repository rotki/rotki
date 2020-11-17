import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests
from eth_utils.typing import HexAddress, HexStr

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.tests.utils.aave import AAVE_TEST_ACC_1
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.typing import (
    AssetAmount,
    ChecksumEthAddress,
    Location,
    Price,
    Timestamp,
    TradeType,
)

# Addresses
# Harvest Finance USDC-WETH vault
TEST_ADDRESS_USDC_WETH = ChecksumEthAddress(
    HexAddress(HexStr('0xA79a083FDD87F73c2f983c5551EC974685D6bb36')),
)


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_USDC_WETH]])
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


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_USDC_WETH]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_balances_graph(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        rotki_premium_credentials,
        start_with_valid_premium,
):
    """Check querying the uniswap balances endpoint works. Uses real data.

    Requires the graph available and premium credentials.

    TODO: Here we should use a test account for which we will know what
    balances it has and we never modify
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    # Set module premium attribute
    rotki.chain_manager.uniswap.premium = premium

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
        json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(
            UserWarning(f'Test account {TEST_ADDRESS_USDC_WETH} has no uniswap balances'),
        )
        return

    address_balances = result[TEST_ADDRESS_USDC_WETH]

    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['assets']) == 2
        assert lp['total_supply']
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

            assert lp_asset['total_amount']
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']


EXPECTED_TRADES = [AMMTrade(
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('USDT'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('20632.012923')),
    rate=Price(FVal('375.1275076909090909090909091')),
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
    rate=Price(FVal('371.4351220275573898976315789')),
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
    quote_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'),  # noqa: E501
        symbol='ALEPH',
        name='aleph.im v2',
    ),
    amount=AssetAmount(FVal('904.171423330858608178')),
    rate=Price(FVal('0.1604821621994156262081817395')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6',
        log_index=98,
        address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
        timestamp=Timestamp(1602796833),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'),  # noqa: E501
            symbol='ALEPH',
            name='aleph.im v2',
        ),
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
    rate=Price(FVal('374.9648272096103830092879257')),
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
    rate=Price(FVal('0.9835081452620556913888108835')),
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
    rate=Price(FVal('0.8986486458818072655160164770')),
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
    rate=Price(FVal('0.7259977767454599148166666667')),
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
    rate=Price(FVal('20.8229580065011456795')),
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
    rate=Price(FVal('24.53020699025697325558361475')),
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
    rate=Price(FVal('1.043359110743797209725374332')),
    trade_index=0,
    swaps=[AMMSwap(
        tx_hash='0x06d91cb3501019ac9f01f5e48d4790cfc69c1aa0593a7c4e80d83aaba3539578',
        log_index=140,
        address=CRAZY_UNISWAP_ADDRESS,
        from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
        to_address=deserialize_ethereum_address('0x21aD02e972E968D9c76a7081a483d782001d6558'),
        timestamp=Timestamp(1605431265),
        location=Location.UNISWAP,
        token0=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x37236CD05b34Cc79d3715AF2383E96dd7443dCF1'),  # noqa: E501
            symbol='SLP',
            name='Small Love Potion',
        ),
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
        token1=UnknownEthereumToken(
            ethereum_address=deserialize_ethereum_address('0x37236CD05b34Cc79d3715AF2383E96dd7443dCF1'),  # noqa: E501
            symbol='SLP',
            name='Small Love Potion',
        ),
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
    rate=Price(FVal('4.028080078867186255105216731')),
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
    rate=Price(FVal('0.5731680724164101146042500330')),
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
    rate=Price(FVal('0.7095950786343146869149332940')),
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
