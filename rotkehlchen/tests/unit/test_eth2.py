from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.eth2 import (
    REQUEST_DELTA_TS,
    _get_eth2_staking_deposits_onchain,
    get_eth2_balances,
    get_eth2_details,
    get_eth2_staking_deposits,
)
from rotkehlchen.chain.ethereum.eth2_utils import (
    _scrape_validator_daily_stats,
    get_validator_daily_stats,
)
from rotkehlchen.chain.ethereum.typing import (
    DEPOSITING_VALIDATOR_PERFORMANCE,
    Eth2Deposit,
    ValidatorDailyStats,
    ValidatorDetails,
    ValidatorPerformance,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.ethereum import (
    ETHEREUM_TEST_PARAMETERS,
    wait_until_all_nodes_connected,
)
from rotkehlchen.tests.utils.factories import make_ethereum_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.typing import Timestamp
from rotkehlchen.user_messages import MessagesAggregator

ADDR1 = deserialize_ethereum_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
ADDR2 = deserialize_ethereum_address('0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19')
ADDR3 = deserialize_ethereum_address('0x3266F3546a1e5Dc6A15588f3324741A0E20a3B6c')

# List of ADDR1, ADDR2 and ADDR3 deposit events from 1604506685 to 1605044577
# sorted by (timestamp, log_index).
EXPECTED_DEPOSITS = [
    Eth2Deposit(
        from_address=ADDR1,
        pubkey='0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
        withdrawal_credentials='0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=9,
        tx_hash='0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
        log_index=22,
        timestamp=Timestamp(int(1604506685)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x90b2f65cb43d9cdb2279af9f76010d667b9d8d72e908f2515497a7102820ce6bb15302fe2b8dc082fce9718569344ad8',  # noqa: E501
        withdrawal_credentials='0x00a257d19e1650dec1ab59fc9e1cb9a9fc2fe7265b0f27e7d79ff61aeff0a1f0',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=993,
        tx_hash='0x3403bd94a1bf185ee18a525499e408a1b9b7d801cff6418e31efda346762e754',
        log_index=266,
        timestamp=Timestamp(int(1604611131)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb4610a24815f1874a12eba7ea9b77126ca16c0aa29a127ba14ba4ee179834f4feb0aa4497baaa50985ad748d15a286cf',  # noqa: E501
        withdrawal_credentials='0x00f7ce43bfb18009abe0e8e5b3a8c0da3c014bc80e4a0a8dccda647f48ea8547',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=994,
        tx_hash='0x89b3b87c8841950893a4752ab03cbb835a1b5593a5d68cd343663824bf2d311e',
        log_index=141,
        timestamp=Timestamp(int(1604611169)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xa96352b921bcc4b1a90a7aeb68739b6a5508079a63158ca84786241da247142173f9b38d553de899c1778de4f83e6c6c',  # noqa: E501
        withdrawal_credentials='0x0062a11c0395b8379bff5310398be82ee6d950d397899f7d39751d5721c01d9e',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=995,
        tx_hash='0x1a228f3421f5b18904c92a21690b188d05a47bfbcfbe2175cbfdf27e2cd6ea53',
        log_index=62,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x911cba78efe677a502a3995060e2389e2d16d03f989c87f1a0fdf82345a77dfd3b9476720825ea5f5a374bd386301b60',  # noqa: E501
        withdrawal_credentials='0x0007b5cf7558a6ee86d2dbf69227dfee28783d36fc6d18b30bda7ffc385fe27a',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=996,
        tx_hash='0xae84e32268d21ca03559d03abc769eaeaff2409ce282e7a1b9a3015a9cdb9357',
        log_index=63,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35',  # noqa: E501
        withdrawal_credentials='0x00c988827cb5ce8a4a33e67bf5e61457949d9935cd21d44e15d5751c91a2c177',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=997,
        tx_hash='0x7cb53c523001273ada3623edfdc32838683b3820589be2a450b1d527e8851070',
        log_index=64,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x89da8cb17b203eefacc8346e1ee718a305b622028dc77913d3b26f2034f92693d305a630f45c76b781ef68cd4640253e',  # noqa: E501
        withdrawal_credentials='0x00df23e0483e4b77609b849368b6f84cc5b0a55bd7bcd95374ed1a59cc73fc28',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=998,
        tx_hash='0xf2174fbaaf45204a178652ce28567d398a8afb3699b5bd34b5bbb7b33a3b8c34',
        log_index=65,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x930a90c7f0b00ce4c7d7994652f1e301753c084d5499de31abadb2e3913cba2eb4026de8d49ea35294db10119b83b2e1',  # noqa: E501
        withdrawal_credentials='0x00b522800f977a14d8eae22d675d241b53807c6d75ba1e180f8ac52d9600322c',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=999,
        tx_hash='0x187bef85f7797f4f42534fcfa080ed28ab77491b79fe9e9be8039416eebab6bc',
        log_index=66,
        timestamp=Timestamp(int(1604611182)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb18e1737e1a1a76b8dff905ba7a4cb1ff5c526a4b7b0788188aade0488274c91e9c797e75f0f8452384ff53d44fad3df',  # noqa: E501
        withdrawal_credentials='0x000c0efd86dba58898debd8e80fa1d7d88bc2b7b1237d32485b2c9101edba203',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1000,
        tx_hash='0xcb929eb5425743eb039edd03495a53141643f8e341483d7c8319d55a746a3e7d',
        log_index=298,
        timestamp=Timestamp(int(1604612368)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x976c5c76f3cbc10d22ac50c27f816b82d91192f6b6177857a89a0349fcecaa8301469ab1d303e381e630c591456e0e54',  # noqa: E501
        withdrawal_credentials='0x00cd586bed9443813cf4778a71224ceaef520419afc803fd720a0f4b068ee839',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1040,
        tx_hash='0x64a66740ae4cf64e8735271f94fa9c763e9a68c506292671041301196f6f2d70',
        log_index=172,
        timestamp=Timestamp(int(1604641797)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x85a82370ef68f52209d3a07f5cca32b0bbe4d2d39574f39beab746d54e696831a02a95f3dcea25f1fba766bdb5048a09',  # noqa: E501
        withdrawal_credentials='0x007e6a2f6fa852677aa4239cc753240421993f931feeab37c5d654739ea30bfc',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1041,
        tx_hash='0xccd2ddb9827a39bb30fd1a2166f40d2d571feab375e0d6469ba749d86e3f4e0b',
        log_index=246,
        timestamp=Timestamp(int(1604641801)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb347f7421cec107e1cdf3ae9b6308c577fc6c1c254fa44552be97db3eccdac667dc6d6e5409f8e546c9dcbcef47c83f3',  # noqa: E501
        withdrawal_credentials='0x00477a22f13287589a64ee40b8674a43c4fbf381e2e842b9814dfc4f75c7a10c',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1042,
        tx_hash='0x721a69c5bd3b697827eabd44d7176e95ba803a462d99e74f62299111e8c516b1',
        log_index=256,
        timestamp=Timestamp(int(1604641801)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x965f40c2a6f004d4457a89e7b49ea5d101367cd31c86836d6551ea504e55ee3e32aed8b2615ee1c13212db46fb411a7a',  # noqa: E501
        withdrawal_credentials='0x006483a6a77c286cdc1711d67631244a2d4441babca4fd82acef4bb6c6be5a50',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1043,
        tx_hash='0xedf5930af6dd9efd54787d57acb250aff72ecb9a697b4abefa87274035343787',
        log_index=8,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x90d4b57b88eb613737c1bb2e79f8ed8f2abd1c5e31cea9aa741f16cb777716d2fc1cabf9e15d3c15edf8091533916eb5',  # noqa: E501
        withdrawal_credentials='0x00cd969a3cfd32e0db1b11041e53e971961ff9500e1deaf7d8ebb3bbe0de540c',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1044,
        tx_hash='0x92f90a1271a184e1c5ee1e468f391bab5749108effb2c57a49f2cef153f9bc58',
        log_index=44,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0x92a5d445d10ce8d413c506a012ef92719ca230ab0fd4066e2968df8adb52bb112ee080a3267f282f09db94dc59a3ec77',  # noqa: E501
        withdrawal_credentials='0x001badfb8f47cd4650788335cd314f6aa4be2350fe2313d2a7add27e63535d3a',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1045,
        tx_hash='0x7c2f5f1ade5b7df58eebbe3c76b8cb038936e0f7fb4479ab5ac9df7a6f0fbd41',
        log_index=62,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR3,
        pubkey='0xb44383a9ce75b90cc8248bdd46d02a2a309117bbfdbe9fd05743def6d483549072c3285ae4953f48b1d17c9787697764',  # noqa: E501
        withdrawal_credentials='0x00c45ca431dfbe790525de640d928e0dfdd9c08e93a69482a3c2adedb379d874',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1046,
        tx_hash='0x5722e35df3387aa21c825b0d8ddea3cf168d421a31edfe63c73ffc028df2a4f1',
        log_index=74,
        timestamp=Timestamp(int(1604641860)),
    ),
    Eth2Deposit(
        from_address=ADDR2,
        pubkey='0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
        withdrawal_credentials='0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1650,
        tx_hash='0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7',
        log_index=221,
        timestamp=Timestamp(int(1605043544)),
    ),
    Eth2Deposit(
        from_address=ADDR2,
        pubkey='0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475',  # noqa: E501
        withdrawal_credentials='0x0082add39f581048857972a9bac9ae5f5c42b23c947281e4ca30953386c866ed',  # noqa: E501
        value=Balance(FVal(32), FVal(64)),
        deposit_index=1651,
        tx_hash='0xc114753fb5d11a94a95dd980cff9f26693632550de56b5291201774686ddba3f',
        log_index=145,
        timestamp=Timestamp(int(1605044577)),
    ),
]


@pytest.mark.freeze_time(datetime(2020, 11, 10, 21, 42, 57))
@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
@pytest.mark.parametrize('default_mock_price_value', [FVal(2)])
def test_get_eth2_staking_deposits_onchain(  # pylint: disable=unused-argument
        ethereum_manager,
        call_order,
        ethereum_manager_connect_at_start,
        inquirer,
        price_historian,
):
    """
    Test on-chain request of deposit events for ADDR1, ADDR2 and ADDR3 in a
    specific time range:
      - From ts:   1604506685 (from EXPECTED_DEPOSITS[0].timestamp)
      - To ts:     1605044577 (from EXPECTED_DEPOSITS[-1].timestamp)

    NB: Using `to_ts` from datetime now is for showing usefulness of freezegun
    """
    from_ts = EXPECTED_DEPOSITS[0].timestamp  # 1604506685
    to_ts = int(datetime.now().timestamp())  # 1605044577

    wait_until_all_nodes_connected(
        ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
        ethereum=ethereum_manager,
    )
    # Main call
    deposits = _get_eth2_staking_deposits_onchain(
        ethereum=ethereum_manager,
        addresses=[ADDR1, ADDR2, ADDR3],
        msg_aggregator=MessagesAggregator(),
        from_ts=from_ts,
        to_ts=to_ts,
    )
    # Querying filtering by a timestamp range and specific addresses, and
    # having replicated the deposits in EXPECTED_DEPOSITS allows to assert the
    # length. Due to `_get_eth2_staking_deposits_onchain()` does not implement
    # sorting deposits by (timestamp, log_index), asserting both lists against
    # each other is discarded
    assert len(deposits) == len(EXPECTED_DEPOSITS)

    for expected_deposit in EXPECTED_DEPOSITS:
        assert expected_deposit in deposits

    total_addr1 = sum(
        deposit.value.amount for deposit in deposits if deposit.from_address == ADDR1
    )
    total_addr2 = sum(
        deposit.value.amount for deposit in deposits if deposit.from_address == ADDR2
    )
    total_addr3 = sum(
        deposit.value.amount for deposit in deposits if deposit.from_address == ADDR3
    )

    assert total_addr1 == FVal(32)
    assert total_addr2 == FVal(64)
    assert total_addr3 == FVal(480)


@pytest.mark.parametrize(*ETHEREUM_TEST_PARAMETERS)
@pytest.mark.parametrize('default_mock_price_value', [FVal(2)])
def test_get_eth2_staking_deposits_fetch_from_db(  # pylint: disable=unused-argument
        ethereum_manager,
        call_order,
        ethereum_manager_connect_at_start,
        inquirer,
        price_historian,
        freezer,
):
    """
    Test new on-chain requests for existing addresses requires a difference of
    REQUEST_DELTA_TS since last used query range `end_ts`.
    """
    freezer.move_to(datetime.fromtimestamp(EXPECTED_DEPOSITS[0].timestamp))
    ts_now = int(datetime.now().timestamp())  # 1604506685

    database = MagicMock()
    database.get_used_query_range.side_effect = [
        (Timestamp(ts_now - (2 * REQUEST_DELTA_TS)), Timestamp(ts_now)),
        (Timestamp(ts_now - (2 * REQUEST_DELTA_TS)), Timestamp(ts_now)),
        (Timestamp(ts_now - (2 * REQUEST_DELTA_TS)), Timestamp(ts_now)),
    ]
    dbeth2 = MagicMock()
    dbeth2.get_eth2_deposits.side_effect = [
        [],  # no on-chain request, nothing in DB
        [],  # no on-chain request, nothing in DB
        [EXPECTED_DEPOSITS[0]],  # on-chain request, deposit in DB
    ]
    dbeth2_mock = patch('rotkehlchen.chain.ethereum.eth2.DBEth2', return_value=dbeth2)
    with dbeth2_mock, patch(
        'rotkehlchen.chain.ethereum.eth2._get_eth2_staking_deposits_onchain',
    ) as mock_get_eth2_staking_deposits_onchain:
        # 3rd call return
        mock_get_eth2_staking_deposits_onchain.return_value = [EXPECTED_DEPOSITS[0]]

        wait_until_all_nodes_connected(
            ethereum_manager_connect_at_start=ethereum_manager_connect_at_start,
            ethereum=ethereum_manager,
        )
        message_aggregator = MessagesAggregator()

        # First call
        deposit_results_onchain = get_eth2_staking_deposits(
            ethereum=ethereum_manager,
            addresses=[ADDR1],
            msg_aggregator=message_aggregator,
            database=database,
        )
        assert deposit_results_onchain == []
        mock_get_eth2_staking_deposits_onchain.assert_not_called()

        # NB: Move time to ts_now + REQUEST_DELTA_TS - 1s
        freezer.move_to(datetime.fromtimestamp(ts_now + REQUEST_DELTA_TS - 1))

        # Second call
        deposit_results_onchain = get_eth2_staking_deposits(
            ethereum=ethereum_manager,
            addresses=[ADDR1],
            msg_aggregator=message_aggregator,
            database=database,
        )
        assert deposit_results_onchain == []
        mock_get_eth2_staking_deposits_onchain.assert_not_called()

        # NB: Move time to ts_now + REQUEST_DELTA_TS (triggers request)
        freezer.move_to(datetime.fromtimestamp(ts_now + REQUEST_DELTA_TS))

        # Third call
        deposit_results_onchain = get_eth2_staking_deposits(
            ethereum=ethereum_manager,
            addresses=[ADDR1],
            msg_aggregator=message_aggregator,
            database=database,
        )
        assert deposit_results_onchain == [EXPECTED_DEPOSITS[0]]
        mock_get_eth2_staking_deposits_onchain.assert_called_with(
            ethereum=ethereum_manager,
            addresses=[ADDR1],
            msg_aggregator=message_aggregator,
            from_ts=Timestamp(ts_now),
            to_ts=Timestamp(ts_now + REQUEST_DELTA_TS),
        )


def test_eth2_deposits_serialization():
    addr1 = make_ethereum_address()
    addr2 = make_ethereum_address()
    deposits = [
        Eth2Deposit(
            from_address=addr1,
            pubkey='0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
            withdrawal_credentials='0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
            value=Balance(FVal(32), FVal(64)),
            deposit_index=9,
            tx_hash='0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
            log_index=22,
            timestamp=Timestamp(int(1604506685)),
        ), Eth2Deposit(
            from_address=addr2,
            pubkey='0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
            withdrawal_credentials='0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
            value=Balance(FVal(32), FVal(64)),
            deposit_index=1650,
            tx_hash='0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7',
            log_index=221,
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
            'deposit_index': 9,
            'tx_hash': '0xd9eca1c2a0c5ff2f25071713432b21cc4d0ff2e8963edc63a48478e395e08db1',
            'log_index': 22,
            'timestamp': 1604506685,
        }, {
            'from_address': addr2,
            'pubkey': '0xa8ff5fc88412d080a297683c25a791ef77eb52d75b265fabab1f2c2591bb927c35818ac6289bc6680ab252787d0ebab3',  # noqa: E501
            'withdrawal_credentials': '0x00cfe1c10347d642a8b8daf86d23bcb368076972691445de2cf517ff43765817',  # noqa: E501
            'value': {'amount': '32', 'usd_value': '64'},
            'deposit_index': 1650,
            'tx_hash': '0x6905f4d1843fb8c003c1fbbc2c8e6c5f9792f4f44ddb1122553412ee0b128da7',
            'log_index': 221,
            'timestamp': 1605043544,
        },
    ]


def _create_beacon_mock(beaconchain):
    def mock_requests_get(url, *args, **kwargs):  # pylint: disable=unused-argument
        if 'eth1' in url:
            response = '{"status":"OK","data":[{"publickey":"0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b","valid_signature":true,"validatorindex":9},{"publickey":"0x8b242e5cdb0a7740a605f3c39262253eb2b5e7ee514a544e823f996e8de9961db7d5264d08c5ce13a65efa82b868accc","valid_signature":true,"validatorindex":1507}]}'  # noqa: E501
        elif 'performance' in url:
            response = '{"status":"OK","data":{"balance":32143716247,"performance1d":14437802,"performance31d":143716247,"performance365d":143716247,"performance7d":105960750,"validatorindex":9}}'  # noqa: E501
        else:
            raise AssertionError(f'Unexpected url: {url} in mock of beaconchain in tests')
        return MockResponse(200, response)

    return patch.object(beaconchain.session, 'get', wraps=mock_requests_get)


def test_get_eth2_balances_validator_not_yet_active(beaconchain, inquirer):  # pylint: disable=unused-argument  # noqa: E501
    """Test that if a validator is detected but is not yet active the balance is shown properly

    Test for: https://github.com/rotki/rotki/issues/1888
    """
    with _create_beacon_mock(beaconchain):
        mapping = get_eth2_balances(beaconchain, [ADDR1])

    assert len(mapping) == 1
    amount = FVal('64.143716247')
    assert mapping[ADDR1] == Balance(amount=amount, usd_value=amount * FVal('1.5'))


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_get_eth2_details_validator_not_yet_active(beaconchain, inquirer, price_historian):  # pylint: disable=unused-argument  # noqa: E501
    """Test that if a validator is detected but is not yet active the balance is shown properly

    Test for: https://github.com/rotki/rotki/issues/1888
    """
    with _create_beacon_mock(beaconchain):
        details = get_eth2_details(beaconchain=beaconchain, addresses=[ADDR1])

    for idx in range(0, 2):
        # basic check about daily stats but then delete since this is not what this test checks
        assert len(details[idx].daily_stats) > 0
        assert details[idx].daily_stats[0].timestamp < details[idx].daily_stats[-1].timestamp
        details[idx] = details[idx]._replace(daily_stats=[])

    expected_details = [
        ValidatorDetails(
            validator_index=9,
            public_key='0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
            eth1_depositor=ADDR1,
            performance=ValidatorPerformance(
                balance=32143716247,
                performance_1d=14437802,
                performance_1w=105960750,
                performance_1m=143716247,
                performance_1y=143716247,
            ),
            daily_stats=[],
        ), ValidatorDetails(
            validator_index=1507,
            public_key='0x8b242e5cdb0a7740a605f3c39262253eb2b5e7ee514a544e823f996e8de9961db7d5264d08c5ce13a65efa82b868accc',  # noqa: E501
            eth1_depositor=ADDR1,
            performance=DEPOSITING_VALIDATOR_PERFORMANCE,
            daily_stats=[],
        ),
    ]
    assert details == expected_details


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats(price_historian, function_scope_messages_aggregator):  # pylint: disable=unused-argument  # noqa: E501
    stats = _scrape_validator_daily_stats(
        validator_index=33710,
        last_known_timestamp=0,
        msg_aggregator=function_scope_messages_aggregator,
    )

    assert len(stats) >= 81
    expected_stats = [ValidatorDailyStats(
        timestamp=1607126400,    # 2020/12/05
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=ZERO,
        end_amount=FVal(32),
        deposits_number=1,
        amount_deposited=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607212800,    # 2020/12/06
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607299200,    # 2020/12/07
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607385600,  # 2020/12/08
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607472000,  # 2020/12/09
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607558400,  # 2020/12/10
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607644800,  # 2020/12/11
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607731200,  # 2020/12/12
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607817600,  # 2020/12/13
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607904000,  # 2020/12/14
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=ZERO,
        start_amount=FVal(32),
        end_amount=FVal(32),
    ), ValidatorDailyStats(
        timestamp=1607990400,  # 2020/12/15
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0120'),
        start_amount=FVal(32),
        end_amount=FVal('32.01'),
        proposed_blocks=1,
    ), ValidatorDailyStats(
        timestamp=1608076800,  # 2020/12/16
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0132'),
        start_amount=FVal('32.01'),
        end_amount=FVal('32.03'),
    ), ValidatorDailyStats(
        timestamp=1608163200,  # 2020/12/17
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('-0.0001'),
        start_amount=FVal('32.03'),
        end_amount=FVal('32.03'),
        missed_attestations=126,
    ), ValidatorDailyStats(
        timestamp=1608249600,  # 2020/12/18
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0129'),
        start_amount=FVal('32.03'),
        end_amount=FVal('32.04'),
    ), ValidatorDailyStats(
        timestamp=1608336000,  # 2020/12/19
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0127'),
        start_amount=FVal('32.04'),
        end_amount=FVal('32.05'),
    ), ValidatorDailyStats(
        timestamp=1608422400,  # 2020/12/20
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0144'),
        start_amount=FVal('32.05'),
        end_amount=FVal('32.07'),
        missed_attestations=1,
        proposed_blocks=1,
    ), ValidatorDailyStats(
        timestamp=1608508800,  # 2020/12/21
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0124'),
        start_amount=FVal('32.07'),
        end_amount=FVal('32.08'),
    ), ValidatorDailyStats(
        timestamp=1608595200,  # 2020/12/22
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0121'),
        start_amount=FVal('32.08'),
        end_amount=FVal('32.09'),
        missed_attestations=1,
    ), ValidatorDailyStats(
        timestamp=1608681600,  # 2020/12/23
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0120'),
        start_amount=FVal('32.09'),
        end_amount=FVal('32.10'),
    ), ValidatorDailyStats(
        timestamp=1608768000,  # 2020/12/24
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0119'),
        start_amount=FVal('32.1'),
        end_amount=FVal('32.11'),
    ), ValidatorDailyStats(
        timestamp=1608854400,  # 2020/12/25
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0117'),
        start_amount=FVal('32.11'),
        end_amount=FVal('32.13'),
    )]

    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_last_known_timestamp(  # pylint: disable=unused-argument  # noqa: E501
        price_historian,
        function_scope_messages_aggregator,
):
    stats = _scrape_validator_daily_stats(
        validator_index=33710,
        last_known_timestamp=1613520000,
        msg_aggregator=function_scope_messages_aggregator,
    )

    assert len(stats) >= 6
    expected_stats = [ValidatorDailyStats(
        timestamp=1613606400,    # 2021/02/18
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0078'),
        start_amount=FVal('32.66'),
        end_amount=FVal('32.67'),
        missed_attestations=1,
    ), ValidatorDailyStats(
        timestamp=1613692800,    # 2021/02/19
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0068'),
        start_amount=FVal('32.67'),
        end_amount=FVal('32.68'),
        missed_attestations=19,
    ), ValidatorDailyStats(
        timestamp=1613779200,    # 2021/02/20
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0080'),
        start_amount=FVal('32.68'),
        end_amount=FVal('32.68'),
    ), ValidatorDailyStats(
        timestamp=1613865600,    # 2021/02/21
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0111'),
        start_amount=FVal('32.68'),
        end_amount=FVal('32.69'),
        missed_attestations=3,
        proposed_blocks=1,
    ), ValidatorDailyStats(
        timestamp=1613952000,    # 2021/02/22
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0078'),
        start_amount=FVal('32.69'),
        end_amount=FVal('32.7'),
        missed_attestations=1,
    ), ValidatorDailyStats(
        timestamp=1614038400,    # 2021/02/23
        start_usd_price=FVal(1.55),
        end_usd_price=FVal(1.55),
        pnl=FVal('0.0077'),
        start_amount=FVal('32.7'),
        end_amount=FVal('32.71'),
        missed_attestations=1,
    )]

    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_db_interaction(  # pylint: disable=unused-argument  # noqa: E501
        price_historian,
        database,
        function_scope_messages_aggregator,
):
    stats_call_patch = patch(
        'requests.get',
        wraps=requests.get,
    )

    with stats_call_patch as stats_call:
        stats = get_validator_daily_stats(
            db=database,
            validator_index=33710,
            msg_aggregator=function_scope_messages_aggregator,
            from_timestamp=1613606300,
            to_timestamp=1614038500,
        )

        assert stats_call.call_count == 1
        assert len(stats) >= 6
        expected_stats = [ValidatorDailyStats(
            timestamp=1613606400,    # 2021/02/18
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            pnl=FVal('0.0078'),
            start_amount=FVal('32.66'),
            end_amount=FVal('32.67'),
            missed_attestations=1,
        ), ValidatorDailyStats(
            timestamp=1613692800,    # 2021/02/19
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            pnl=FVal('0.0068'),
            start_amount=FVal('32.67'),
            end_amount=FVal('32.68'),
            missed_attestations=19,
        ), ValidatorDailyStats(
            timestamp=1613779200,    # 2021/02/20
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            pnl=FVal('0.0080'),
            start_amount=FVal('32.68'),
            end_amount=FVal('32.68'),
        ), ValidatorDailyStats(
            timestamp=1613865600,    # 2021/02/21
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            pnl=FVal('0.0111'),
            start_amount=FVal('32.68'),
            end_amount=FVal('32.69'),
            missed_attestations=3,
            proposed_blocks=1,
        ), ValidatorDailyStats(
            timestamp=1613952000,    # 2021/02/22
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            pnl=FVal('0.0078'),
            start_amount=FVal('32.69'),
            end_amount=FVal('32.7'),
            missed_attestations=1,
        ), ValidatorDailyStats(
            timestamp=1614038400,    # 2021/02/23
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            pnl=FVal('0.0077'),
            start_amount=FVal('32.7'),
            end_amount=FVal('32.71'),
            missed_attestations=1,
        )]
        assert stats[:len(expected_stats)] == expected_stats

        # Make sure that calling it again does not make an external call
        stats = get_validator_daily_stats(
            db=database,
            validator_index=33710,
            msg_aggregator=function_scope_messages_aggregator,
            from_timestamp=1613606300,
            to_timestamp=1614038500,
        )
        assert stats_call.call_count == 1
        assert stats[:len(expected_stats)] == expected_stats
