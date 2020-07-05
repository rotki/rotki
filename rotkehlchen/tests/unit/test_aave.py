import pytest

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.aave import Aave, AaveEvent
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
        AaveEvent(
            event_type='deposit',
            value=Balance(
                amount=FVal('102.926986169186236436'),
                usd_value=FVal('104.367963975554843746104'),
            ),
            block_number=9963767,
            timestamp=1588114293,
            tx_hash='0x8b72307967c4f7a486c1cb1b6ebca5e549de06e02930ece0399e2096f1a132c5',
        ), AaveEvent(
            event_type='deposit',
            value=Balance(
                amount=FVal('160'),
                usd_value=FVal('161.440'),
            ),
            block_number=9987395,
            timestamp=1588430911,
            tx_hash='0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
        ), AaveEvent(
            event_type='interest',
            value=Balance(
                amount=FVal('0.037901731034995483'),
                usd_value=FVal('0.038242846614310442347'),
            ),
            block_number=9987395,
            timestamp=1588430911,
            tx_hash='0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
        ), AaveEvent(
            event_type='deposit',
            value=Balance(
                amount=FVal('390'),
                usd_value=FVal('393.510'),
            ),
            block_number=9989872,
            timestamp=1588463542,
            tx_hash='0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
        ), AaveEvent(
            event_type='interest',
            value=Balance(
                amount=FVal('0.013768655195843925'),
                usd_value=FVal('0.013892573092606520325'),
            ),
            block_number=9989872,
            timestamp=1588463542,
            tx_hash='0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
        ), AaveEvent(
            event_type='deposit',
            value=Balance(
                amount=FVal('58.985239852398524415'),
                usd_value=FVal('59.398136531365314085905'),
            ),
            block_number=10041636,
            timestamp=1589155650,
            tx_hash='0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
        ), AaveEvent(
            event_type='interest',
            value=Balance(
                amount=FVal('0.598140134217201945'),
                usd_value=FVal('0.602327115156722358615'),
            ),
            block_number=10041636,
            timestamp=1589155650,
            tx_hash='0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
        ), AaveEvent(
            event_type='interest',
            value=Balance(
                amount=FVal('1.13704264707898858'),
                usd_value=FVal('1.14045377502022554574'),
            ),
            block_number=10160566,
            timestamp=1590753905,
            tx_hash='0x07ac09cc06c7cd74c7312f3a82c9f77d69ba7a89a4a3b7ded33db07e32c3607c',
        ), AaveEvent(
            event_type='deposit',
            value=Balance(
                amount=FVal('168.84093462143338681'),
                usd_value=FVal('171.03586677151202083853'),
            ),
            block_number=10266740,
            timestamp=1592175763,
            tx_hash='0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
        ), AaveEvent(
            event_type='interest',
            value=Balance(
                amount=FVal('3.948991286917379003'),
                usd_value=FVal('4.000328173647304930039'),
            ),
            block_number=10266740,
            timestamp=1592175763,
            tx_hash='0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
        ),
    ]
    assert len(profit_map) == 1
    assert profit_map['aDAI'].events == expected_events
    # comparison is greater than since interest is always accruing since writing the test
    assert profit_map['aDAI'].total_earned.amount >= FVal('24.207179802347627414')
    assert profit_map['aDAI'].total_earned.usd_value >= FVal('24.580592532348742989192')
