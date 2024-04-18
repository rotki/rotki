import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.assets.asset import EvmToken, UnderlyingToken
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import ChainID, EvmTokenKind

# Top holder of WBTC-WETH pool (0x1eff8af5d577060ba4ac8a29a13525bb0ee2a3d5)
BALANCER_TEST_ADDR1 = string_to_evm_address('0x49a2DcC237a65Cc1F412ed47E0594602f6141936')
BALANCER_TEST_ADDR2 = string_to_evm_address('0x7716a99194d758c8537F056825b75Dd0C8FDD89f')
BALANCER_TEST_ADDR2_POOL1 = EvmToken.initialize(
    address=string_to_evm_address('0x59A19D8c652FA0284f44113D0ff9aBa70bd46fB4'),
    chain_id=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    name='Balancer Pool Token',
    symbol='BPT',
    protocol='balancer',
    underlying_tokens=[
        UnderlyingToken(address=string_to_evm_address('0xba100000625a3754423978a60c9317c58a424e3D'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.8)),  # noqa: E501  # BAL
        UnderlyingToken(address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.2)),  # noqa: E501  # WETH
    ],
)
BALANCER_TEST_ADDR2_POOL2 = EvmToken.initialize(
    address=string_to_evm_address('0x574FdB861a0247401B317a3E68a83aDEAF758cf6'),
    chain_id=ChainID.ETHEREUM,
    token_kind=EvmTokenKind.ERC20,
    name='Balancer Pool Token',
    symbol='BPT',
    protocol='balancer',
    underlying_tokens=[
        UnderlyingToken(address=string_to_evm_address('0x0D8775F648430679A709E98d2b0Cb6250d2887EF'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.1)),  # noqa: E501  # BAT
        UnderlyingToken(address=string_to_evm_address('0xdd974D5C2e2928deA5F71b9825b8b646686BD200'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.1)),  # noqa: E501  # KNC
        UnderlyingToken(address=string_to_evm_address('0x80fB784B7eD66730e8b1DBd9820aFD29931aab03'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.1)),  # noqa: E501  # LEND
        UnderlyingToken(address=string_to_evm_address('0x514910771AF9Ca656af840dff83E8264EcF986CA'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.35)),  # noqa: E501  # LINK
        UnderlyingToken(address=string_to_evm_address('0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.1)),  # noqa: E501  # MKR
        UnderlyingToken(address=string_to_evm_address('0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.1)),  # noqa: E501  # SNX
        UnderlyingToken(address=string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'), token_kind=EvmTokenKind.ERC20, weight=FVal(0.15)),  # noqa: E501  # WETH
    ],
)


@pytest.mark.parametrize('ethereum_accounts', [[BALANCER_TEST_ADDR1]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_balancer_module_not_activated(rotkehlchen_api_server):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'evmmodulebalancesresource', module='balancer'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='balancer module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [[BALANCER_TEST_ADDR1]])
@pytest.mark.parametrize('ethereum_modules', [['balancer']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_balances(rotkehlchen_api_server, ethereum_accounts):
    """Test get the balances for premium users works as expected"""
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'evmmodulebalancesresource', module='balancer'),
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
            UserWarning(f'Test account {BALANCER_TEST_ADDR1} has no balances'),
        )
        return

    for pool_share in result[BALANCER_TEST_ADDR1]:
        assert pool_share['address'] is not None
        assert FVal(pool_share['total_amount']) >= ZERO
        assert FVal(pool_share['user_balance']['amount']) >= ZERO
        assert FVal(pool_share['user_balance']['usd_value']) >= ZERO

        for pool_token in pool_share['tokens']:
            assert pool_token['token'] is not None
            assert pool_token['total_amount'] is not None
            assert FVal(pool_token['user_balance']['amount']) >= ZERO
            assert FVal(pool_token['user_balance']['usd_value']) >= ZERO
            assert FVal(pool_token['usd_price']) >= ZERO
            assert FVal(pool_token['weight']) >= ZERO
