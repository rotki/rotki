from typing import List

import pytest

from rotkehlchen.chain.ethereum.interfaces.ammswap.typing import LiquidityPool, LiquidityPoolEvent

from .utils import (
    LP_1_EVENTS,
    LP_1_EVENTS_BALANCE,
    LP_2_EVENTS,
    LP_2_EVENTS_BALANCE,
    LP_3_BALANCE,
    LP_3_EVENTS,
    LP_3_EVENTS_BALANCE,
    TEST_ADDRESS_1,
)


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_no_events_no_balances(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events: List[LiquidityPoolEvent] = []
    balances: List[LiquidityPool] = []
    events_balances = rotki.chain_manager.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=events,
        balances=balances,
    )
    assert events_balances == []


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_single_pool_without_balances(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    balances: List[LiquidityPool] = []
    events_balances = rotki.chain_manager.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=LP_1_EVENTS,
        balances=balances,
    )
    assert events_balances == [LP_1_EVENTS_BALANCE]


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_multiple_pools_without_balances(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events = list(LP_1_EVENTS)
    events.extend(LP_2_EVENTS)
    balances: List[LiquidityPool] = []
    events_balances = rotki.chain_manager.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=events,
        balances=balances,
    )
    assert events_balances == [LP_1_EVENTS_BALANCE, LP_2_EVENTS_BALANCE]


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_single_pool_with_balances(rotkehlchen_api_server):
    """Test LP current balances are factorized in the pool events balance
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events_balances = rotki.chain_manager.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=LP_3_EVENTS,
        balances=[LP_3_BALANCE],
    )
    assert events_balances == [LP_3_EVENTS_BALANCE]
