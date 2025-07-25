import os
import re
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    CONSOLIDATION_REQUEST_CONTRACT,
    CPT_ETH2,
    MIN_EFFECTIVE_BALANCE,
    UNKNOWN_VALIDATOR_INDEX,
    WITHDRAWAL_REQUEST_CONTRACT,
)
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDailyStats,
    ValidatorDetails,
    ValidatorDetailsWithStatus,
    ValidatorStatus,
    ValidatorType,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import (
    EthBlockEvent,
    EthDepositEvent,
    EthWithdrawalEvent,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ChainID,
    Eth2PubKey,
    EvmTransaction,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.history.price import PriceHistorian
    from rotkehlchen.types import ChecksumEvmAddress

ADDR1 = string_to_evm_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
ADDR2 = string_to_evm_address('0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19')


def test_get_validators_to_query_for_stats(database):
    db = DBEth2(database)
    now = ts_now()
    assert db.get_validators_to_query_for_stats(now) == []
    with database.user_write() as cursor:
        db.add_or_update_validators(cursor, [
            ValidatorDetails(
                validator_index=1,
                public_key=Eth2PubKey('0xfoo1'),
                validator_type=ValidatorType.DISTRIBUTING,
            ),
        ],
        )
    assert db.get_validators_to_query_for_stats(now) == [(1, 0, None)]

    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=1,
        timestamp=Timestamp(1607126400),
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=1,
        timestamp=Timestamp(1607212800),
        pnl=ZERO,
    )])
    assert db.get_validators_to_query_for_stats(now) == [(1, 1607212800, None)]

    # now add a daily stats entry closer than a day in the past and see we don't query anything
    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=1,
        timestamp=Timestamp(now - 3600),
        pnl=ZERO,
    )])
    assert db.get_validators_to_query_for_stats(now) == []

    # Now add multiple validators and daily stats and assert on result
    with database.user_write() as cursor:
        db.add_or_update_validators(cursor, [
            ValidatorDetails(validator_index=2, public_key=Eth2PubKey('0xfoo2'), validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
            ValidatorDetails(validator_index=3, public_key=Eth2PubKey('0xfoo3'), validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
            ValidatorDetails(validator_index=4, public_key=Eth2PubKey('0xfoo4'), validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
        ])
    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=3,
        timestamp=Timestamp(1607126400),
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=3,
        timestamp=Timestamp(1617512800),
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=4,
        timestamp=Timestamp(1617512800),
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=4,
        timestamp=Timestamp(now - 7200),
        pnl=ZERO,
    )])
    assert db.get_validators_to_query_for_stats(now) == [(2, 0, None), (3, 1617512800, None)]
    assert db.get_validators_to_query_for_stats(Timestamp(1617512800 + DAY_IN_SECONDS * 2 + HOUR_IN_SECONDS * 18 + 1)) == [(2, 0, None), (3, 1617512800, None)]  # noqa: E501

    # Let's make validator 3 have an exit after its last stat
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=EthWithdrawalEvent(
                validator_index=3,
                timestamp=ts_sec_to_ms(Timestamp(1617512800 + DAY_IN_SECONDS)),
                amount=ONE,
                withdrawal_address=make_evm_address(),
                is_exit=True,
            ),
        )
    assert db.get_validators_to_query_for_stats(now) == [(2, 0, None), (3, 1617512800, 1617512800 + DAY_IN_SECONDS)]  # noqa: E501

    # this is invalid as a validator can't have 2 exits but this is for the unit test
    # make sure the validator exits and stats exists up to the exit
    with database.user_write() as write_cursor:
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=EthWithdrawalEvent(
                validator_index=3,
                timestamp=ts_sec_to_ms(Timestamp(1617512800)),
                amount=ONE,
                withdrawal_address=make_evm_address(),
                is_exit=True,
            ),
        )
    assert db.get_validators_to_query_for_stats(now) == [(2, 0, None)]


DAILY_STATS_RE = re.compile(r'https://beaconcha.in/api/v1/validator/stats/(\d+)')


def mock_query_validator_daily_stats(beaconchain: 'BeaconChain', network_mocking: bool):

    def mock_query(url, **kwargs):  # pylint: disable=unused-argument
        match = DAILY_STATS_RE.search(url)
        if match is None:
            raise AssertionError(f'Unexpected validator stats query in test: {url}')

        validator_index = int(match.group(1))
        root_path = Path(__file__).resolve().parent.parent.parent
        file_path = root_path / 'tests' / 'data' / 'mocks' / 'test_eth2' / 'validator_daily_stats' / f'{validator_index}.json'  # noqa: E501
        return MockResponse(200, file_path.read_text(encoding='utf8'))

    return patch.object(
        beaconchain.session,
        'request',
        new=mock_query if network_mocking else requests.get,
    )


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats(
        network_mocking,
        price_historian,
        database,
        messages_aggregator,
):  # pylint: disable=unused-argument
    validator_index = 33710
    beaconchain = BeaconChain(database, messages_aggregator)
    with mock_query_validator_daily_stats(beaconchain, network_mocking):
        stats = beaconchain.query_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=0,
            exit_ts=None,
        )

    assert len(stats) >= 81
    expected_stats = [ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607212823,    # 2020/12/06
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607299223,    # 2020/12/07
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607385623,  # 2020/12/08
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607472023,  # 2020/12/09
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607558423,  # 2020/12/10
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607644823,  # 2020/12/11
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607731223,  # 2020/12/12
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607817623,  # 2020/12/13
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607904023,  # 2020/12/14
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607990423,  # 2020/12/15
        pnl=FVal('0.011901184'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608076823,  # 2020/12/16
        pnl=FVal('0.013122458'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608163223,  # 2020/12/17
        pnl=FVal('-0.000114942'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608249623,  # 2020/12/18
        pnl=FVal('0.01280657'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608336023,  # 2020/12/19
        pnl=FVal('0.01261697'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608422423,  # 2020/12/20
        pnl=FVal('0.014366383'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608508823,  # 2020/12/21
        pnl=FVal('0.012315232'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608595223,  # 2020/12/22
        pnl=FVal('0.012076577'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608681623,  # 2020/12/23
        pnl=FVal('0.011941107'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608768023,  # 2020/12/24
        pnl=FVal('0.011885565'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608854423,  # 2020/12/25
        pnl=FVal('0.011691997'),
    )]
    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats

    # make sure that the 24/25 Dec 2022 0 stat, which is after exit is not there
    assert stats[-1].timestamp <= 1671753600
    assert stats[-1].pnl != ZERO
    assert stats[-2].timestamp <= 1671753600
    assert stats[-2].pnl != ZERO


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_last_known_timestamp(
        network_mocking,
        price_historian,
        database,
        messages_aggregator,
):  # pylint: disable=unused-argument
    validator_index = 33710
    beaconchain = BeaconChain(database, messages_aggregator)
    with mock_query_validator_daily_stats(beaconchain, network_mocking):
        stats = beaconchain.query_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=1613520000,
            exit_ts=None,
        )

    assert len(stats) >= 6
    expected_stats = [ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613520023,    # 2021/02/17
        pnl=FVal('0.007824513'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613606423,    # 2021/02/18
        pnl=FVal('0.007801811'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613692823,    # 2021/02/19
        pnl=FVal('0.006798106'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613779223,    # 2021/02/20
        pnl=FVal('0.007945406'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613865623,    # 2021/02/21
        pnl=FVal('0.011105614'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613952023,    # 2021/02/22
        pnl=FVal('0.007780681'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1614038423,    # 2021/02/23
        pnl=FVal('0.007687101'),
    )]

    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_db_interaction(  # pylint: disable=unused-argument
        price_historian,
        database,
        eth2,
        network_mocking,
):
    validator_index = 33710
    public_key = Eth2PubKey('0x9882b4c33c0d5394205b12d62952c50fe03c6c9fe08faa36425f70afb7caac0689dcd981af35d0d03defb8286d50911d')  # noqa: E501
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [
            ValidatorDetails(
                validator_index=validator_index,
                public_key=public_key,
                validator_type=ValidatorType.DISTRIBUTING,
            ),
        ])

    with (
        mock_query_validator_daily_stats(eth2.beacon_inquirer.beaconchain, network_mocking),
        patch('rotkehlchen.chain.ethereum.modules.eth2.beacon.BeaconInquirer.query_validator_daily_stats', wraps=eth2.beacon_inquirer.query_validator_daily_stats) as stats_call,  # noqa: E501
    ):
        filter_query = Eth2DailyStatsFilterQuery.make(
            validator_indices=[validator_index],
            from_ts=Timestamp(1613606300),
            to_ts=Timestamp(1614038500),
        )
        with database.conn.read_ctx() as cursor:
            stats, filter_total_found, sum_pnl = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=filter_query,
                only_cache=False,
            )

        assert stats_call.call_count == 1
        assert len(stats) == 6
        assert filter_total_found == 6
        expected_stats = [ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613606423,    # 2021/02/18
            pnl=FVal('0.007801811'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613692823,    # 2021/02/19
            pnl=FVal('0.006798106'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613779223,    # 2021/02/20
            pnl=FVal('0.007945406'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613865623,    # 2021/02/21
            pnl=FVal('0.011105614'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613952023,    # 2021/02/22
            pnl=FVal('0.007780681'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1614038423,    # 2021/02/23
            pnl=FVal('0.007687101'),
        )]
        assert stats == expected_stats
        assert sum_pnl == sum(x.pnl for x in expected_stats)

        with database.conn.read_ctx() as cursor:
            # Make sure that calling it again does not make an external call
            stats, filter_total_found, sum_pnl = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=filter_query,
                only_cache=False,
            )
        assert stats_call.call_count == 1
        assert stats[:len(expected_stats)] == expected_stats

        # Check that changing ownership proportion works
        proportion = FVal(0.45)
        with database.user_write() as write_cursor:
            dbeth2.edit_validator_ownership(
                write_cursor=write_cursor,
                validator_index=validator_index,
                ownership_proportion=proportion,
            )
        with database.conn.read_ctx() as cursor:
            stats, filter_total_found, _ = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=filter_query,
                only_cache=False,
            )
        last_stat = stats[-1]
        assert last_stat.pnl == expected_stats[-1].pnl * proportion
        # TODO: The new sum_pnl here is not changing as ownership proportion is not taken into account here  # noqa: E501


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_genesis_event(
        network_mocking: bool,
        price_historian: 'PriceHistorian',  # pylint: disable=unused-argument
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
) -> None:
    """
    Test that if profit returned by beaconchain on genesis is > 32 ETH the app
    handles it correctly.
    """
    validator_index = 999
    beaconchain = BeaconChain(database, messages_aggregator)
    with mock_query_validator_daily_stats(beaconchain, network_mocking):
        stats = beaconchain.query_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=Timestamp(0),
            exit_ts=None,
        )
    assert stats == [
        ValidatorDailyStats(
            validator_index=999,
            timestamp=Timestamp(1606780823),  # day after eth2 genesis
            pnl=FVal('0.012007402'),
            ownership_percentage=ONE,
        ), ValidatorDailyStats(
            validator_index=999,
            timestamp=Timestamp(1606694423),
            pnl=ZERO,
            ownership_percentage=ONE,
        ),
    ]


@pytest.mark.skipif('CI' in os.environ, reason='do not run this in CI as it spams')
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_query_genesis_validator_stats_all(
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
        price_historian,
):  # pylint: disable=unused-argument
    """A test to see that the scraper of daily stats goes to the very first day of
    genesis for old validators despite UI actually showing pages"""
    beaconchain = BeaconChain(database, messages_aggregator)
    stats = beaconchain.query_validator_daily_stats(
        validator_index=1,
        last_known_timestamp=Timestamp(0),
        exit_ts=None,
    )
    assert len(stats) >= 861
    assert stats[-1].timestamp == 1606694423


@pytest.mark.freeze_time('2024-06-20 19:55:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.vcr(filter_query_parameters=['apikey'])
def test_querying_daily_stats_twice(
        database: DBHandler,
        messages_aggregator: MessagesAggregator,
        price_historian: 'PriceHistorian',
        eth2: 'Eth2',
):  # pylint: disable=unused-argument
    """Test that querying the daily stats twice doesn't trigger a network
    request the second time"""
    eth2.add_validator(validator_index=1118010, public_key=None, ownership_proportion=ONE)
    with eth2.database.conn.cursor() as cursor:
        stats, _, _ = eth2.get_validator_daily_stats(
            cursor=cursor,
            filter_query=Eth2DailyStatsFilterQuery.make(),
            only_cache=False,
        )
        assert len(stats) > 100

        with patch(
            'rotkehlchen.chain.ethereum.modules.eth2.beacon.BeaconInquirer.query_validator_daily_stats',
            wraps=eth2.beacon_inquirer.query_validator_daily_stats,
        ) as patched_query:
            eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=Eth2DailyStatsFilterQuery.make(),
                only_cache=False,
            )
            assert patched_query.call_count == 0


@pytest.mark.parametrize('eth2_mock_data', [{
    'eth1': {
        ADDR1: [
            ('0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b', True, 9),  # noqa: E501
        ],
        ADDR2: [
            ('0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475', True, 1647),  # noqa: E501
            ('0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35', True, 997),  # noqa: E501
        ],
    }, 'validator': [
        {
            'activationeligibilityepoch': 0,
            'activationepoch': 0,
            'balance': 32012290563,
            'effectivebalance': 32000000000,
            'exitepoch': 9223372036854775807,
            'lastattestationslot': 8250797,
            'name': '',
            'pubkey': '0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b',  # noqa: E501
            'slashed': False,
            'status': 'active_online',
            'validatorindex': 9,
            'withdrawableepoch': 9223372036854775807,
            'withdrawalcredentials': '0x004c7691c2085648f394ffaef851f3b1d51b95f7263114bc923fc5338f5fc499',  # noqa: E501
            'total_withdrawals': 4392252178,
        }, {
            'activationeligibilityepoch': 0,
            'activationepoch': 0,
            'balance': 32012290563,
            'effectivebalance': 32000000000,
            'exitepoch': 9223372036854775807,
            'lastattestationslot': 8250797,
            'name': '',
            'pubkey': '0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35',  # noqa: E501
            'slashed': False,
            'status': 'active_online',
            'validatorindex': 997,
            'withdrawableepoch': 9223372036854775807,
            'withdrawalcredentials': '0x010000000000000000000000347ac2e04dd10cbf70f65c058ac3a078d4d9e0e5',  # noqa: E501
            'total_withdrawals': 4392252178,
        }, {
            'activationeligibilityepoch': 0,
            'activationepoch': 0,
            'balance': 32012290563,
            'effectivebalance': 32000000000,
            'exitepoch': 9223372036854775807,
            'lastattestationslot': 8250797,
            'name': '',
            'pubkey': '0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475',  # noqa: E501
            'slashed': False,
            'status': 'active_online',
            'validatorindex': 1647,
            'withdrawableepoch': 9223372036854775807,
            'withdrawalcredentials': '0x01000000000000000000000000f8a0d8ee1c21151bccb416bca1c152f9952d19',  # noqa: E501
            'total_withdrawals': 4392252178,
        }, {
            'activationeligibilityepoch': 0,
            'activationepoch': 0,
            'balance': 32012290563,
            'effectivebalance': 32000000000,
            'exitepoch': 9223372036854775807,
            'lastattestationslot': 8250797,
            'name': '',
            'pubkey': '0xac3d4d453d58c6e6fd5186d8f231eb00ff5a753da3669c208157419055c7c562b7e317654d8c67783c656a956927209d',  # noqa: E501
            'slashed': False,
            'status': 'active_online',
            'validatorindex': 1757,
            'withdrawableepoch': 9223372036854775807,
            'withdrawalcredentials': '0x01000000000000000000000000f8a0d8ee1c21151bccb416bca1c152f9952d19',  # noqa: E501
            'total_withdrawals': 4392252178,
        },
    ],
}])
def test_ownership_proportion(eth2: 'Eth2', database):
    """
    Test that the ownership proportion is correct when querying validators. If proportion is
    customized then the custom value should be used. Otherwise the proportion should be ONE.
    """
    dbeth2 = DBEth2(database)
    validators = [
        ValidatorDetails(
            validator_index=9,
            public_key=Eth2PubKey('0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'),
            ownership_proportion=FVal(0.5),
            validator_type=ValidatorType.BLS,
        ), ValidatorDetails(
            validator_index=1647,
            public_key=Eth2PubKey('0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475'),
            ownership_proportion=FVal(0.7),
            validator_type=ValidatorType.DISTRIBUTING,
        ), ValidatorDetails(  # This validator is tracked but not owned by any of the addresses
            validator_index=1757,
            public_key=Eth2PubKey('0xac3d4d453d58c6e6fd5186d8f231eb00ff5a753da3669c208157419055c7c562b7e317654d8c67783c656a956927209d'),
            ownership_proportion=FVal(0.9),
            validator_type=ValidatorType.DISTRIBUTING,
        ),
    ]
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, validators)

    result = eth2.get_validators(ignore_cache=True, addresses=[ADDR1, ADDR2], validator_indices=None)  # noqa: E501
    assert result[0].validator_index == 9 and result[0].ownership_proportion == FVal(0.5), 'Proportion from the DB should be used'  # noqa: E501
    assert result[1].validator_index == 1647 and result[1].ownership_proportion == FVal(0.7), 'Proportion from the DB should be used'  # noqa: E501
    assert result[2].validator_index == 1757 and result[2].ownership_proportion == FVal(0.9), 'Proportion from the DB should be used'  # noqa: E501
    assert result[3].validator_index == 997 and result[3].ownership_proportion == ONE, 'Since this validator is new, the proportion should be ONE'  # noqa: E501

    # also test filtering by index
    result = eth2.get_validators(ignore_cache=True, addresses=[], validator_indices={9, 1757})
    assert [x.validator_index for x in result] == [9, 1757]


def test_deposits_pubkey_re(eth2: 'Eth2', database):
    dbevents = DBHistoryEvents(database)
    pubkey1 = Eth2PubKey('0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda')  # noqa: E501
    pubkey2 = Eth2PubKey('0x96dab7564980306b3052649e523747fb613ebf91308a788350bbd16435f55f8d3a7090a2ec73fe636eed66ada6e52ad5')  # noqa: E501
    tx_hash1 = make_evm_tx_hash()
    tx_hash2 = make_evm_tx_hash()
    with database.user_write() as cursor:
        dbevents.add_history_events(
            write_cursor=cursor,
            history=[EvmEvent(
                tx_hash=tx_hash1,
                sequence_index=0,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                location_label=ADDR1,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal(32),
                notes=f'Deposit 32 ETH to validator with pubkey {pubkey1}. Deposit index: 519464. Withdrawal credentials: 0x00c5af874f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8',  # noqa: E501
                counterparty=CPT_ETH2,
            ), EvmEvent(
                tx_hash=tx_hash1,
                sequence_index=1,
                timestamp=TimestampMS(2),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.01'),
                notes='Some fees',
                counterparty=CPT_GAS,
            ), EvmEvent(
                tx_hash=tx_hash2,
                sequence_index=0,
                timestamp=TimestampMS(3),
                location=Location.ETHEREUM,
                location_label=ADDR2,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal(32),
                notes=f'Deposit 32 ETH to validator with pubkey {pubkey2}. Deposit index: 529464. Withdrawal credentials: 0x00a5a0074f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8',  # noqa: E501
                counterparty=CPT_ETH2,
            )],
        )

    result = eth2._get_saved_pubkey_to_deposit_address()
    assert len(result) == 2
    assert result[pubkey1] == ADDR1
    assert result[pubkey2] == ADDR2


@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b', '0xF4fEae08C1Fa864B64024238E33Bfb4A3Ea7741d']])  # noqa: E501
@pytest.mark.parametrize('eth2_mock_data', [{
    'validator': [
        {'data_can_be_anything_here': 'with length of list being 2 (validators)'},
        {'thatswhy': 'wehavetwo. Normally these should have been validator data response'},
    ],

}])
def test_eth_validators_performance(eth2, database, ethereum_accounts):
    """Test that the performance of all multiple validators is returned fine"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    vindex1 = 45555
    vindex1_address = ethereum_accounts[0]
    vindex2 = 114543
    vindex2_address = ethereum_accounts[1]
    mev_builder_address = string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990')
    block_number = 15824493
    tx_hash = deserialize_evm_tx_hash('0x8d0969db1e536969ba2e29abf8e8945e4304d49ae14523b66cbe9be5d52df804')  # noqa: E501
    # tx_hash_2 doesn't exist. Only here for testing
    tx_hash_2 = deserialize_evm_tx_hash('0x8d0969db1e536969ba2e29abf8e8945e4304d49ae14523b66cbe9be5d52df805')  # noqa: E501
    block_reward_1 = FVal('0.2')
    block_reward_2 = FVal('0.3')
    no_mev_block_reward_2 = FVal('0.8')
    mev_reward_1 = FVal('4')
    mev_reward_2 = FVal('3')
    withdrawal_1 = FVal('5')
    exit_1 = FVal('33')
    timestampms = TimestampMS(1666693607000)

    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, validators=[
            ValidatorDetails(
                validator_index=vindex1,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a13223088320656fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),
            ), ValidatorDetails(
                validator_index=vindex2,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xa41a0224e73270cee8e06a9984aa2cd902a20e66c8bb528caae602a7caf76c417d0bdf2ab3b6e50a579fa7d98c6d240c'),
            ),
        ])

        dbevents.add_history_events(write_cursor, [
            EthBlockEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                amount=block_reward_1,
                fee_recipient=vindex1_address,
                fee_recipient_tracked=True,
                block_number=block_number,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=vindex1,
                timestamp=TimestampMS(timestampms + (1 * (HOUR_IN_SECONDS * 1000))),
                amount=mev_reward_1,
                fee_recipient=vindex1_address,
                fee_recipient_tracked=True,
                block_number=block_number,
                is_mev_reward=True,
            ), EthBlockEvent(
                validator_index=vindex2,
                timestamp=TimestampMS(timestampms + (2 * (HOUR_IN_SECONDS * 1000))),
                amount=block_reward_2,  # since mev builder gets it we shouldn't count it
                fee_recipient=mev_builder_address,
                fee_recipient_tracked=False,
                block_number=block_number + 1,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=vindex2,
                timestamp=TimestampMS(timestampms + (3 * (HOUR_IN_SECONDS * 1000))),
                amount=mev_reward_2,
                fee_recipient=vindex2_address,
                fee_recipient_tracked=True,
                block_number=block_number + 1,
                is_mev_reward=True,
            ), EvmEvent(
                tx_hash=tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(timestampms + (4 * (HOUR_IN_SECONDS * 1000))),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.MEV_REWARD,
                asset=A_ETH,
                amount=mev_reward_1,
                location_label=vindex1_address,
                notes=f'Received {mev_reward_1} ETH from {mev_builder_address}',
                extra_data={'validator_index': vindex1},
            ), EvmEvent(
                tx_hash=tx_hash_2,
                sequence_index=0,
                timestamp=TimestampMS(timestampms + (5 * (HOUR_IN_SECONDS * 1000))),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.MEV_REWARD,
                asset=A_ETH,
                amount=mev_reward_2,
                location_label=vindex2_address,
                notes=f'Received {mev_reward_2} ETH from {mev_builder_address}',
                extra_data={'validator_index': vindex2},
            ), EthWithdrawalEvent(
                validator_index=vindex1,
                timestamp=TimestampMS(timestampms + (6 * (HOUR_IN_SECONDS * 1000))),
                amount=withdrawal_1,
                withdrawal_address=vindex1_address,
                is_exit=False,
            ), EthBlockEvent(
                identifier=8,
                validator_index=vindex2,
                timestamp=TimestampMS(timestampms + (7 * (HOUR_IN_SECONDS * 1000))),
                amount=no_mev_block_reward_2,
                fee_recipient=vindex2_address,
                fee_recipient_tracked=True,
                block_number=16212625,
                is_mev_reward=False,
            ), EthWithdrawalEvent(
                identifier=9,
                validator_index=vindex1,
                timestamp=TimestampMS(timestampms + (36 * (HOUR_IN_SECONDS * 1000))),
                amount=exit_1,
                withdrawal_address=vindex1_address,
                is_exit=True,
            ),
        ])

    def check_performance_validator(performance, vindex, check_keys, expected_data, expected_apr):
        for check_key in check_keys:
            assert performance['validators'][vindex][check_key] == expected_data[check_key]
            assert performance['validators'][vindex]['apr'].is_close(expected_apr)

    performance = eth2.get_performance(from_ts=Timestamp(0), to_ts=Timestamp(1706866836), limit=10, offset=0, ignore_cache=True)  # noqa: E501

    assert set(performance.keys()) == {'sums', 'validators', 'entries_found', 'entries_total'}
    expected_sums = {
        'execution_blocks': block_reward_1 + no_mev_block_reward_2,
        'execution_mev': mev_reward_1 + mev_reward_2,
        'exits': exit_1 - 32,
        'sum': block_reward_1 + mev_reward_1 + withdrawal_1 + (exit_1 - 32) + mev_reward_2 + no_mev_block_reward_2,   # noqa: E501
        'withdrawals': withdrawal_1,
    }
    for check_key, check_value in expected_sums.items():
        assert performance['sums'][check_key] == check_value
    assert performance['sums']['apr'].is_close(FVal('0.00404161581589250586388450985171054082159224751613839429006282479554837399160762'))  # noqa: E501

    assert set(performance['validators'].keys()) == {vindex1, vindex2}
    expected_vindex1 = {
        'execution_blocks': block_reward_1,
        'execution_mev': mev_reward_1,
        'exits': exit_1 - 32,
        'sum': block_reward_1 + mev_reward_1 + withdrawal_1 + (exit_1 - 32),
    }
    check_performance_validator(performance, vindex1, ('execution_blocks', 'execution_mev', 'exits', 'sum'), expected_vindex1, FVal('0.00588921161744336568737457149820678805432013209494451739409154470208477353062825'))  # noqa: E501
    expected_vindex2 = {
        'execution_blocks': no_mev_block_reward_2,
        'execution_mev': mev_reward_2,
        'sum': mev_reward_2 + no_mev_block_reward_2,
    }
    check_performance_validator(performance, vindex2, ('execution_blocks', 'execution_mev', 'sum'), expected_vindex2, FVal('0.00219402001434164604039444820521429358886436293733227118603410488901197445258700'))  # noqa: E501

    # Check pagination and that cache works
    performance = eth2.get_performance(from_ts=Timestamp(0), to_ts=Timestamp(1706866836), limit=1, offset=0, ignore_cache=False)  # noqa: E501
    assert set(performance['validators'].keys()) == {vindex1}
    check_performance_validator(performance, vindex1, ('execution_blocks', 'execution_mev', 'exits', 'sum'), expected_vindex1, FVal('0.00588921161744336568737457149820678805432013209494451739409154470208477353062825'))  # noqa: E501

    performance = eth2.get_performance(from_ts=Timestamp(0), to_ts=Timestamp(1706866836), limit=2, offset=1, ignore_cache=False)  # noqa: E501
    assert set(performance['validators'].keys()) == {vindex2}
    check_performance_validator(performance, vindex2, ('execution_blocks', 'execution_mev', 'sum'), expected_vindex2, FVal('0.00219402001434164604039444820521429358886436293733227118603410488901197445258700'))  # noqa: E501

    # check that filtering by an unknown address returns nothing
    performance = eth2.get_performance(from_ts=Timestamp(0), to_ts=Timestamp(1706866836), limit=10, offset=0, addresses=[make_evm_address()], ignore_cache=True)  # noqa: E501
    assert performance['entries_found'] == 0
    assert performance['entries_total'] == 2
    assert performance['sums'] == {}
    assert performance['validators'] == {}


@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_eth_accumulating_validators_performance(
        eth2: 'Eth2',
        database: 'DBHandler',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that the performance of accumulating validators is handled correctly.

    Validators:
    1. Accumulating - Target for consolidations.
    2. Distributing - Consolidated into validator 1
    3. Accumulating - Consolidated into validator 1 after a 64 ETH deposit
    4. Accumulating - Exits with pnl with an effective balance > 32

    Events:
    - initial deposits of 32 ETH to each validator
    - deposit of 64 ETH to validator 3
    - deposit of 10 ETH to validator 4
    - skimming withdrawal of 0.02 ETH from validator 3
    - partial withdrawal (via EL request) of 4 ETH from validator 3
    - consolidation of validators 2 and 3 into validator 1
    - exit of validator 4
    - block reward of 0.05 ETH for validator 1
    """
    eth2.premium._cached_limits = {'eth_staked_limit': 8096}  # type: ignore  # todo: Set those by fixture. ignore is since we only set the one relevant limit
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    validators = [(validator1 := ValidatorDetails(
        validator_index=1073521,
        validator_type=ValidatorType.ACCUMULATING,
        public_key=Eth2PubKey('0xae44b0684220d51d11726e09115b1a9068147755bfa8dcb67fa208f6178a251c2450cc7072d75976ef5c32ab3acd8e68'),
    )), (validator2 := ValidatorDetails(
        validator_index=67929,
        validator_type=ValidatorType.DISTRIBUTING,
        public_key=Eth2PubKey('0x99e7ae8ad91b8f8fa447554858481980a57da7e93bcf49d92acadcec2e689e98b4e8c25a2f1fbb1ad337c3d4711fd977'),
    )), (validator3 := ValidatorDetails(
        validator_index=47086,
        validator_type=ValidatorType.ACCUMULATING,
        public_key=Eth2PubKey('0x97662e211e8eb3fa64ffd73ada75cfd6d14078aef7f1138d6430abb38d4d1d1b91191f18470e6e467dd4c125f73a9f48'),
    )), (validator4 := ValidatorDetails(
        validator_index=1672457,
        validator_type=ValidatorType.ACCUMULATING,
        public_key=Eth2PubKey('0x8ad15ca10be31b7fb7ad6e87f721b7311f535b3e47dc7e6e25d9c6f904a35fc0964b3ab581bb162ac474653236b5f9a6'),
    ))]

    tx_hash_1, timestamp, user_address, hour_in_ms = make_evm_tx_hash(), TimestampMS(1746119141000), ethereum_accounts[0], ts_sec_to_ms(Timestamp(HOUR_IN_SECONDS))  # noqa: E501
    events: list[HistoryBaseEntry] = [EthDepositEvent(
        tx_hash=tx_hash_1,
        validator_index=validator.validator_index,  # type: ignore[arg-type]  # validator_index has been set
        sequence_index=idx,
        timestamp=timestamp,
        amount=MIN_EFFECTIVE_BALANCE,
        depositor=user_address,
    ) for idx, validator in enumerate(validators)]
    events.extend([EthDepositEvent(
        tx_hash=make_evm_tx_hash(),
        validator_index=validator3.validator_index,  # type: ignore[arg-type]
        sequence_index=1,
        timestamp=TimestampMS(timestamp + (1 * hour_in_ms)),
        amount=FVal('64'),
        depositor=user_address,
    ), EthDepositEvent(
        tx_hash=make_evm_tx_hash(),
        validator_index=validator4.validator_index,  # type: ignore[arg-type]
        sequence_index=1,
        timestamp=TimestampMS(timestamp + (1 * hour_in_ms)),
        amount=(second_deposit := FVal('10')),
        depositor=user_address,
    ), EthWithdrawalEvent(
        validator_index=validator3.validator_index,  # type: ignore[arg-type]
        timestamp=TimestampMS(timestamp + (2 * hour_in_ms)),
        amount=(skim_amount := FVal('0.02')),
        withdrawal_address=user_address,
        is_exit=False,
    ), EvmEvent(
        tx_hash=make_evm_tx_hash(),
        sequence_index=1,
        timestamp=TimestampMS(timestamp + (3 * hour_in_ms)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_ETH,
        amount=(withdrawal_amount := FVal('4')),
        location_label=user_address,
        notes=f'Request to withdraw {withdrawal_amount} ETH from validator {validator3.validator_index}',  # noqa: E501
        counterparty=CPT_ETH2,
        address=WITHDRAWAL_REQUEST_CONTRACT,
        extra_data={'validator_index': validator3.validator_index},
    ), EthWithdrawalEvent(
        validator_index=validator3.validator_index,  # type: ignore[arg-type]
        timestamp=TimestampMS(timestamp + (36 * hour_in_ms)),
        amount=withdrawal_amount,
        withdrawal_address=user_address,
        is_exit=False,
    ), EthWithdrawalEvent(
        validator_index=validator4.validator_index,  # type: ignore[arg-type]
        timestamp=TimestampMS(timestamp + (72 * hour_in_ms)),
        amount=MIN_EFFECTIVE_BALANCE + second_deposit + (exit_amount := FVal('0.01')),
        withdrawal_address=user_address,
        is_exit=True,
    ), EthBlockEvent(
        validator_index=validator1.validator_index,  # type: ignore[arg-type]
        timestamp=TimestampMS(timestamp + (75 * hour_in_ms)),
        amount=(block_reward := FVal('0.05')),
        fee_recipient=user_address,
        fee_recipient_tracked=True,
        block_number=33333,
        is_mev_reward=False,
    )])
    events.extend([EvmEvent(
        tx_hash=make_evm_tx_hash(),
        sequence_index=1,
        timestamp=TimestampMS(timestamp + (40 * hour_in_ms)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.CONSOLIDATE,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        counterparty=CPT_ETH2,
        address=CONSOLIDATION_REQUEST_CONTRACT,
        extra_data={
            'source_validator_index': validator.validator_index,
            'target_validator_index': validator1.validator_index,
        },
    ) for validator in (validator2, validator3)])

    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, validators)
        dbevents.add_history_events(write_cursor, events)

    with patch.object(eth2.premium, 'is_active', return_value=True):  # needed to use the premium limit  # noqa: E501
        assert eth2.get_performance(
            from_ts=ts_ms_to_sec(timestamp),
            to_ts=ts_ms_to_sec(TimestampMS(timestamp + (100 * hour_in_ms))),
            limit=10,
            offset=0,
            ignore_cache=True,
        ) == {
            'validators': {
                validator3.validator_index: {'withdrawals': skim_amount, 'sum': skim_amount, 'apr': FVal('0.0188793103448275862068965517241379310344827586206896551724137931034482758620690')},  # noqa: E501
                validator4.validator_index: {'exits': exit_amount, 'sum': exit_amount, 'apr': FVal('0.0290643662906436629064366290643662906436629064366290643662906436629064366290644')},  # noqa: E501
                validator1.validator_index: {'execution_blocks': block_reward, 'sum': block_reward, 'apr': FVal('0.0411654135338345864661654135338345864661654135338345864661654135338345864661654')},  # noqa: E501
            },
            'sums': {
                'withdrawals': skim_amount,
                'sum': skim_amount + exit_amount + block_reward,
                'exits': exit_amount,
                'execution_blocks': block_reward,
                'apr': FVal('0.0297030300564352785264995314407796027147703595303844353349566167667297663190996'),  # noqa: E501
            },
            'entries_total': 4,
            'entries_found': 3,
        }


@pytest.mark.vcr
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b', '0xF4fEae08C1Fa864B64024238E33Bfb4A3Ea7741d']])  # noqa: E501
def test_eth_validators_performance_recent(eth2, database, ethereum_accounts):
    """Test that performance to recent time also takes into account outstanding consensus pnl"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    vindex1 = 647202
    vindex2 = 647205
    block_reward_1 = FVal('0.2')

    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, validators=[
            ValidatorDetails(
                validator_index=vindex1,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0x8f1e2e85780c76baede1331c1b5050b7ef752014d24eac669542051ff066dff263753bc033030ccb3c6cfdcc73de0757'),
            ), ValidatorDetails(
                validator_index=vindex2,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0x845fd413c7c5fc2073437d423167f41a51c7f13343c8beb71d5cad2092036ff8277570aec8ba9467aee7ca352dd19d87'),
            ),
        ])
        dbevents.add_history_events(write_cursor, [  # add single event to one of them
            EthBlockEvent(  # to see combining with other fields works
                validator_index=vindex1,
                timestamp=TimestampMS(1666693607000),
                amount=block_reward_1,
                fee_recipient=ethereum_accounts[0],
                fee_recipient_tracked=True,
                block_number=15824493,
                is_mev_reward=False,
            ),
        ])

    outstanding_pnl_v1 = FVal('0.000234828')
    outstanding_pnl_v2 = FVal('0.000232698')
    performance = eth2.get_performance(from_ts=Timestamp(0), to_ts=ts_now(), limit=10, offset=0, ignore_cache=False)  # noqa: E501

    # Pop out APRs to compare separately
    sums_apr = performance['sums'].pop('apr')
    vindex1_apr = performance['validators'][vindex1].pop('apr')
    vindex2_apr = performance['validators'][vindex2].pop('apr')

    # Check the rest of the dict
    assert performance == {
        'entries_found': 2,
        'entries_total': 2,
        'sums': {
            'execution_blocks': block_reward_1,
            'outstanding_consensus_pnl': outstanding_pnl_v1 + outstanding_pnl_v2,
            'sum': block_reward_1 + outstanding_pnl_v1 + outstanding_pnl_v2,
        }, 'validators': {
            vindex1: {
                'execution_blocks': block_reward_1,
                'outstanding_consensus_pnl': outstanding_pnl_v1,
                'sum': block_reward_1 + outstanding_pnl_v1,
            }, vindex2: {
                'outstanding_consensus_pnl': outstanding_pnl_v2,
                'sum': outstanding_pnl_v2,
            },
        },
    }

    # Check APRs separately with is_close
    assert sums_apr.is_close(FVal('0.0000563343374354938274757423808642722178406443566732779649187925545876083487124555'), max_diff=1e-8)  # noqa: E501
    assert vindex1_apr.is_close(FVal('0.00011253789171708606449971303386732112296831511920433901600306536566456522874236'), max_diff=1e-8)  # noqa: E501
    assert vindex2_apr.is_close(FVal('1.30783153901590451771727861223312712973594142216913834519743510651468682550518E-7'), max_diff=1e-8)  # noqa: E501


def test_combine_block_with_tx_events(eth2, database):
    """Small unit test to see the logic of the DB query to detect and modify eth2
    mev reward events works"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    dbevmtx = DBEvmTx(database)
    vindex1 = 45555
    vindex1_address = string_to_evm_address('0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b')
    mev_builder_address = string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990')
    block_number = 15824493
    tx_hash = deserialize_evm_tx_hash('0x8d0969db1e536969ba2e29abf8e8945e4304d49ae14523b66cbe9be5d52df804')  # noqa: E501
    mev_reward = FVal('0.126458404824519798')
    timestampms = TimestampMS(1666693607000)

    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [
            ValidatorDetails(
                validator_index=vindex1,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a1322308832065v6fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),
            ),
        ])
        database.add_blockchain_accounts(write_cursor, [BlockchainAccountData(chain=SupportedBlockchain.ETHEREUM, address=vindex1_address)])  # noqa: E501

        dbevmtx.add_evm_transactions(
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash,
                chain_id=ChainID.ETHEREUM,
                timestamp=Timestamp(1666693607),
                block_number=block_number,
                from_address=mev_builder_address,
                to_address=vindex1_address,
                value=126458404824519798,
                gas=27500,
                gas_price=9213569214,
                gas_used=0,  # irrelevant
                input_data=b'',  # irrelevant
                nonce=16239,
            )],
            relevant_address=vindex1_address,
        )

        dbevents.add_history_events(write_cursor, [
            EthBlockEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                amount=FVal('0.126419309459217215'),
                fee_recipient=mev_builder_address,
                fee_recipient_tracked=True,
                block_number=block_number,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                amount=mev_reward,
                fee_recipient=vindex1_address,
                fee_recipient_tracked=True,
                block_number=block_number,
                is_mev_reward=True,
            ), EvmEvent(
                tx_hash=tx_hash,
                sequence_index=0,
                timestamp=timestampms,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=mev_reward,
                location_label=vindex1_address,
                notes=f'Received {mev_reward} ETH from {mev_builder_address}',
            ),
        ])

    eth2.combine_block_with_tx_events()

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
                        group_by_event_ids=False,
        )

    modified_event = EvmEvent(
        identifier=3,
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestampms,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.MEV_REWARD,
        asset=A_ETH,
        amount=mev_reward,
        location_label=vindex1_address,
        notes=f'Received {mev_reward} ETH from {mev_builder_address} as mev reward for block {block_number} in {tx_hash.hex()}',  # pylint: disable=no-member  # noqa: E501
        event_identifier=EthBlockEvent.form_event_identifier(block_number),
        extra_data={'validator_index': vindex1},
    )
    assert modified_event == events[2]

    with database.conn.read_ctx() as cursor:
        hidden_ids = dbevents.get_hidden_event_ids(cursor)
        assert hidden_ids == [2]


@pytest.mark.vcr
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-04-30 21:52:55 GMT')
def test_refresh_activated_validators_deposits(eth2, database):
    """Test that if an eth deposit event is missing the index, the redetection task works"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    validator1 = ValidatorDetails(
        validator_index=30932,
        validator_type=ValidatorType.DISTRIBUTING,
        public_key=Eth2PubKey('0xa7d4c301a02b7dc747c0f8ff32579226588c7771e133e9b2817cc7a9a977f0004dbee4f4f7f89451a1f5f761e3bb8c81'),
    )
    validator2 = ValidatorDetails(
        validator_index=207003,
        validator_type=ValidatorType.DISTRIBUTING,
        public_key=Eth2PubKey('0x989620ffd512c08907841e28a2c472bbfad2e57c73f474814bf64bab3ae3b44436b1db7b05e4ccc1eb2c3f949a546278'),
    )
    validator3 = ValidatorDetails(
        validator_index=4523,
        validator_type=ValidatorType.BLS,
        public_key=Eth2PubKey('0x967c17368bcb6a90164d1af369115b3bf265b82c350fc78d9b1fa9389f2a216867ca02121f21c4be121f334ce2ac7f4f'),
    )
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [validator1])  # first one is active and in DB at time of deposit decoding  # noqa: E501

    starting_events = [EthDepositEvent(
        identifier=1,
        tx_hash=make_evm_tx_hash(),
        validator_index=validator1.validator_index,
        sequence_index=1,
        timestamp=TimestampMS(360000),
        amount=FVal(32),
        depositor=string_to_evm_address('0xA3E5ff1230a38243BB64Dc1423Df40B63a4CA0c3'),
    ), EthDepositEvent(
        identifier=2,
        tx_hash=make_evm_tx_hash(),
        validator_index=UNKNOWN_VALIDATOR_INDEX,  # actual value should be 207003
        sequence_index=2,
        timestamp=TimestampMS(460000),
        amount=FVal(32),
        depositor=string_to_evm_address('0xf879704602696cD6a567eA569F5D95b4dd51b5FD'),
        extra_data={'public_key': validator2.public_key},
    ), EthDepositEvent(
        identifier=3,
        tx_hash=make_evm_tx_hash(),
        validator_index=UNKNOWN_VALIDATOR_INDEX,  # actual value should be 4523
        sequence_index=3,
        timestamp=TimestampMS(660000),
        amount=FVal(32),
        depositor=string_to_evm_address('0xFCD50905214325355A57aE9df084C5dd40D5D478'),
        extra_data={'public_key': validator3.public_key},
    )]

    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, starting_events)

    eth2.refresh_activated_validators_deposits()

    with database.conn.read_ctx() as cursor:
        new_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    # make sure validator indices have been detected for the deposits
    assert isinstance(new_events, list)
    assert len(starting_events) == len(new_events)
    assert starting_events[0] == new_events[0], 'first event should not have been modified'
    edited_event_2 = starting_events[1]
    edited_event_2.extra_data = None
    edited_event_2.validator_index = validator2.validator_index
    edited_event_2.notes = f'Deposit 32 ETH to validator {validator2.validator_index}'
    assert edited_event_2 == new_events[1]
    edited_event_3 = starting_events[2]
    edited_event_3.extra_data = None
    edited_event_3.validator_index = validator3.validator_index
    edited_event_3.notes = f'Deposit 32 ETH to validator {validator3.validator_index}'
    assert edited_event_3 == new_events[2]

    # finally make sure validators are also added
    with database.conn.read_ctx() as cursor:
        assert set(dbeth2.get_validators(cursor)) == {validator3, validator1, validator2}


@pytest.mark.vcr
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2024-02-04 09:00:00 GMT')
def test_query_chunked_endpoint_with_offset_pagination(eth2):
    """This test makes sure that offset pagination works fine for beaconchain queries.

    It tries to do this by testing for block productions
    """
    validator_indices = range(450000, 450000 + 194)
    result = eth2.beacon_inquirer.beaconchain._query_chunked_endpoint_with_pagination(
        indices=validator_indices,
        module='execution',
        endpoint='produced',
        limit=50,
    )
    assert len(result) == 946  # with the offset bug it was 251 (only first chunk worked)


def test_validator_daily_stats_empty(database):
    dbeth2 = DBEth2(database)
    with database.conn.read_ctx() as cursor:
        result = dbeth2.get_validator_daily_stats_and_limit_info(cursor, Eth2DailyStatsFilterQuery.make())  # noqa: E501

    assert result == ([], 0, ZERO)


def test_get_active_validator_indices(database):
    active_index, exited_index, noevents_index = 1, 575645, 4242
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [
            ValidatorDetails(
                validator_index=active_index,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c'),
            ), ValidatorDetails(
                validator_index=exited_index,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0x800041b1eff8af7a583caa402426ffe8e5da001615f5ce00ba30ea8e3e627491e0aa7f8c0417071d5c1c7eb908962d8e'),
                withdrawable_timestamp=Timestamp(1699801559),
                exited_timestamp=Timestamp(1699976207000),
            ), ValidatorDetails(
                validator_index=noevents_index,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288'),
            ),
        ])

    with database.conn.read_ctx() as cursor:
        assert dbeth2.get_active_validator_indices(cursor) == {active_index, noevents_index}


@pytest.mark.vcr(
    filter_query_parameters=['apikey'],
    match_on=['beaconchain_matcher'],
)
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2024-02-15 13:00:00 GMT')
def test_refresh_validator_data_after_v40_v41_upgrade(eth2):
    """In v40->v41 upgrade the validator table changed, and more columns were added.
    Most of them were optional but in normal operation they would be detected.
    Adding this test to make sure this happens.

    Also testing that foreign key relation with daily stats is not causing all daily
    stats for the
    """
    with eth2.database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO eth2_validators('
            'validator_index, public_key, validator_type, ownership_proportion) VALUES(?, ?, ?, ?)',  # noqa: E501
            [
                (42, '0xb0fee189ffa7ddb3326ef685c911f3416e15664ff1825f3b8e542ba237bd3900f960cd6316ef5f8a5adbaf4903944013', 1, '1.0'),  # noqa: E501
                (1232, '0xa15f29dd50327bc53b02d34d7db28f175ffc21d7ffbb2646c8b1b82bb6bca553333a19fd4b9890174937d434cc115ace', 1, '0.35'),  # noqa: E501
                (5231, '0xb052a2b421770b99c2348b652fbdc770b2a27a87bf56993dff212d839556d70e7b68f5d953133624e11774b8cb81129d', 1, '1.0'),  # noqa: E501
            ],
        )
        write_cursor.executemany(
            'INSERT OR IGNORE INTO eth2_daily_staking_details(validator_index, timestamp, pnl)'
            'VALUES(?, ?, ?)', [
                (42, 1707998469, '0.01'),
                (1232, 1707998469, '0.01'),
                (5231, 1707998469, '0.01'),
            ],
        )
        assert write_cursor.execute('SELECT COUNT(*) from eth2_daily_staking_details').fetchone()[0] == 3  # noqa: E501

    eth2.detect_and_refresh_validators([])

    with eth2.database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT * from eth2_validators').fetchall() == [
            (1, 42, '0xb0fee189ffa7ddb3326ef685c911f3416e15664ff1825f3b8e542ba237bd3900f960cd6316ef5f8a5adbaf4903944013', '1.0', '0x42751916BD8e4ef1966ca033D4EA1FA2a8563f88', 1, 1606824023, None, None),  # noqa: E501
            (2, 1232, '0xa15f29dd50327bc53b02d34d7db28f175ffc21d7ffbb2646c8b1b82bb6bca553333a19fd4b9890174937d434cc115ace', '0.35', '0x009Ec7D76feBECAbd5c73CB13f6d0FB83e45D450', 1, 1606824023, None, None),  # noqa: E501
            (3, 5231, '0xb052a2b421770b99c2348b652fbdc770b2a27a87bf56993dff212d839556d70e7b68f5d953133624e11774b8cb81129d', '1.0', '0x5675801e9346eA8165e7Eb80dcCD01dCa65c0f3A', 1, 1606824023, None, None),  # noqa: E501
        ]
        assert cursor.execute('SELECT COUNT(*) from eth2_daily_staking_details').fetchone()[0] == 3


@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b']])
def test_clean_cache_on_account_removal(
        ethereum_accounts: list['ChecksumEvmAddress'],
        database: 'DBHandler',
) -> None:
    """Test that last withdrawal query timestamps are removed from the cache when """
    with database.conn.write_ctx() as write_cursor:
        database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.WITHDRAWALS_TS,
            address=ethereum_accounts[0],
            value=Timestamp(1739807677),
        )
        database.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.ETHEREUM,
            accounts=ethereum_accounts,
        )
        assert database.get_dynamic_cache(
            cursor=write_cursor,
            name=DBCacheDynamic.WITHDRAWALS_TS,
            address=ethereum_accounts[0],
        ) is None


@pytest.mark.parametrize('eth2_mock_data', [{
    'validator': [{'data_can_be_anything_here': 'with length of list being 1 (validator)'}],

}])
def test_staking_performance_division_by_zero_protection(eth2) -> None:
    """Test that division by zero is prevented when time_weighted_avg is zero in APR calculation"""
    dbevents, dbeth2 = DBHistoryEvents(eth2.database), DBEth2(eth2.database)
    with eth2.database.conn.write_ctx() as write_cursor:
        dbeth2.add_or_update_validators(
            write_cursor=write_cursor,
            validators=[(validator := ValidatorDetailsWithStatus(
                activation_timestamp=Timestamp(1606824023),
                validator_index=(v_index := 999999),
                public_key=Eth2PubKey('0xb912072ccf65435991175736cd73bcb4b2852a993f7d00c4bf3abab5fcfacbd72b37114320a60d9894eaced1ddee1cae'),
                withdrawal_address=make_evm_address(),
                status=ValidatorStatus.ACTIVE,
                validator_type=ValidatorType.DISTRIBUTING,
            ))],
        )

    with eth2.database.conn.write_ctx() as write_cursor:
        dbevents.add_history_events(
            write_cursor=write_cursor,
            history=[EthWithdrawalEvent(
                identifier=1,
                validator_index=v_index,
                timestamp=TimestampMS(1631379127000),
                amount=ONE,
                withdrawal_address=make_evm_address(),
                is_exit=False,
            )],
        )

    with (
        patch('rotkehlchen.chain.ethereum.modules.eth2.beacon.BeaconInquirer.get_validator_data', return_value=[validator]),  # noqa: E501
        patch('rotkehlchen.chain.ethereum.modules.eth2.eth2.Eth2._time_weighted_average', return_value=ZERO),  # noqa: E501
    ):
        result = eth2.get_performance(
            from_ts=Timestamp(1631378127),
            to_ts=Timestamp(1631379927),
            limit=100,
            offset=0,
            validator_indices=[v_index],
            ignore_cache=True,
        )
        validator_apr = result['validators'][v_index]
        assert FVal(validator_apr['sum']) == ONE
        assert FVal(validator_apr['withdrawals']) == ONE
        assert FVal(validator_apr['apr']) == ZERO


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0xa966b01E2136953DF4F4914CfA9D37724E99a187']])
def test_validator_details_update(
        eth2: 'Eth2',
        database: 'DBHandler',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    """Test that validator details are properly updated."""
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=(v_index := 765881),
            validator_type=ValidatorType.DISTRIBUTING,  # Will be updated to accumulating
            public_key=(pub_key := Eth2PubKey('0x8f4bbc39e8319c17050fd94bb609bc21b5f45d2208de5ecf73fc5f38cccfdd434aefb13ed77dea5c1745fa76b627a8af')),  # noqa: E501
        )])

    assert eth2.get_validators(
        ignore_cache=True,
        addresses=[withdrawal_address := ethereum_accounts[0]],
        validator_indices={v_index},
    ) == [ValidatorDetailsWithStatus(
        validator_index=v_index,
        validator_type=ValidatorType.ACCUMULATING,
        public_key=pub_key,
        withdrawal_address=withdrawal_address,
        activation_timestamp=Timestamp(1690165463),
        status=ValidatorStatus.ACTIVE,
    )]


def test_consolidated_validator_pending_withdrawal_outstanding_rewards(
        eth2: 'Eth2',
        database: 'DBHandler',
) -> None:
    """Test that consolidated validators with pending withdrawals don't show negative outstanding rewards"""  # noqa: E501
    with database.user_write() as write_cursor:
        DBEth2(database).add_or_update_validators(write_cursor, [ValidatorDetails(
            validator_index=(validator_index := 999999),
            validator_type=ValidatorType.DISTRIBUTING,  # consolidated/exited validator
            public_key=(pub_key := Eth2PubKey('0xb912072ccf65435991175736cd73bcb4b2852a993f7d00c4bf3abab5fcfacbd72b37114320a60d9894eaced1ddee1cae')),  # noqa: E501
        )])

    with (
        patch('rotkehlchen.chain.ethereum.modules.eth2.beacon.BeaconInquirer.get_balances', return_value={pub_key: Balance(amount=(small_balance := FVal('0.5')), usd_value=small_balance)}),  # mock a small balance (pending withdrawal) that's less than MIN_EFFECTIVE_BALANCE  # noqa: E501
        patch('rotkehlchen.chain.ethereum.modules.eth2.eth2.DBEth2.group_validators_by_type', return_value=(set(), set())),  # no accumulating validators  # noqa: E501
    ):
        result = eth2.get_performance(
            from_ts=Timestamp(0),
            to_ts=ts_now(),
            limit=10,
            offset=0,
            ignore_cache=True,
        )
        assert result['validators'][validator_index]['outstanding_consensus_pnl'] == small_balance
        assert result['sums']['outstanding_consensus_pnl'] == small_balance
