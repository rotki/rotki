import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests
from eth_utils.typing import HexAddress, HexStr

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.unknown_asset import UnknownEthereumToken
from rotkehlchen.chain.ethereum.trades import AMMTrade
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
    Fee,
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
    tx_hash='0x13723c8b286ec56e95b00e091557e6a76f723d20a52503d2e08df5867d942b51',
    log_index=319,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1603180607),
    location=Location.UNISWAP,
    trade_type=TradeType.SELL,
    base_asset=EthereumToken('WETH'),
    quote_asset=EthereumToken('USDT'),
    amount=AssetAmount(FVal('55')),
    rate=Price(FVal('0.002665760253508154513092246380')),
    fee=Fee(FVal('0.165')),
    notes='',
), AMMTrade(
    tx_hash='0xf6272151d26f391886232263a384d1d9fb84c54e33119d014bc0b556dc27e900',
    log_index=90,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1603056982),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('1411.453463704718081611')),
    rate=Price(FVal('371.4351220275573898976315789')),
    fee=Fee(FVal('0.0114')),
    notes='',
), AMMTrade(
    tx_hash='0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6',
    log_index=98,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
    timestamp=Timestamp(1602796833),
    location=Location.UNISWAP,
    trade_type=TradeType.SELL,
    base_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x27702a26126e0B3702af63Ee09aC4d1A084EF628'),  # noqa: E501
        symbol='ALEPH',
        name='aleph.im v2',
    ),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('5634.092979176915803392')),
    rate=Price(FVal('2336.169422971930807616108754')),
    fee=Fee(FVal('16.902278937530747410176')),
    notes='',
), AMMTrade(
    tx_hash='0x296c750be451687a6e95de55a85c1b86182e44138902599fb277990447d5ded6',
    log_index=101,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1602796833),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('904.171423330858608178')),
    rate=Price(FVal('374.9135202626966097309933754')),
    fee=Fee(FVal('0.007235039878241668578')),
    notes='',
), AMMTrade(
    tx_hash='0x96531b9f02bbb9b3f97e0a761eb49c8fd0752d8cc934dda4c5296e1e35d2b91e',
    log_index=32,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1602796676),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('1211.13639188704153712')),
    rate=Price(FVal('374.9648272096103830092879257')),
    fee=Fee(FVal('0.00969')),
    notes='',
), AMMTrade(
    tx_hash='0x0b9b335b5a805dc58e330413ef6de52fc13369247978d90bb0436a9aadf98c86',
    log_index=198,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1601858969),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('USDC'),
    amount=AssetAmount(FVal('27.555943016050019506')),
    rate=Price(FVal('0.9835081452620556913888108835')),
    fee=Fee(FVal('0.084054036')),
    notes='',
), AMMTrade(
    tx_hash='0xf3a3be42927fafb244e3968537491c8c5b1e789237e633ae972073726bf185f0',
    log_index=169,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1601851402),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('yyDAI+yUSDC+yUSDT+yTUSD'),
    quote_asset=EthereumToken('yDAI+yUSDC+yUSDT+yTUSD'),
    amount=AssetAmount(FVal('49.398809059381378894')),
    rate=Price(FVal('0.8986486458818072655160164770')),
    fee=Fee(FVal('0.164910310450337380488')),
    notes='',
), AMMTrade(
    tx_hash='0x99a50afa868558ed1a854a124cf3abb1cba3a0bb86a4e0ceef23246154387247',
    log_index=292,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1601847584),
    location=Location.UNISWAP,
    trade_type=TradeType.SELL,
    base_asset=EthereumToken('YAM'),
    quote_asset=EthereumToken('yyDAI+yUSDC+yUSDT+yTUSD'),
    amount=AssetAmount(FVal('60')),
    rate=Price(FVal('1.377414686423491971126255967')),
    fee=Fee(FVal('0.180')),
    notes='',
), AMMTrade(
    tx_hash='0x648ddb305ae1c5b4185bdff50fa81e2f4757d2957c2a369269712529881d41c9',
    log_index=122,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1601547546),
    location=Location.UNISWAP,
    trade_type=TradeType.SELL,
    base_asset=EthereumToken('WETH'),
    quote_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0xEfc1C73A3D8728Dc4Cf2A18ac5705FE93E5914AC'),  # noqa: E501
        symbol='METRIC',
        name='Metric.exchange',
    ),
    amount=AssetAmount(FVal('10')),
    rate=Price(FVal('0.04802391666389518346374466944')),
    fee=Fee(FVal('0.030')),
    notes='',
), AMMTrade(
    tx_hash='0xa1cc9423122b91a688d030dbe640eadf778c3d35c65deb032abebcba853387f5',
    log_index=74,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11'),
    timestamp=Timestamp(1601481706),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('WETH'),
    quote_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0xEfc1C73A3D8728Dc4Cf2A18ac5705FE93E5914AC'),  # noqa: E501
        symbol='METRIC',
        name='Metric.exchange',
    ),
    amount=AssetAmount(FVal('0.235217404883028274')),
    rate=Price(FVal('0.06964233827338962583711401226')),
    fee=Fee(FVal('0.010132517548146640923')),
    notes='',
), AMMTrade(
    tx_hash='0xa1cc9423122b91a688d030dbe640eadf778c3d35c65deb032abebcba853387f5',
    log_index=77,
    address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    from_address=deserialize_ethereum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D'),
    to_address=deserialize_ethereum_address('0x21d05071cA08593e13cd3aFD0b4869537e015C92'),
    timestamp=Timestamp(1601481706),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=EthereumToken('DAI'),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('82.850917596149392912')),
    rate=Price(FVal('352.2312374688024838546352371')),
    fee=Fee(FVal('0.000705652214649084822')),
    notes='',
)]


def _query_and_assert_simple_uniswap_trades(setup, api_server, async_query):
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            "uniswaphistoryresource",
        ), json={'async_query': async_query, 'to_timestamp': 1605437542})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    for idx, trade in enumerate(result['trades'][AAVE_TEST_ACC_1]):
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
    db_trades = rotki.data.db.get_amm_trades()
    assert len(db_trades) == 36
    # Query a 2nd time to make sure that when retrieving from the database everything works fine
    _query_and_assert_simple_uniswap_trades(setup, rotkehlchen_api_server, async_query)


CRAZY_UNISWAP_ADDRESS = '0xB1637bE0173330664adecB343faF112Ca837dA06'
EXPECTED_CRAZY_TRADES = [AMMTrade(
    # According to etherscan this should be 2 uniswap trades, but it shows as one from the graph
    tx_hash='0x06d91cb3501019ac9f01f5e48d4790cfc69c1aa0593a7c4e80d83aaba3539578',
    log_index=143,
    address=deserialize_ethereum_address(CRAZY_UNISWAP_ADDRESS),
    timestamp=Timestamp(1605431265),
    location=Location.UNISWAP,
    trade_type=TradeType.BUY,
    base_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x30BCd71b8d21FE830e493b30e90befbA29de9114'),  # noqa: E501
        symbol='🐟',
        name='Penguin Party Fish',
    ),
    quote_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x37236CD05b34Cc79d3715AF2383E96dd7443dCF1'),  # noqa: E501
        symbol='SLP',
        name='Small Love Potion',
    ),
    amount=AssetAmount(FVal('20.085448793024895802')),
    rate=Price(FVal('0.02292859451258549749086757991')),
    fee=Fee(FVal('2.628')),
    notes='',
), AMMTrade(
    tx_hash='0xde838fff85d4df6d1b4270477456bab1b644e7f4830f606fc2dc522608b6194f',
    log_index=20,
    address=deserialize_ethereum_address(CRAZY_UNISWAP_ADDRESS),
    timestamp=Timestamp(1605420918),
    location=Location.UNISWAP,
    trade_type=TradeType.SELL,
    base_asset=UnknownEthereumToken(
        ethereum_address=deserialize_ethereum_address('0x86B0Aa51eB489585D88d2e671E5ee1b9e457Be60'),  # noqa: E501
        symbol='FMK',
        name='https://t.me/fomok',
    ),
    quote_asset=EthereumToken('WETH'),
    amount=AssetAmount(FVal('1.318527141747939222')),
    rate=Price(FVal('56.09408723106908869704792258')),
    fee=Fee(FVal('0.003955581425243817666')),
    notes='',
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
            "uniswaphistoryresource",
        ), json={'async_query': async_query, 'to_timestamp': 1605437542})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    for idx, trade in enumerate(result['trades'][CRAZY_UNISWAP_ADDRESS]):
        if idx == len(EXPECTED_CRAZY_TRADES):
            break  # test up to last EXPECTED_CRAZY_TRADES trades from 1605437542
        assert trade == EXPECTED_CRAZY_TRADES[idx].serialize()
