from contextlib import ExitStack
from datetime import datetime
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.eth2.eth2 import REQUEST_DELTA_TS
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    Eth2Deposit,
    Eth2Validator,
    ValidatorDailyStats,
)
from rotkehlchen.chain.ethereum.modules.eth2.utils import scrape_validator_daily_stats
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

ADDR1 = string_to_evm_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
ADDR2 = string_to_evm_address('0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19')
ADDR3 = string_to_evm_address('0x3266F3546a1e5Dc6A15588f3324741A0E20a3B6c')

# List of ADDR1, ADDR2 and ADDR3 deposit events from 1604506685 to 1605044577
# sorted by (timestamp, log_index).
EXPECTED_DEPOSITS = [
    Eth2Deposit(
        from_address=ADDR1,
        pubkey='0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
        withdrawal_credentials='0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1'),  # noqa: E501
        tx_index=15,
        timestamp=Timestamp(int(1604506685)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x90b2f65cb43d9cdb2279af9f76010d667b9d8d72e908f2515497a7102820ce6bb15302fe2b8dc082fce9718569344ad8',  # noqa: E501
        withdrawal_credentials='0x00a257d19e1650dec1ab59fc9e1cb9a9fc2fe7265b0f27e7d79ff61aeff0a1f0',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x3403bd94a1bf185ee18a525499e408a1b9b7d801cff6418e31efda346762e754'),  # noqa: E501
        tx_index=105,
        timestamp=Timestamp(int(1604611131)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb4610a24815f1874a12eba7ea9b77126ca16c0aa29a127ba14ba4ee179834f4feb0aa4497baaa50985ad748d15a286cf',  # noqa: E501
        withdrawal_credentials='0x00f7ce43bfb18009abe0e8e5b3a8c0da3c014bc80e4a0a8dccda647f48ea8547',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x89b3b87c8841950893a4752ab03cbb835a1b5593a5d68cd343663824bf2d311e'),  # noqa: E501
        tx_index=57,
        timestamp=Timestamp(int(1604611169)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xa96352b921bcc4b1a90a7aeb68739b6a5508079a63158ca84786241da247142173f9b38d553de899c1778de4f83e6c6c',  # noqa: E501
        withdrawal_credentials='0x0062a11c0395b8379bff5310398be82ee6d950d397899f7d39751d5721c01d9e',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x1a228f3421f5b18904c92a21690b188d05a47bfbcfbe2175cbfdf27e2cd6ea53'),  # noqa: E501
        tx_index=25,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x911cba78efe677a502a3995060e2389e2d16d03f989c87f1a0fdf82345a77dfd3b9476720825ea5f5a374bd386301b60',  # noqa: E501
        withdrawal_credentials='0x0007b5cf7558a6ee86d2dbf69227dfee28783d36fc6d18b30bda7ffc385fe27a',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xae84e32268d21ca03559d03abc769eaeaff2409ce282e7a1b9a3015a9cdb9357'),  # noqa: E501
        tx_index=26,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35',  # noqa: E501
        withdrawal_credentials='0x00c988827cb5ce8a4a33e67bf5e61457949d9935cd21d44e15d5751c91a2c177',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x7cb53c523001273ada3623edfdc32838683b3820589be2a450b1d527e8851070'),  # noqa: E501
        tx_index=27,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x89da8cb17b203eefacc8346e1ee718a305b622028dc77913d3b26f2034f92693d305a630f45c76b781ef68cd4640253e',  # noqa: E501
        withdrawal_credentials='0x00df23e0483e4b77609b849368b6f84cc5b0a55bd7bcd95374ed1a59cc73fc28',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xf2174fbaaf45204a178652ce28567d398a8afb3699b5bd34b5bbb7b33a3b8c34'),  # noqa: E501
        tx_index=28,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x930a90c7f0b00ce4c7d7994652f1e301753c084d5499de31abadb2e3913cba2eb4026de8d49ea35294db10119b83b2e1',  # noqa: E501
        withdrawal_credentials='0x00b522800f977a14d8eae22d675d241b53807c6d75ba1e180f8ac52d9600322c',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x187bef85f7797f4f42534fcfa080ed28ab77491b79fe9e9be8039416eebab6bc'),  # noqa: E501
        tx_index=29,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb18e1737e1a1a76b8dff905ba7a4cb1ff5c526a4b7b0788188aade0488274c91e9c797e75f0f8452384ff53d44fad3df',  # noqa: E501
        withdrawal_credentials='0x000c0efd86dba58898debd8e80fa1d7d88bc2b7b1237d32485b2c9101edba203',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xcb929eb5425743eb039edd03495a53141643f8e341483d7c8319d55a746a3e7d'),  # noqa: E501
        tx_index=178,
        timestamp=Timestamp(int(1604612368)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x976c5c76f3cbc10d22ac50c27f816b82d91192f6b6177857a89a0349fcecaa8301469ab1d303e381e630c591456e0e54',  # noqa: E501
        withdrawal_credentials='0x00cd586bed9443813cf4778a71224ceaef520419afc803fd720a0f4b068ee839',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x64a66740ae4cf64e8735271f94fa9c763e9a68c506292671041301196f6f2d70'),  # noqa: E501
        tx_index=91,
        timestamp=Timestamp(int(1604641797)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x85a82370ef68f52209d3a07f5cca32b0bbe4d2d39574f39beab746d54e696831a02a95f3dcea25f1fba766bdb5048a09',  # noqa: E501
        withdrawal_credentials='0x007e6a2f6fa852677aa4239cc753240421993f931feeab37c5d654739ea30bfc',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xccd2ddb9827a39bb30fd1a2166f40d2d571feab375e0d6469ba749d86e3f4e0b'),  # noqa: E501
        tx_index=190,
        timestamp=Timestamp(int(1604641801)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb347f7421cec107e1cdf3ae9b6308c577fc6c1c254fa44552be97db3eccdac667dc6d6e5409f8e546c9dcbcef47c83f3',  # noqa: E501
        withdrawal_credentials='0x00477a22f13287589a64ee40b8674a43c4fbf381e2e842b9814dfc4f75c7a10c',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x721a69c5bd3b697827eabd44d7176e95ba803a462d99e74f62299111e8c516b1'),  # noqa: E501
        tx_index=198,
        timestamp=Timestamp(int(1604641801)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x965f40c2a6f004d4457a89e7b49ea5d101367cd31c86836d6551ea504e55ee3e32aed8b2615ee1c13212db46fb411a7a',  # noqa: E501
        withdrawal_credentials='0x006483a6a77c286cdc1711d67631244a2d4441babca4fd82acef4bb6c6be5a50',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xedf5930af6dd9efd54787d57acb250aff72ecb9a697b4abefa87274035343787'),  # noqa: E501
        tx_index=13,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x90d4b57b88eb613737c1bb2e79f8ed8f2abd1c5e31cea9aa741f16cb777716d2fc1cabf9e15d3c15edf8091533916eb5',  # noqa: E501
        withdrawal_credentials='0x00cd969a3cfd32e0db1b11041e53e971961ff9500e1deaf7d8ebb3bbe0de540c',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x92f90a1271a184e1c5ee1e468f391bab5749108effb2c57a49f2cef153f9bc58'),  # noqa: E501
        tx_index=25,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x92a5d445d10ce8d413c506a012ef92719ca230ab0fd4066e2968df8adb52bb112ee080a3267f282f09db94dc59a3ec77',  # noqa: E501
        withdrawal_credentials='0x001badfb8f47cd4650788335cd314f6aa4be2350fe2313d2a7add27e63535d3a',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x7c2f5f1ade5b7df58eebbe3c76b8cb038936e0f7fb4479ab5ac9df7a6f0fbd41'),  # noqa: E501
        tx_index=31,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb44383a9ce75b90cc8248bdd46d02a2a309117bbfdbe9fd05743def6d483549072c3285ae4953f48b1d17c9787697764',  # noqa: E501
        withdrawal_credentials='0x00c45ca431dfbe790525de640d928e0dfdd9c08e93a69482a3c2adedb379d874',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x5722e35df3387aa21c825b0d8ddea3cf168d421a31edfe63c73ffc028df2a4f1'),  # noqa: E501
        tx_index=39,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR2,
        pubkey='0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
        withdrawal_credentials='0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7'),  # noqa: E501
        tx_index=125,
        timestamp=Timestamp(int(1605043544)),
    ),
    Eth2Deposit(
        from_address=ADDR2,
        pubkey='0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475',  # noqa: E501
        withdrawal_credentials='0x0082add39f581048857972a9bac9ae5f5c42b23c947281e4ca30953386c866ed',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        tx_hash=deserialize_evm_tx_hash('0xc114753fb5d11a94a95dd980cff9f26693632550de56b5291201774686ddba3f'),  # noqa: E501
        tx_index=52,
        timestamp=Timestamp(int(1605044577)),
    ),
]


@pytest.mark.freeze_time(datetime(2020, 11, 10, 21, 42, 57))
@pytest.mark.parametrize('default_mock_price_value', [FVal(2)])
def test_get_eth2_staking_deposits(  # pylint: disable=unused-argument
        price_historian,
        eth2,
):
    """Test retrieval of eth2 staking deposits"""
    deposits = eth2.get_staking_deposits(
        addresses=[ADDR1, ADDR2, ADDR3],
    )
    assert len(deposits) >= len(EXPECTED_DEPOSITS)

    for idx, expected_deposit in enumerate(EXPECTED_DEPOSITS):
        assert expected_deposit == deposits[idx]

    total_addr1 = sum(
        deposit.value.amount for deposit in EXPECTED_DEPOSITS if deposit.from_address == ADDR1
    )
    total_addr2 = sum(
        deposit.value.amount for deposit in EXPECTED_DEPOSITS if deposit.from_address == ADDR2
    )
    total_addr3 = sum(
        deposit.value.amount for deposit in EXPECTED_DEPOSITS if deposit.from_address == ADDR3
    )

    assert total_addr1 == FVal(32)
    assert total_addr2 == FVal(64)
    assert total_addr3 == FVal(480)


@pytest.mark.parametrize('default_mock_price_value', [FVal(2)])
def test_get_eth2_staking_deposits_fetch_from_db(  # pylint: disable=unused-argument
        price_historian,
        freezer,
        eth2,
):
    """
    Test new on-chain requests for existing addresses requires a difference of
    REQUEST_DELTA_TS since last used query range `end_ts`.
    """
    start_ts = 1604506685
    freezer.move_to(datetime.fromtimestamp(start_ts))
    get_deposits_patch = patch.object(
        eth2.beaconchain, 'get_validator_deposits', wraps=eth2.beaconchain.get_validator_deposits,  # noqa: E501
    )
    get_address_validator_patch = patch.object(
        eth2.beaconchain, 'get_eth1_address_validators', wraps=eth2.beaconchain.get_eth1_address_validators,  # noqa: E501
    )

    with ExitStack() as stack:
        get_deposits_patch = stack.enter_context(get_deposits_patch)
        get_address_validator_patch = stack.enter_context(get_address_validator_patch)
        eth2.get_staking_deposits([ADDR1])
        assert get_address_validator_patch.call_count == 1
        get_address_validator_patch.assert_called_with(ADDR1)
        assert get_deposits_patch.call_count == 1
        get_deposits_patch.assert_called_with(['0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'])  # noqa: E501

        # NB: Move time to ts_now + REQUEST_DELTA_TS - 2
        freezer.move_to(datetime.fromtimestamp(start_ts + REQUEST_DELTA_TS - 2))
        eth2.get_staking_deposits([ADDR1])
        assert get_address_validator_patch.call_count == 1
        assert get_deposits_patch.call_count == 2
        get_deposits_patch.assert_called_with([])  # noqa: E501

        # NB: Move time to ts_now + REQUEST_DELTA_TS + 2
        freezer.move_to(datetime.fromtimestamp(start_ts + REQUEST_DELTA_TS + 2))
        eth2.get_staking_deposits([ADDR1])
        assert get_address_validator_patch.call_count == 2
        get_address_validator_patch.assert_called_with(ADDR1)
        assert get_deposits_patch.call_count == 3
        get_deposits_patch.assert_called_with([])  # noqa: E501


def test_eth2_deposits_serialization():
    addr1 = make_ethereum_address()
    addr2 = make_ethereum_address()
    deposits = [
        Eth2Deposit(
            from_address=addr1,
            pubkey='0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
            withdrawal_credentials='0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
            value=Balance(FVal(32), FVal(64)),
            tx_hash=deserialize_evm_tx_hash('0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1'),  # noqa: E501
            tx_index=22,
            timestamp=Timestamp(int(1604506685)),
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
            withdrawal_credentials='0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
            value=Balance(FVal(32), FVal(64)),
            tx_hash=deserialize_evm_tx_hash('0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7'),  # noqa: E501
            tx_index=221,
            timestamp=Timestamp(int(1605043544)),
        ),
    ]

    serialized = process_result_list(deposits)
    assert serialized == [
        {
            'from_address': addr1,
            'pubkey': '0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
            'withdrawal_credentials': '0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
            'value': {'amount': '32', 'usd_value': '64'},
            'tx_hash': '0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
            'tx_index': 22,
            'timestamp': 1604506685,
        }, {
            'from_address': addr2,
            'pubkey': '0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
            'withdrawal_credentials': '0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
            'value': {'amount': '32', 'usd_value': '64'},
            'tx_hash': '0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7',
            'tx_index': 221,
            'timestamp': 1605043544,
        },
    ]


def test_get_validators_to_query_for_stats(database):
    db = DBEth2(database)
    now = ts_now()
    assert db.get_validators_to_query_for_stats(now) == []
    with database.user_write() as cursor:
        db.add_validators(cursor, [Eth2Validator(index=1, public_key='0xfoo1', ownership_proportion=ONE)])  # noqa: E501
    assert db.get_validators_to_query_for_stats(now) == [(1, 0)]

    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=1,
        timestamp=1607126400,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=ZERO,
        end_amount=FVal(32),
        deposits_number=1,
        amount_deposited=FVal(32),
    ), ValidatorDailyStats(
        validator_index=1,
        timestamp=1607212800,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    )])
    assert db.get_validators_to_query_for_stats(now) == [(1, 1607212800)]

    # now add a daily stats entry closer than a day in the past and see we don't query anything
    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=1,
        timestamp=now - 3600,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=ZERO,
        end_amount=FVal(32),
        deposits_number=1,
        amount_deposited=FVal(32),
    )])
    assert db.get_validators_to_query_for_stats(now) == []

    # Now add multiple validators and daily stats and assert on result
    with database.user_write() as cursor:
        db.add_validators(cursor, [
            Eth2Validator(index=2, public_key='0xfoo2', ownership_proportion=ONE),
            Eth2Validator(index=3, public_key='0xfoo3', ownership_proportion=ONE),
            Eth2Validator(index=4, public_key='0xfoo4', ownership_proportion=ONE),
        ])
    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=3,
        timestamp=1607126400,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=ZERO,
        end_amount=FVal(32),
        deposits_number=1,
        amount_deposited=FVal(32),
    ), ValidatorDailyStats(
        validator_index=3,
        timestamp=1617512800,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=4,
        timestamp=1617512800,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=4,
        timestamp=now - 7200,
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    )])
    assert db.get_validators_to_query_for_stats(now) == [(2, 0), (3, 1617512800)]

    assert db.get_validators_to_query_for_stats(1617512800 + 100000) == [(2, 0), (3, 1617512800)]


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats(price_historian, function_scope_messages_aggregator):  # pylint: disable=unused-argument  # noqa: E501
    validator_index = 33710
    stats = scrape_validator_daily_stats(
        validator_index=validator_index,
        last_known_timestamp=0,
        msg_aggregator=function_scope_messages_aggregator,
    )

    assert len(stats) >= 81
    expected_stats = [ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607126400,    # 2020/12/05
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=ZERO,
        end_amount=FVal(32),
        deposits_number=1,
        amount_deposited=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607212800,    # 2020/12/06
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607299200,    # 2020/12/07
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607385600,  # 2020/12/08
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607472000,  # 2020/12/09
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607558400,  # 2020/12/10
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607644800,  # 2020/12/11
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607731200,  # 2020/12/12
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607817600,  # 2020/12/13
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607904000,  # 2020/12/14
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607990400,  # 2020/12/15
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0119'),
        start_amount=FVal(32),
        end_amount=FVal('32.0119'),
        proposed_blocks=1,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608076800,  # 2020/12/16
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01318'),
        start_amount=FVal('32.0119'),
        end_amount=FVal('32.02508'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608163200,  # 2020/12/17
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('-0.00006'),
        start_amount=FVal('32.02508'),
        end_amount=FVal('32.02503'),
        missed_attestations=126,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608249600,  # 2020/12/18
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01286'),
        start_amount=FVal('32.02503'),
        end_amount=FVal('32.03789'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608336000,  # 2020/12/19
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01267'),
        start_amount=FVal('32.03789'),
        end_amount=FVal('32.05056'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608422400,  # 2020/12/20
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01442'),
        start_amount=FVal('32.05056'),
        end_amount=FVal('32.06499'),
        missed_attestations=1,
        proposed_blocks=1,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608508800,  # 2020/12/21
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01237'),
        start_amount=FVal('32.06499'),
        end_amount=FVal('32.07736'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608595200,  # 2020/12/22
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01213'),
        start_amount=FVal('32.07736'),
        end_amount=FVal('32.08949'),
        missed_attestations=1,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608681600,  # 2020/12/23
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.012'),
        start_amount=FVal('32.08949'),
        end_amount=FVal('32.10148'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608768000,  # 2020/12/24
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01194'),
        start_amount=FVal('32.10148'),
        end_amount=FVal('32.11342'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608854400,  # 2020/12/25
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01174'),
        start_amount=FVal('32.11342'),
        end_amount=FVal('32.12517'),
    )]
    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_last_known_timestamp(  # pylint: disable=unused-argument  # noqa: E501
        price_historian,
        function_scope_messages_aggregator,
):
    validator_index = 33710
    stats = scrape_validator_daily_stats(
        validator_index=validator_index,
        last_known_timestamp=1613520000,
        msg_aggregator=function_scope_messages_aggregator,
    )

    assert len(stats) >= 6
    expected_stats = [ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613606400,    # 2021/02/18
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.00784'),
        start_amount=FVal('32.6608'),
        end_amount=FVal('32.66863'),
        missed_attestations=1,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613692800,    # 2021/02/19
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.00683'),
        start_amount=FVal('32.66863'),
        end_amount=FVal('32.67547'),
        missed_attestations=19,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613779200,    # 2021/02/20
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.00798'),
        start_amount=FVal('32.67547'),
        end_amount=FVal('32.68345'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613865600,    # 2021/02/21
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.01114'),
        start_amount=FVal('32.68345'),
        end_amount=FVal('32.69459'),
        missed_attestations=3,
        proposed_blocks=1,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613952000,    # 2021/02/22
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.00782'),
        start_amount=FVal('32.69459'),
        end_amount=FVal('32.70241'),
        missed_attestations=1,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1614038400,    # 2021/02/23
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.00772'),
        start_amount=FVal('32.70241'),
        end_amount=FVal('32.71013'),
        missed_attestations=1,
    )]

    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_db_interaction(  # pylint: disable=unused-argument  # noqa: E501
        price_historian,
        database,
        function_scope_messages_aggregator,
        eth2,
):
    stats_call_patch = patch(
        'requests.get',
        wraps=requests.get,
    )

    validator_index = 33710
    public_key = '0x9882b4c33c0d5394205b12d62952c50fe03c6c9fe08faa36425f70afb7caac0689dcd981af35d0d03defb8286d50911d'  # noqa: E501
    with database.user_write() as cursor:
        dbeth2 = DBEth2(database)
        dbeth2.add_validators(cursor, [
            Eth2Validator(
                index=validator_index,
                public_key=public_key,
                ownership_proportion=ONE,
            ),
        ])
        with stats_call_patch as stats_call:
            filter_query = Eth2DailyStatsFilterQuery.make(
                validators=[validator_index],
                from_ts=1613606300,
                to_ts=1614038500,
            )
            stats, filter_total_found, sum_pnl, sum_usd_value = eth2.get_validator_daily_stats(
                cursor,
                filter_query=filter_query,
                only_cache=False,
                msg_aggregator=function_scope_messages_aggregator,
            )
            assert stats_call.call_count == 1
            assert len(stats) >= 6
            assert filter_total_found >= 6
            expected_stats = [ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=1613606400,    # 2021/02/18
                start_usd_price=FVal(1.55),
                end_usd_price=FVal(1.55),
                pnl=FVal('0.00784'),
                start_amount=FVal('32.6608'),
                end_amount=FVal('32.66863'),
                missed_attestations=1,
            ), ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=1613692800,    # 2021/02/19
                start_usd_price=FVal(1.55),
                end_usd_price=FVal(1.55),
                pnl=FVal('0.00683'),
                start_amount=FVal('32.66863'),
                end_amount=FVal('32.67547'),
                missed_attestations=19,
            ), ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=1613779200,    # 2021/02/20
                start_usd_price=FVal(1.55),
                end_usd_price=FVal(1.55),
                pnl=FVal('0.00798'),
                start_amount=FVal('32.67547'),
                end_amount=FVal('32.68345'),
            ), ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=1613865600,    # 2021/02/21
                start_usd_price=FVal(1.55),
                end_usd_price=FVal(1.55),
                pnl=FVal('0.01114'),
                start_amount=FVal('32.68345'),
                end_amount=FVal('32.69459'),
                missed_attestations=3,
                proposed_blocks=1,
            ), ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=1613952000,    # 2021/02/22
                start_usd_price=FVal(1.55),
                end_usd_price=FVal(1.55),
                pnl=FVal('0.00782'),
                start_amount=FVal('32.69459'),
                end_amount=FVal('32.70241'),
                missed_attestations=1,
            ), ValidatorDailyStats(
                validator_index=validator_index,
                timestamp=1614038400,    # 2021/02/23
                start_usd_price=FVal(1.55),
                end_usd_price=FVal(1.55),
                pnl=FVal('0.00772'),
                start_amount=FVal('32.70241'),
                end_amount=FVal('32.71013'),
                missed_attestations=1,
            )]
            # TODO: doesn't seem to be related to the refactoring. Need to check.
            assert stats[:len(expected_stats)] == expected_stats
            assert sum_pnl >= sum(x.pnl for x in expected_stats)
            assert sum_usd_value >= sum(x.pnl * ((x.start_usd_price + x.end_usd_price) / 2) for x in expected_stats)  # noqa: E501

            # Make sure that calling it again does not make an external call
            stats, filter_total_found, _, _ = eth2.get_validator_daily_stats(
                cursor,
                filter_query=filter_query,
                only_cache=False,
                msg_aggregator=function_scope_messages_aggregator,
            )
            assert stats_call.call_count == 1
            assert stats[:len(expected_stats)] == expected_stats

            # Check that changing ownership proportion works
            dbeth2.edit_validator(
                validator_index=validator_index,
                ownership_proportion=FVal(0.45),
            )
            stats, filter_total_found, _, _ = eth2.get_validator_daily_stats(
                cursor,
                filter_query=filter_query,
                only_cache=False,
                msg_aggregator=function_scope_messages_aggregator,
            )
            last_stat = stats[:len(expected_stats)][-1]
            assert last_stat.pnl_balance.amount == expected_stats[-1].pnl_balance.amount * FVal(0.45)  # noqa: E501
