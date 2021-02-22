from typing import List

from rotkehlchen.chain.ethereum.modules.uniswap.typing import LiquidityPool, LiquidityPoolEvent
from rotkehlchen.chain.ethereum.modules.uniswap.uniswap import Uniswap

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


def test_no_events_no_balances():
    events: List[LiquidityPoolEvent] = []
    balances: List[LiquidityPool] = []
    events_balances = Uniswap._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=events,
        balances=balances,
    )
    assert events_balances == []


def test_single_pool_without_balances():
    balances: List[LiquidityPool] = []
    events_balances = Uniswap._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=LP_1_EVENTS,
        balances=balances,
    )
    assert events_balances == [LP_1_EVENTS_BALANCE]


def test_multiple_pools_without_balances():
    events = list(LP_1_EVENTS)
    events.extend(LP_2_EVENTS)
    balances: List[LiquidityPool] = []
    events_balances = Uniswap._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=events,
        balances=balances,
    )
    assert events_balances == [LP_1_EVENTS_BALANCE, LP_2_EVENTS_BALANCE]


def test_single_pool_with_balances():
    """Test LP current balances are factorized in the pool events balance
    """
    events_balances = Uniswap._calculate_events_balances(
        address=TEST_ADDRESS_1,
        events=LP_3_EVENTS,
        balances=[LP_3_BALANCE],
    )
    assert events_balances == [LP_3_EVENTS_BALANCE]
