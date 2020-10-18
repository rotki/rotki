import pytest

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.aave import Aave
from rotkehlchen.chain.ethereum.aave.common import AAVE_RESERVE_TO_ASSET, ATOKEN_TO_DEPLOYED_BLOCK
from rotkehlchen.constants.ethereum import AAVE_ETH_RESERVE_ADDRESS
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium
from rotkehlchen.tests.utils.aave import (
    AAVE_TEST_ACC_2,
    aave_mocked_current_prices,
    aave_mocked_historical_prices,
    expected_aave_deposit_test_events,
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
        user_address=AAVE_TEST_ACC_2,
        to_block=10386830,  # test was written at this block
        atokens_list=[EthereumToken('aDAI')],
    )

    assert history.events == expected_aave_deposit_test_events[:10]
    assert len(history.total_earned) == 1
    # comparison is greater than since interest is always accruing since writing the test
    # and 5.6 "should be" the principal balance at the given block
    assert history.total_earned['aDAI'].amount >= FVal('5.6')
    assert history.total_earned['aDAI'].usd_value >= FVal('5.6')


def test_aave_reserve_mapping():
    assert len(ATOKEN_TO_DEPLOYED_BLOCK) == len(AAVE_RESERVE_TO_ASSET)
    for address, asset in AAVE_RESERVE_TO_ASSET.items():
        if address == AAVE_ETH_RESERVE_ADDRESS:
            continue

        msg = f'Wrong address for {asset.symbol}. Expected {asset.ethereum_address} got {address}'
        assert address == asset.ethereum_address, msg
