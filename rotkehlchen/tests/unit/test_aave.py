import pytest

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.aave import Aave, AaveInterestPayment
from rotkehlchen.fval import FVal
from rotkehlchen.premium.premium import Premium


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


mocked_historical_prices = {
    'aDAI': {
        'USD': {
            1589155650: FVal('1.007'),
            1590753905: FVal('1.003'),
            1588114293: FVal('1.014'),
            1588463542: FVal('1.009'),
            1588430911: FVal('1.009'),
            1592175763: FVal('1.013'),
        },
    },
}
mocked_current_prices = {'aDAI': FVal('1.017')}


@pytest.mark.parametrize('mocked_price_queries', [mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [mocked_current_prices])
def test_get_lending_profit_for_address(aave, price_historian):  # pylint: disable=unused-argument
    profit_map = aave.get_lending_profit_for_address(
        user_address='0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
        atokens_list=[EthereumToken('aDAI')],
        given_to_block=10386830,  # test was written at this block
    )

    expected_events = [
        AaveInterestPayment(
            balance=Balance(
                amount=FVal('0.037901731034995483'),
                usd_value=FVal('0.038242846614310442347'),
            ),
            block_number=9987395,
            timestamp=1588430911,
        ), AaveInterestPayment(
            balance=Balance(
                amount=FVal('0.013768655195843925'),
                usd_value=FVal('0.013892573092606520325'),
            ),
            block_number=9989872,
            timestamp=1588463542,
        ), AaveInterestPayment(
            balance=Balance(
                amount=FVal('0.598140134217201945'),
                usd_value=FVal('0.602327115156722358615'),
            ),
            block_number=10041636,
            timestamp=1589155650,
        ), AaveInterestPayment(
            balance=Balance(
                amount=FVal('1.13704264707898858'),
                usd_value=FVal('1.14045377502022554574'),
            ),
            block_number=10160566,
            timestamp=1590753905,
        ), AaveInterestPayment(
            balance=Balance(
                amount=FVal('3.948991286917379003'),
                usd_value=FVal('4.000328173647304930039'),
            ),
            block_number=10266740,
            timestamp=1592175763,
        ),
    ]
    assert len(profit_map) == 1
    assert profit_map['aDAI'].events == expected_events
    # comparison is greater than since interest is always accruing since writing the test
    assert profit_map['aDAI'].total_earned.amount >= FVal('14.639592665598308240')
    assert profit_map['aDAI'].total_earned.usd_value >= FVal('14.855619384119985440682')
