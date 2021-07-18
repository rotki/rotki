from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.structures import (
    AaveBorrowEvent,
    AaveDepositWithdrawalEvent,
    AaveInterestEvent,
    AaveLiquidationEvent,
    AaveRepayEvent,
)
from rotkehlchen.constants.assets import (
    A_ADAI_V1,
    A_AWBTC_V1,
    A_BUSD,
    A_DAI,
    A_ETH,
    A_WBTC,
    A_LINK,
    A_ALINK_V1,
    A_USDT,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.constants import A_ADAI
from rotkehlchen.typing import Timestamp

AAVE_TEST_ACC_1 = '0x21d05071cA08593e13cd3aFD0b4869537e015C92'
AAVE_TEST_ACC_2 = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'
AAVE_TEST_ACC_3 = '0xbA215F7BE6c620dA3F8240B82741eaF3C5f5D786'

aave_mocked_historical_prices = {
    A_ADAI_V1: {  # aDAI
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
    A_DAI: {  # DAI
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
aave_mocked_current_prices = {A_ADAI_V1: FVal('1.017')}

expected_aave_deposit_test_events = [
    AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('102.926986169186236436'),
            usd_value=FVal('104.367963975554843746104'),
        ),
        block_number=9963767,
        timestamp=Timestamp(1588114293),
        tx_hash='0x8b72307967c4f7a486c1cb1b6ebca5e549de06e02930ece0399e2096f1a132c5',
        log_index=72,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('160'),
            usd_value=FVal('161.440'),
        ),
        block_number=9987395,
        timestamp=Timestamp(1588430911),
        tx_hash='0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
        log_index=146,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('0.037901731034995483'),
            usd_value=FVal('0.038242846614310442347'),
        ),
        block_number=9987395,
        timestamp=Timestamp(1588430911),
        tx_hash='0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
        log_index=142,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('390'),
            usd_value=FVal('393.510'),
        ),
        block_number=9989872,
        timestamp=Timestamp(1588463542),
        tx_hash='0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
        log_index=157,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('0.013768655195843925'),
            usd_value=FVal('0.013892573092606520325'),
        ),
        block_number=9989872,
        timestamp=Timestamp(1588463542),
        tx_hash='0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
        log_index=153,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('58.985239852398524415'),
            usd_value=FVal('59.398136531365314085905'),
        ),
        block_number=10041636,
        timestamp=Timestamp(1589155650),
        tx_hash='0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
        log_index=35,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('0.598140134217201945'),
            usd_value=FVal('0.602327115156722358615'),
        ),
        block_number=10041636,
        timestamp=Timestamp(1589155650),
        tx_hash='0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
        log_index=31,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('1.13704264707898858'),
            usd_value=FVal('1.14045377502022554574'),
        ),
        block_number=10160566,
        timestamp=Timestamp(1590753905),
        tx_hash='0x07ac09cc06c7cd74c7312f3a82c9f77d69ba7a89a4a3b7ded33db07e32c3607c',
        log_index=152,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('168.84093462143338681'),
            usd_value=FVal('171.03586677151202083853'),
        ),
        block_number=10266740,
        timestamp=Timestamp(1592175763),
        tx_hash='0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
        log_index=82,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('3.948991286917379003'),
            usd_value=FVal('4.000328173647304930039'),
        ),
        block_number=10266740,
        timestamp=Timestamp(1592175763),
        tx_hash='0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
        log_index=78,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('1939.840878392183347402'),
            usd_value=FVal('1976.697855081634831002638'),
        ),
        block_number=10440633,
        timestamp=Timestamp(1594502373),
        tx_hash='0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41',
        log_index=104,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('27.824509817913242961'),
            usd_value=FVal('28.353175504453594577259'),
        ),
        block_number=10440633,
        timestamp=Timestamp(1594502373),
        tx_hash='0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41',
        log_index=100,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('2507.675873220870275072'),
            usd_value=FVal('2507.675873220870275072'),
        ),
        block_number=10505913,
        timestamp=Timestamp(1595376667),
        tx_hash='0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410',
        log_index=96,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('17.91499070977557364'),
            usd_value=FVal('17.91499070977557364'),
        ),
        block_number=10505913,
        timestamp=Timestamp(1595376667),
        tx_hash='0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410',
        log_index=92,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ADAI,
        value=Balance(
            amount=FVal('88.663672238882760399'),
            usd_value=FVal('88.663672238882760399'),
        ),
        block_number=10718983,
        timestamp=Timestamp(1598217272),
        tx_hash='0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486',
        log_index=97,
    ), AaveDepositWithdrawalEvent(
        event_type='withdrawal',
        asset=A_DAI,
        atoken=A_ADAI_V1,
        value=Balance(
            amount=FVal('7968.408929477087756071'),
            usd_value=FVal('7968.408929477087756071'),
        ),
        block_number=10718983,
        timestamp=Timestamp(1598217272),
        tx_hash='0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486',
        log_index=102,
    ),
]

expected_aave_liquidation_test_events = [
    AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_WBTC,
        atoken=A_AWBTC_V1,
        value=Balance(
            amount=FVal('1.11'),
            usd_value=FVal('1.11'),
        ),
        block_number=0,
        timestamp=Timestamp(1598799955),
        tx_hash='0x400b21334279498fc5b7ff469fec0c5e94620001104f18267c796497a7260ada',
        log_index=1,
    ), AaveBorrowEvent(
        event_type='borrow',
        asset=A_ETH,
        value=Balance(
            amount=FVal('18.5'),
            usd_value=FVal('18.5'),
        ),
        block_number=0,
        timestamp=Timestamp(1598800092),
        tx_hash='0x819cdd20760ab68bc7bf9343cb2e5552ab512dcf071afe1c3995a07a379f0961',
        log_index=2,
        borrow_rate_mode='variable',
        borrow_rate=FVal('0.018558721449222331635565398'),
        accrued_borrow_interest=ZERO,
    ), AaveLiquidationEvent(
        event_type='liquidation',
        collateral_asset=A_WBTC,
        collateral_balance=Balance(
            amount=FVal('0.41590034'),
            usd_value=FVal('0.41590034'),
        ),
        principal_asset=A_ETH,
        principal_balance=Balance(
            amount=FVal('9.251070299427409111'),
            usd_value=FVal('9.251070299427409111'),
        ),
        block_number=0,
        timestamp=Timestamp(1598941756),
        tx_hash='0x00eea6359d247c9433d32620358555a0fd3265378ff146b9511b7cff1ecb7829',
        log_index=8,
    ), AaveRepayEvent(
        event_type='repay',
        asset=A_ETH,
        value=Balance(
            amount=FVal('3.665850591343088034'),
            usd_value=FVal('3.665850591343088034'),
        ),
        fee=Balance(amount=ZERO, usd_value=ZERO),
        block_number=0,
        timestamp=Timestamp(1599023196),
        tx_hash='0xb30831fcc5f02e551befa6238839354e602b0a351cdf77eb170c29427c326304',
        log_index=4,
    ), AaveRepayEvent(
        event_type='repay',
        asset=A_ETH,
        value=Balance(
            amount=FVal('5.587531295588010728'),
            usd_value=FVal('5.587531295588010728'),
        ),
        fee=Balance(amount=ZERO, usd_value=ZERO),
        block_number=0,
        timestamp=Timestamp(1599401677),
        tx_hash='0xefde39a330215fb189b70e9964b4f7d8cd6f1335c5994899dd04de7a1b30b3aa',
        log_index=4,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_AWBTC_V1,
        value=Balance(
            amount=FVal('0.00000833'),
            usd_value=FVal('0.00000833'),
        ),
        block_number=0,
        timestamp=Timestamp(1599401782),
        tx_hash='0x54eee67a3f1e114d102ea76d69298636caf717e19c1b910264d955c4ba942905',
        log_index=4,
    ), AaveDepositWithdrawalEvent(
        event_type='withdrawal',
        asset=A_WBTC,
        atoken=A_AWBTC_V1,
        value=Balance(
            amount=FVal('0.69410968'),
            usd_value=FVal('0.69410968'),
        ),
        block_number=0,
        timestamp=Timestamp(1599401782),
        tx_hash='0x54eee67a3f1e114d102ea76d69298636caf717e19c1b910264d955c4ba942905',
        log_index=3,
    ), AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_WBTC,
        atoken=A_AWBTC_V1,
        value=Balance(
            amount=FVal('1.47386645'),
            usd_value=FVal('1.47386645'),
        ),
        block_number=0,
        timestamp=Timestamp(1601394794),
        tx_hash='0x70ca1f4a64bd2be9bff8a6d42e333e89f855a9fec2df643b76fe9401c2b1867c',
        log_index=1,
    ), AaveBorrowEvent(
        event_type='borrow',
        asset=A_BUSD,
        value=Balance(
            amount=FVal('5000'),
            usd_value=FVal('5000'),
        ),
        block_number=0,
        timestamp=Timestamp(1601398506),
        tx_hash='0xb59ff2759b37da52537f43aaa5cbce3bcab77ef208cba80e22086610323c2a17',
        log_index=2,
        borrow_rate_mode='variable',
        borrow_rate=FVal('0.048662000571241866099699838'),
        accrued_borrow_interest=ZERO,
    ),
]

expected_aave_v2_events = [
    AaveDepositWithdrawalEvent(
        event_type='deposit',
        asset=A_LINK,
        atoken=A_ALINK_V1,
        value=Balance(
            amount=FVal('12629.998670888732814733'),
            usd_value=FVal('12629.998670888732814733'),
        ),
        block_number=0,
        timestamp=Timestamp(1615333105),
        tx_hash='0x75444c0ae48700f388d05ec8380b3922c4daf1e8eef2476001437b68d36f56a1',
        log_index=1,
    ), AaveBorrowEvent(
        event_type='borrow',
        asset=A_USDT,
        value=Balance(
            amount=FVal('100000'),
            usd_value=FVal('100000'),
        ),
        block_number=0,
        timestamp=Timestamp(1615333284),
        tx_hash='0x74e8781fd86e81a87a4ba93bc7755d4a94901765cd72399f0372d36e7a26a03a',
        log_index=2,
        borrow_rate_mode='stable',
        borrow_rate=FVal('0.088712770921360153608109216'),
        accrued_borrow_interest=ZERO,
    ), AaveRepayEvent(
        event_type='repay',
        asset=A_USDT,
        value=Balance(
            amount=FVal('100071.409221'),
            usd_value=FVal('100071.409221'),
        ),
        fee=Balance(amount=ZERO, usd_value=ZERO),
        block_number=0,
        timestamp=Timestamp(1615587042),
        tx_hash='0x164e3eafef02ac1a956ba3c7d027506d47de36b34daee1e05ca0d178413911c1',
        log_index=4,
    ), AaveInterestEvent(
        event_type='interest',
        asset=A_ALINK_V1,
        value=Balance(
            amount=FVal('0.092486713379308309'),
            usd_value=FVal('0.092486713379308309'),
        ),
        block_number=0,
        timestamp=Timestamp(1615669328),
        tx_hash='0xfeee61357d43e79a2beae9edab860c30db9765964be26eff82c6834d4e2c2db7',
        log_index=4,
    ), AaveDepositWithdrawalEvent(
        event_type='withdrawal',
        asset=A_LINK,
        atoken=A_ALINK_V1,
        value=Balance(
            amount=FVal('12630.091157602112123042'),
            usd_value=FVal('12630.091157602112123042'),
        ),
        block_number=0,
        timestamp=Timestamp(1615669328),
        tx_hash='0xfeee61357d43e79a2beae9edab860c30db9765964be26eff82c6834d4e2c2db7',
        log_index=3,
    ),
]
