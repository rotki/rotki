from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.modules.adex.adex import Adex
from rotkehlchen.chain.ethereum.modules.adex.typing import (
    TOM_POOL_ID,
    ADXStakingBalance,
    ADXStakingEvents,
    Bond,
    ChannelWithdraw,
    Unbond,
)
from rotkehlchen.constants.assets import A_ADX, A_DAI
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.typing import Timestamp

TEST_ADDR = deserialize_ethereum_address('0x494B9728BECA6C03269c38Ed86179757F77Cc0dd')
TEST_ADDR_USER_IDENTITY = deserialize_ethereum_address('0xaC29E71ACA2ff1C121673f0FC9d47e7616F692Ae')  # noqa: E501


def test_get_user_identity():
    """Test our Python port of AdEX `getUserIdentity()` works as expected.

    AdEX `getUserIdentity()`:
    https://github.com/AdExNetwork/adex-staking/blob/master/src/helpers/identity.js#L12
    """
    contract_address = Adex._get_user_identity(address=TEST_ADDR)
    assert contract_address == TEST_ADDR_USER_IDENTITY


def test_get_bond_id():
    """Test our Python port of AdEX `getBondId()` calculates the expected
    bond id using the LogBond event data.

    Bond tx (origin of `owner`, `amount`, `pool_id` and `nonce`):
    0x7944c10032e2a079d3f03ad57a90a93bde468b0baba84121be79790162215855

    Unbond tx (claiming and re-staking), its log index 283 contains the expected
    bond id:
    0xc59d65bc6c18e11a3650e8d7ec41a11f58016bbf843376c7f4cb0833402399f1

    AdEX `getBondId()`:
    https://github.com/AdExNetwork/adex-staking/blob/master/src/helpers/bonds.js#L5
    """
    expected_bond_id = '0xf1570226030766ce222ffa240231bbfc2a8de995516e63927c672b1b46c7f2c6'
    bond_id = Adex._get_bond_id(
        identity_address=TEST_ADDR_USER_IDENTITY,
        amount=10661562521452745365522,
        pool_id=TOM_POOL_ID,
        nonce=1596569185,
    )
    assert bond_id == expected_bond_id


TEST_FIX_STAKING_EVENTS = ADXStakingEvents(
    bonds=[
        Bond(
            tx_hash='1',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1604366004),
            bond_id='0x540cab9883923c01e657d5da4ca5674b6e4626b4a148224635495502d674c7c5',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            value=Balance(
                amount=FVal('100000'),
                usd_value=FVal('21345.00000'),
            ),
            nonce=1604365948,
            slashed_at=Timestamp(0),
        ),
        Bond(
            tx_hash='2',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1607453764),
            bond_id='0x16bb43690fe3764b15a2eb8d5e94e1ac13d6ef38e6c6f9d9f9c745eaff92d427',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            value=Balance(
                amount=FVal('105056.894263641728544592'),
                usd_value=FVal('29935.96202042471054878149040'),
            ),
            nonce=1604365948,
            slashed_at=Timestamp(0),
        ),
        Bond(
            tx_hash='3',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1607915796),
            bond_id='0x30bd07a0cc0c9b94e2d10487c1053fc6a5043c41fb28dcfa3ff80a68013eb501',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            value=Balance(
                amount=FVal('105843.792804312484410368'),
                usd_value=FVal('28307.92238551337395555292160'),
            ),
            nonce=1604365948,
            slashed_at=Timestamp(0),
        ),
    ],
    unbonds=[
        Unbond(
            tx_hash='2',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1607453764),
            bond_id='0x540cab9883923c01e657d5da4ca5674b6e4626b4a148224635495502d674c7c5',
            value=Balance(
                amount=FVal('100000'),
                usd_value=FVal('28495.00000'),
            ),
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
        ),
        Unbond(
            tx_hash='3',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1607915796),
            bond_id='0x16bb43690fe3764b15a2eb8d5e94e1ac13d6ef38e6c6f9d9f9c745eaff92d427',
            value=Balance(
                amount=FVal('105056.894263641728544592'),
                usd_value=FVal('28097.46637081098029925113040'),
            ),
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
        ),
    ],
    unbond_requests=[],
    channel_withdraws=[
        # From AdEx subgraph
        ChannelWithdraw(
            tx_hash='2',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1607453764),
            value=Balance(
                amount=FVal('5056.894263641728544592'),
                usd_value=FVal('1440.96202042471054878149040'),
            ),
            channel_id='0x30d87bab0ef1e7f8b4c3b894ca2beed41bbd54c481f31e5791c1e855c9dbf4ba',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            token=A_ADX,
            log_index=316,
        ),
        ChannelWithdraw(
            tx_hash='3',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1607915796),
            value=Balance(
                amount=FVal('786.898540670755865776'),
                usd_value=FVal('210.45601470239365630179120'),
            ),
            channel_id='0x30d87bab0ef1e7f8b4c3b894ca2beed41bbd54c481f31e5791c1e855c9dbf4ba',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            token=A_ADX,
            log_index=213,
        ),
        ChannelWithdraw(
            tx_hash='4',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1610322797),
            value=Balance(
                amount=FVal('1939.339070905230671011'),
                usd_value=FVal('687.59266758944953440695005'),
            ),
            channel_id='0x30d87bab0ef1e7f8b4c3b894ca2beed41bbd54c481f31e5791c1e855c9dbf4ba',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            token=A_ADX,
            log_index=130,
        ),
        # NB: missing from AdEx subgraph. Note channel_id are different
        ChannelWithdraw(
            tx_hash='4',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1610322797),
            value=Balance(
                amount=FVal('2455.145121212890626196'),
                usd_value=FVal('870.4717027260302'),
            ),
            channel_id='0xd179d5f8f09812458535f5bf271c2c5affa26329f355537e6d6246879355fcc9',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            token=A_ADX,
            log_index=124,
        ),
        ChannelWithdraw(
            tx_hash='4',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1610322797),
            value=Balance(
                amount=FVal('0.942403051800451729'),
                usd_value=FVal('0.942403051800451729'),
            ),
            channel_id='0xc18bd3ea2b0b6018ac675fc86236e304ad11cbe03e6ce31bb66417a001bd7221',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            token=A_DAI,
            log_index=126,
        ),
        ChannelWithdraw(
            tx_hash='4',
            address=TEST_ADDR,
            identity_address=TEST_ADDR_USER_IDENTITY,
            timestamp=Timestamp(1610322797),
            value=Balance(
                amount=FVal('0.221231768887185282'),
                usd_value=FVal('0.221231768887185282'),
            ),
            channel_id='0xaccd95e386de6650e222495f9f096dc926863c4f1cd786e732eca12b35807e47',
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            token=A_DAI,
            log_index=128,
        ),
    ],
)
TEST_FIX_IDENTITY_ADDRESS_MAP = {TEST_ADDR_USER_IDENTITY: TEST_ADDR}
TEST_FIX_FEE_REWARDS = [
    # DAI channel
    {
        'balances': {
            TEST_ADDR_USER_IDENTITY: '686126927577621578',
        },
        'channelArgs': {
            'tokenAddr': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'validUntil': 1640995200,
        },
        'channelId': '0x654d40ca25aa111a8259dabcc7d2073c90803b884c5177e4193c0cc313ca70c9',
    },
    # Current ADX channel
    {
        'balances': {
            TEST_ADDR: '6655456224419233586167',
        },
        'channelArgs': {
            'tokenAddr': '0xADE00C28244d5CE17D72E40330B1c318cD12B7c3',
            'validUntil': 1639440000,
        },
        'channelId': '0xd179d5f8f09812458535f5bf271c2c5affa26329f355537e6d6246879355fcc9',
    },
    # DAI channel
    {
        'balances': {
            TEST_ADDR_USER_IDENTITY: '942403051800451729',
        },
        'channelArgs': {
            'tokenAddr': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'validUntil': 1638316800,
        },
        'channelId': '0xc18bd3ea2b0b6018ac675fc86236e304ad11cbe03e6ce31bb66417a001bd7221',
    },
    # DAI channel
    {
        'balances': {
            TEST_ADDR_USER_IDENTITY: '221231768887185282',
        },
        'channelArgs': {
            'tokenAddr': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'validUntil': 1635724800,
        },
        'channelId': '0xaccd95e386de6650e222495f9f096dc926863c4f1cd786e732eca12b35807e47',
    },
    # DAI channel, user EOA/identity not in balances
    {
        'balances': {},
        'channelArgs': {
            'tokenAddr': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'validUntil': 1633046400,
        },
        'channelId': '0x261ded3a41f1c7b7a249200a8b47c9f3f820f6830e67e068fc971bd630fa6892',
    },
    # ADX channel, validUntil expired
    {
        'balances': {
            TEST_ADDR: '6655456224419233586167',
        },
        'channelArgs': {
            'tokenAddr': '0xADE00C28244d5CE17D72E40330B1c318cD12B7c3',
            'validUntil': 1612451055,  # 1s less than the frozen time of the test
        },
        'channelId': '0xd179d5f8f09812458535f5bf271c2c5affa26329f355537e6d6246879355fcc9',
    },
]
TEST_FIX_EXPECTED_ADX_STAKING_BALANCE = {
    TEST_ADDR: [
        ADXStakingBalance(
            pool_id='0x2ce0c96383fb229d9776f33846e983a956a7d95844fac57b180ed0071d93bb28',
            pool_name='Tom',
            adx_balance=Balance(
                amount=FVal('110044.103907518827370339'),
                usd_value=FVal('71368.77345690961293455124743'),
            ),
            adx_unclaimed_balance=Balance(
                amount=FVal('4200.311103206342959971'),
                usd_value=FVal('2724.099165051164107660312137'),
            ),
            dai_unclaimed_balance=Balance(
                amount=FVal('0.686126927577621578'),
                usd_value=FVal('0.686126927577621578'),
            ),
            contract_address=deserialize_ethereum_address(
                '0x4846C6837ec670Bbd1f5b485471c8f64ECB9c534',
            ),
        ),
    ],
}


@pytest.mark.freeze_time(datetime.fromtimestamp(1612451056))
def test_calculate_staking_balances():
    """Test the logic refactor works as expected as long as the subgraph returns
    all the ChannelWithdraw events, and not only the ones related with the
    legacy channel.

    Expected results:
      - ADX staked: 105843.79
      - ADX unclaimed: 4200.31
      - ADX balance: 110044.10 (staked + unclaimed)
    """
    with patch('rotkehlchen.chain.ethereum.modules.adex.adex.Graph'):
        adex = Adex(
            ethereum_manager=MagicMock(),
            database=MagicMock(),
            premium=MagicMock(),
            msg_aggregator=MagicMock(),
        )
        staking_balances = adex._calculate_staking_balances(
            staking_events=TEST_FIX_STAKING_EVENTS,
            identity_address_map=TEST_FIX_IDENTITY_ADDRESS_MAP,
            fee_rewards=TEST_FIX_FEE_REWARDS,
            adx_usd_price=FVal('0.648547'),
            dai_usd_price=FVal('1'),
        )
    assert staking_balances == TEST_FIX_EXPECTED_ADX_STAKING_BALANCE


@pytest.mark.freeze_time(datetime.fromtimestamp(1612451056))
def test_calculate_staking_balances_is_pnl_report():
    """Test that if 'is_pnl_report' argument is True, unclaimed ADX and DAI amounts are
    not calculated and set to 0.
    """
    with patch('rotkehlchen.chain.ethereum.modules.adex.adex.Graph'):
        adex = Adex(
            ethereum_manager=MagicMock(),
            database=MagicMock(),
            premium=MagicMock(),
            msg_aggregator=MagicMock(),
        )
        staking_balances = adex._calculate_staking_balances(
            staking_events=TEST_FIX_STAKING_EVENTS,
            identity_address_map=TEST_FIX_IDENTITY_ADDRESS_MAP,
            fee_rewards=TEST_FIX_FEE_REWARDS,
            adx_usd_price=FVal('0.648547'),
            dai_usd_price=FVal('1'),
            is_pnl_report=True,
        )

    staking_balance = staking_balances[TEST_ADDR][0]
    assert staking_balance.adx_balance == Balance(
        amount=FVal('105843.792804312484410368'),
        usd_value=FVal('68644.67429185844882689093530'),
    )
    assert staking_balance.adx_unclaimed_balance == Balance()
    assert staking_balance.dai_unclaimed_balance == Balance()
