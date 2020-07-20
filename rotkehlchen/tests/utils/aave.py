from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.aave import AaveEvent
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_ADAI
from rotkehlchen.typing import Timestamp

aave_mocked_historical_prices = {
    'aDAI': {
        'USD': {
            1589155650: FVal('1.007'),
            1590753905: FVal('1.003'),
            1588114293: FVal('1.014'),
            1588463542: FVal('1.009'),
            1588430911: FVal('1.009'),
            1592175763: FVal('1.013'),
            1594502373: FVal('1.019'),
        },
    },
    'DAI': {
        'USD': {
            1589155650: FVal('1.007'),
            1590753905: FVal('1.003'),
            1588114293: FVal('1.014'),
            1588463542: FVal('1.009'),
            1588430911: FVal('1.009'),
            1592175763: FVal('1.013'),
            1594502373: FVal('1.019'),
        },
    },
}
aave_mocked_current_prices = {'aDAI': FVal('1.017')}

expected_aave_test_events = [
    AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(
            amount=FVal('102.926986169186236436'),
            usd_value=FVal('104.367963975554843746104'),
        ),
        block_number=9963767,
        timestamp=Timestamp(1588114293),
        tx_hash='0x8b72307967c4f7a486c1cb1b6ebca5e549de06e02930ece0399e2096f1a132c5',
        log_index=0,
    ), AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(
            amount=FVal('160'),
            usd_value=FVal('161.440'),
        ),
        block_number=9987395,
        timestamp=Timestamp(1588430911),
        tx_hash='0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
        log_index=0,
    ), AaveEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('0.037901731034995483'),
            usd_value=FVal('0.038242846614310442347'),
        ),
        block_number=9987395,
        timestamp=Timestamp(1588430911),
        tx_hash='0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
        log_index=0,
    ), AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(
            amount=FVal('390'),
            usd_value=FVal('393.510'),
        ),
        block_number=9989872,
        timestamp=Timestamp(1588463542),
        tx_hash='0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
        log_index=0,
    ), AaveEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('0.013768655195843925'),
            usd_value=FVal('0.013892573092606520325'),
        ),
        block_number=9989872,
        timestamp=Timestamp(1588463542),
        tx_hash='0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
        log_index=0,
    ), AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(
            amount=FVal('58.985239852398524415'),
            usd_value=FVal('59.398136531365314085905'),
        ),
        block_number=10041636,
        timestamp=Timestamp(1589155650),
        tx_hash='0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
        log_index=0,
    ), AaveEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('0.598140134217201945'),
            usd_value=FVal('0.602327115156722358615'),
        ),
        block_number=10041636,
        timestamp=Timestamp(1589155650),
        tx_hash='0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
        log_index=0,
    ), AaveEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('1.13704264707898858'),
            usd_value=FVal('1.14045377502022554574'),
        ),
        block_number=10160566,
        timestamp=Timestamp(1590753905),
        tx_hash='0x07ac09cc06c7cd74c7312f3a82c9f77d69ba7a89a4a3b7ded33db07e32c3607c',
        log_index=0,
    ), AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(
            amount=FVal('168.84093462143338681'),
            usd_value=FVal('171.03586677151202083853'),
        ),
        block_number=10266740,
        timestamp=Timestamp(1592175763),
        tx_hash='0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
        log_index=0,
    ), AaveEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('3.948991286917379003'),
            usd_value=FVal('4.000328173647304930039'),
        ),
        block_number=10266740,
        timestamp=Timestamp(1592175763),
        tx_hash='0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
        log_index=0,
    ), AaveEvent(
        event_type='deposit',
        asset=A_DAI,
        value=Balance(
            amount=FVal('1939.840878392183347402'),
            usd_value=FVal('1976.697855081634831002638'),
        ),
        block_number=10440633,
        timestamp=Timestamp(1594502373),
        tx_hash='0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41',
        log_index=0,
    ), AaveEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('27.824509817913242961'),
            usd_value=FVal('28.353175504453594577259'),
        ),
        block_number=10440633,
        timestamp=Timestamp(1594502373),
        tx_hash='0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41',
        log_index=0,
    ),
]
