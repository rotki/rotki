import pytest

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.aave import Aave
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.aave import (
    aave_mocked_current_prices,
    aave_mocked_historical_prices,
    expected_aave_test_events,
)


@pytest.fixture
def aave(
        ethereum_manager,
        database,
        function_scope_messages_aggregator,
        start_with_valid_premium,
        rotki_premium_credentials,
):
    premium = None
    if start_with_valid_premium:
        premium = Premium(rotki_premium_credentials)

    aave = Aave(
        ethereum_manager=ethereum_manager,
        database=database,
        premium=premium,
        msg_aggregator=function_scope_messages_aggregator,
    )
    return aave


@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
def test_get_lending_profit_for_address(aave, price_historian):  # pylint: disable=unused-argument
    history = aave.get_history_for_address(
        user_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        atokens_list=[EthereumToken('aDAI')],
        given_to_block=10386830,  # test was written at this block
    )

    assert history.events == expected_aave_test_events[:10]
    assert len(history.total_earned) == 1
    # comparison is greater than since interest is always accruing since writing the test
    # and 7 "should be" the principal balance at the given block
    assert history.total_earned['aDAI'].amount >= FVal('7')
    assert history.total_earned['aDAI'].usd_value >= FVal('7')
