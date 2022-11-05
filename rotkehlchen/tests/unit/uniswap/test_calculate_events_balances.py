from typing import List

import pytest

from rotkehlchen.chain.ethereum.interfaces.ammswap.types import LiquidityPool, LiquidityPoolEvent

from .utils import (
    TEST_ADDRESS_1,
    const_lp_1_events,
    const_lp_1_events_balance,
    const_lp_2_events,
    const_lp_2_events_balance,
    const_lp_3_balance,
    const_lp_3_events,
    const_lp_3_events_balance,
)


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_no_events_no_balances(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events: List[LiquidityPoolEvent] = []
    balances: List[LiquidityPool] = []
    events_balances = rotki.chains_aggregator.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=events,
        balances=balances,
    )
    assert events_balances == []


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_single_pool_without_balances(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    balances: List[LiquidityPool] = []
    events_balances = rotki.chains_aggregator.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=const_lp_1_events(),
        balances=balances,
    )
    assert events_balances == [const_lp_1_events_balance()]


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_multiple_pools_without_balances(rotkehlchen_api_server):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events = list(const_lp_1_events())
    events.extend(const_lp_2_events())
    balances: List[LiquidityPool] = []
    events_balances = rotki.chains_aggregator.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=events,
        balances=balances,
    )
    assert events_balances == [const_lp_1_events_balance(), const_lp_2_events_balance()]


@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
def test_single_pool_with_balances(rotkehlchen_api_server):
    """Test LP current balances are factorized in the pool events balance
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    events_balances = rotki.chains_aggregator.get_module('uniswap')._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=const_lp_3_events(),
        balances=[const_lp_3_balance()],
    )
    assert events_balances == [const_lp_3_events_balance()]
