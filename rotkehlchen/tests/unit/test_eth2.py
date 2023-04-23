import os
import re
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryEvent
from rotkehlchen.accounting.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2
from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator, ValidatorDailyStats
from rotkehlchen.chain.ethereum.modules.eth2.utils import (
    DAY_AFTER_ETH2_GENESIS,
    scrape_validator_daily_stats,
    scrape_validator_withdrawals,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import Eth2PubKey, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now, ts_now_in_ms

if TYPE_CHECKING:
    from rotkehlchen.history.price import PriceHistorian
    from rotkehlchen.user_messages import MessagesAggregator

ADDR1 = string_to_evm_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
ADDR2 = string_to_evm_address('0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19')
ADDR3 = string_to_evm_address('0x3266F3546a1e5Dc6A15588f3324741A0E20a3B6c')


ADDR1_VALIDATOR_RESPONSE = [
    ('0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b', True, 9),  # noqa: E501
    ('0x95502842e458b73046a5d9cda10211814c63e859f4519a8ecb289c5ad3e1519663b614bb784c08e8b7373fdcf0bdc077', True, 480926),  # noqa: E501
    ('0x915290d8b3674cbd061ad50ddae59f4674b03fe8b8b8d68bbb5570718de09dfc464608e0db91fcd0b80479aa68d37aa9', True, 481101),  # noqa: E501
    ('0xaa9c8a2653f08b3045fdb63547bfe1ad2a66225f7402717bde9897cc163840ee190ed31c78819db372253332bba3c570', True, 482198),  # noqa: E501
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
    assert db.get_validators_to_query_for_stats(1617512800 + DAY_IN_SECONDS * 2 + 2) == [(2, 0), (3, 1617512800)]  # noqa: E501


DAILY_STATS_RE = re.compile(r'https://beaconcha.in/validator/(\d+)/stats')


def mock_scrape_validator_daily_stats(network_mocking: bool):

    def mock_scrape(url, **kwargs):  # pylint: disable=unused-argument
        match = DAILY_STATS_RE.search(url)
        if match is None:
            raise AssertionError(f'Unexpected validator stats query in test: {url}')

        validator_index = int(match.group(1))
        root_path = Path(__file__).resolve().parent.parent.parent
        file_path = root_path / 'tests' / 'data' / 'mocks' / 'test_eth2' / 'validator_daily_stats' / f'{validator_index}.html'  # noqa: E501

        with open(file_path) as f:
            data = f.read()

        return MockResponse(200, data)

    return patch(
        'rotkehlchen.chain.ethereum.modules.eth2.utils.requests.get',
        side_effect=mock_scrape if network_mocking else requests.get,
    )


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats(network_mocking, price_historian, function_scope_messages_aggregator):  # pylint: disable=unused-argument  # noqa: E501
    validator_index = 33710

    with mock_scrape_validator_daily_stats(network_mocking):
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
        network_mocking,
        price_historian,
        function_scope_messages_aggregator,
):
    validator_index = 33710
    with mock_scrape_validator_daily_stats(network_mocking):
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
        network_mocking,
):
    validator_index = 33710
    public_key = '0x9882b4c33c0d5394205b12d62952c50fe03c6c9fe08faa36425f70afb7caac0689dcd981af35d0d03defb8286d50911d'  # noqa: E501
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_validators(write_cursor, [
            Eth2Validator(
                index=validator_index,
                public_key=public_key,
                ownership_proportion=ONE,
            ),
        ])

    with mock_scrape_validator_daily_stats(network_mocking) as stats_call:
        filter_query = Eth2DailyStatsFilterQuery.make(
            validators=[validator_index],
            from_ts=1613606300,
            to_ts=1614038500,
        )
        with database.conn.read_ctx() as cursor:
            stats, filter_total_found, sum_pnl, sum_usd_value = eth2.get_validator_daily_stats(
                cursor=cursor,
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

        with database.conn.read_ctx() as cursor:
            # Make sure that calling it again does not make an external call
            stats, filter_total_found, _, _ = eth2.get_validator_daily_stats(
                cursor=cursor,
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
        with database.conn.read_ctx() as cursor:
            stats, filter_total_found, _, _ = eth2.get_validator_daily_stats(
                cursor=cursor,
                filter_query=filter_query,
                only_cache=False,
                msg_aggregator=function_scope_messages_aggregator,
            )
        last_stat = stats[:len(expected_stats)][-1]
        assert last_stat.pnl_balance.amount == expected_stats[-1].pnl_balance.amount * FVal(0.45)  # noqa: E501


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_genesis_event(
        network_mocking: bool,
        price_historian: 'PriceHistorian',  # pylint: disable=unused-argument
        function_scope_messages_aggregator: 'MessagesAggregator',
) -> None:
    """
    Test that if profit returned by beaconchain on genesis is > 32 ETH the app
    handles it correctly.
    """
    validator_index = 999

    with mock_scrape_validator_daily_stats(network_mocking):
        stats = scrape_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=Timestamp(0),
            msg_aggregator=function_scope_messages_aggregator,
        )
    assert stats == [
        ValidatorDailyStats(
            validator_index=999,
            timestamp=DAY_AFTER_ETH2_GENESIS,
            start_amount=FVal('0'),
            end_amount=FVal('32.01201'),
            pnl=FVal('0.01201'),
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            missed_attestations=2,
            ownership_percentage=ONE,
        ), ValidatorDailyStats(
            validator_index=999,
            timestamp=Timestamp(1606694400),
            start_amount=ZERO,
            end_amount=ZERO,
            pnl=ZERO,
            amount_deposited=FVal(32),
            deposits_number=1,
            start_usd_price=FVal(1.55),
            end_usd_price=FVal(1.55),
            ownership_percentage=ONE,
        ),
    ]


@pytest.mark.skipif('CI' in os.environ, reason='do not run this in CI as it spams')
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_scrape_genesis_validator_stats_all(price_historian, function_scope_messages_aggregator):  # noqa: E501 # pylint: disable=unused-argument
    """A test to see that the scraper of daily stats goes to the very first day of
    genesis for old validators despite UI actually showing pages"""
    stats = scrape_validator_daily_stats(
        validator_index=1,
        last_known_timestamp=Timestamp(0),
        msg_aggregator=function_scope_messages_aggregator,
    )
    assert len(stats) >= 861
    assert stats[-1].timestamp == 1606694400


@pytest.mark.parametrize('eth2_mock_data', [{
    'eth1': {
        ADDR1: [
            ('0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b', True, 9),  # noqa: E501
        ],
        ADDR2: [
            ('0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475', True, 1647),  # noqa: E501
            ('0x946ec21927a99d0c86cd63a0fd37cc378f869aae83098fac68d41e3fb58326ce2e9f81f1d116d14d1c0bd50cb61f0e35', True, 997),  # noqa: E501
        ],
    },
}])
def test_ownership_proportion(eth2: 'Eth2', database):
    """
    Test that the ownership proportion is correct when querying validators. If proportion is
    customized then the custom value should be used. Otherwise the proportion should be ONE.
    """
    dbeth2 = DBEth2(database)
    with database.user_write() as cursor:
        dbeth2.add_validators(cursor, [
            Eth2Validator(
                index=9,
                public_key=Eth2PubKey('0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'),  # noqa: E501
                ownership_proportion=FVal(0.5),
            ),
            Eth2Validator(
                index=1647,
                public_key=Eth2PubKey('0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475'),  # noqa: E501
                ownership_proportion=FVal(0.7),
            ),
            Eth2Validator(  # This validator is tracked but not owned by any of the addresses
                index=1757,
                public_key=Eth2PubKey('0xac3d4d453d58c6e6fd5186d8f231eb00ff5a753da3669c208157419055c7c562b7e317654d8c67783c656a956927209d'),  # noqa: E501
                ownership_proportion=FVal(0.9),
            ),
        ])
    result = eth2.fetch_and_update_eth1_validator_data(addresses=[ADDR1, ADDR2])
    assert result[0].index == 9 and result[0].ownership_proportion == FVal(0.5), 'Proportion from the DB should be used'  # noqa: E501
    assert result[1].index == 1647 and result[1].ownership_proportion == FVal(0.7), 'Proportion from the DB should be used'  # noqa: E501
    assert result[2].index == 1757 and result[2].ownership_proportion == FVal(0.9), 'Proportion from the DB should be used'  # noqa: E501
    assert result[3].index == 997 and result[3].ownership_proportion == ONE, 'Since this validator is new, the proportion should be ONE'  # noqa: E501


def test_deposits_pubkey_re(eth2: 'Eth2', database):
    dbevents = DBHistoryEvents(database)
    pubkey1 = Eth2PubKey('0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda')  # noqa: E501
    pubkey2 = Eth2PubKey('0x96dab7564980306b3052649e523747fb613ebf91308a788350bbd16435f55f8d3a7090a2ec73fe636eed66ada6e52ad5')  # noqa: E501
    with database.user_write() as cursor:
        dbevents.add_history_events(
            write_cursor=cursor,
            history=[EvmEvent(
                event_identifier=b'1',
                sequence_index=0,
                timestamp=TimestampMS(1),
                location=Location.ETHEREUM,
                location_label=ADDR1,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                balance=Balance(amount=FVal(32)),
                notes=f'Deposit 32 ETH to validator with pubkey {pubkey1}. Deposit index: 519464. Withdrawal credentials: 0x00c5af874f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8',  # noqa: E501
                counterparty=CPT_ETH2,
            ), EvmEvent(
                event_identifier=b'1',
                sequence_index=1,
                timestamp=TimestampMS(2),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                balance=Balance(amount=FVal('0.01')),
                notes='Some fees',
                counterparty=CPT_GAS,
            ), EvmEvent(
                event_identifier=b'2',
                sequence_index=0,
                timestamp=TimestampMS(3),
                location=Location.ETHEREUM,
                location_label=ADDR2,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                balance=Balance(amount=FVal(32)),
                notes=f'Deposit 32 ETH to validator with pubkey {pubkey2}. Deposit index: 529464. Withdrawal credentials: 0x00a5a0074f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8',  # noqa: E501
                counterparty=CPT_ETH2,
            )],
        )

    result = eth2._get_saved_pubkey_to_deposit_address()
    assert len(result) == 2
    assert result[pubkey1] == ADDR1
    assert result[pubkey2] == ADDR2


def test_scrape_validator_withdrawals():
    """Simple test for withdrawal scraping.
    Uses goerli since mainnet has few withdrawals for pagination.

    TODO: Switch to mainnet later(?) and add VCR
    """
    goerli_url = patch(
        'rotkehlchen.chain.ethereum.modules.eth2.utils.BEACONCHAIN_ROOT_URL',
        new='https://goerli.beaconcha.in',
    )
    goerli_start = patch(
        'rotkehlchen.chain.ethereum.modules.eth2.utils.ETH2_GENESIS_TIMESTAMP',
        new=1616508000,
    )

    last_known_timestamp = ts_now() - 20 * DAY_IN_SECONDS  # so we have ~2-3 pages
    with goerli_url, goerli_start:
        withdrawal_data = scrape_validator_withdrawals(270410, last_known_timestamp)

    assert len(withdrawal_data) >= 20, 'should have multiple pages'
    for entry in withdrawal_data:
        assert isinstance(entry[0], int)
        assert entry[0] > last_known_timestamp
        assert entry[1] == '0xBC86717BaD3F8CcF86d2882a6bC351C94580A994'
        assert isinstance(entry[2], FVal)


def test_get_validators_to_query_for_withdrawals(database):
    db = DBEth2(database)
    dbevents = DBHistoryEvents(database)
    now_ms = ts_now_in_ms()
    address1 = make_evm_address()
    address2 = make_evm_address()
    assert db.get_validators_to_query_for_withdrawals(now_ms) == []

    with database.user_write() as write_cursor:  # first add some validators
        db.add_validators(write_cursor, [
            Eth2Validator(
                index=1,
                public_key=Eth2PubKey('0xf001'),
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=2,
                public_key=Eth2PubKey('0xf002'),
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=3,
                public_key=Eth2PubKey('0xf003'),
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=42,
                public_key=Eth2PubKey('0xf0042'),
                ownership_proportion=ONE,
            ),
        ])

    # now check that all need to be queried since we have no withdrawals
    assert db.get_validators_to_query_for_withdrawals(now_ms) == [(1, 0), (2, 0), (3, 0), (42, 0)]

    with database.user_write() as write_cursor:  # now add some withdrawals in the DB
        withdrawal1 = EthWithdrawalEvent(
            validator_index=1,
            timestamp=TimestampMS(1),
            balance=Balance(1, 1),
            withdrawal_address=address1,
            is_exit=False,
        )
        withdrawal1.identifier = dbevents.add_history_event(write_cursor, withdrawal1)
        withdrawal2 = EthWithdrawalEvent(
            validator_index=42,
            timestamp=TimestampMS(now_ms - 3600 * 1000),
            balance=Balance(1, 1),
            withdrawal_address=address2,
            is_exit=False,
        )
        withdrawal2.identifier = dbevents.add_history_event(write_cursor, withdrawal2)
        withdrawal3 = EthWithdrawalEvent(
            validator_index=2,
            timestamp=TimestampMS(20),
            balance=Balance(2, 1),
            withdrawal_address=address1,
            is_exit=False,
        )
        withdrawal3.identifier = dbevents.add_history_event(write_cursor, withdrawal3)
        exit1 = EthWithdrawalEvent(
            validator_index=3,
            timestamp=TimestampMS(30),
            balance=Balance(FVal('32.0023'), 1),
            withdrawal_address=address1,
            is_exit=True,
        )
        exit1.identifier = dbevents.add_history_event(write_cursor, exit1)
        exit2 = EthWithdrawalEvent(
            validator_index=46,
            timestamp=TimestampMS(now_ms - 3600 * 1000 * 1.5),
            balance=Balance(FVal('32.0044'), 1),
            withdrawal_address=address2,
            is_exit=True,
        )
        exit2.identifier = dbevents.add_history_event(write_cursor, exit2)

        # add some other events to make sure table populated with non-withdrawals doesn't mess up
        dbevents.add_history_event(write_cursor, HistoryEvent(
            event_identifier=b'id1',
            sequence_index=0,
            timestamp=TimestampMS(10),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_DAI,
            balance=Balance(1, 1),
        ))
        dbevents.add_history_event(write_cursor, HistoryEvent(
            event_identifier=b'id2',
            sequence_index=0,
            timestamp=TimestampMS(now_ms - 1300 * 1000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_DAI,
            balance=Balance(1, 1),
        ))

    result = db.get_validators_to_query_for_withdrawals(now_ms)
    assert result == [(1, 1), (2, 20), (3, 30)]


@pytest.mark.vcr()
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-04-23 00:52:55 GMT')
def test_withdrawals(eth2: 'Eth2', database):
    """Test that when withdrawals are queried, they are properly saved in the DB"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    with database.user_write() as write_cursor:
        dbeth2.add_validators(write_cursor, [
            Eth2Validator(  # this has exited
                index=7287,
                public_key=Eth2PubKey('0xb7763831fdf87f3ee728e60a579cf2be889f6cc89a4878c8651a2a267377cf7e9406b4bcd8f664b88a3e20c368155bf6'),  # noqa: E501
                ownership_proportion=ONE,
            ), Eth2Validator(  # this has exited
                index=7288,
                public_key=Eth2PubKey('0x92db89739c6a3529facf858223b8872bbcf150c4bf3b30eb21ab8b09d4ea2f4d7b07b949a27d9766c70807d3b18ad934'),  # noqa: E501
                ownership_proportion=ONE,
            ), Eth2Validator(  # this is active and has withdrawals
                index=295601,
                public_key=Eth2PubKey('0xab82f22254143786651a1600ce747f22f79bb3c3b016f7a2564e104ffb16af409fc3a8bb48b0ba012454a79c3460f5ae'),  # noqa: E501
                ownership_proportion=ONE,
            ), Eth2Validator(  # this is active and has withdrawals
                index=295603,
                public_key=Eth2PubKey('0x97777229490da343d0b7e661eda342fe1083e35a5c4076da76297ccac08cea6e2c8520fad2afdd4e43d73f0e620cc155'),  # noqa: E501
                ownership_proportion=ONE,
            ),
        ])

    to_ts = ts_now()
    eth2.query_services_for_validator_withdrawals(to_ts=to_ts)

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_all_history_events(cursor, HistoryEventFilterQuery.make(), True, False)  # noqa: E501
        assert events == [EthWithdrawalEvent(
            validator_index=295601,
            timestamp=TimestampMS(1681392599000),
            balance=Balance(amount=FVal('1.631508097')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            validator_index=295603,
            timestamp=TimestampMS(1681392599000),
            balance=Balance(amount=FVal('1.581794994')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            validator_index=7287,
            timestamp=TimestampMS(1681567319000),
            balance=Balance(amount=FVal('36.411594425')),
            withdrawal_address=string_to_evm_address('0x4231B2f83CB7C833Db84ceC0cEAAa9959f051374'),
            is_exit=True,
        ), EthWithdrawalEvent(
            validator_index=7288,
            timestamp=TimestampMS(1681567319000),
            balance=Balance(amount=FVal('36.422259087')),
            withdrawal_address=string_to_evm_address('0x4231B2f83CB7C833Db84ceC0cEAAa9959f051374'),
            is_exit=True,
        ), EthWithdrawalEvent(
            validator_index=295601,
            timestamp=TimestampMS(1681736279000),
            balance=Balance(amount=FVal('0.010870946')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            validator_index=295603,
            timestamp=TimestampMS(1681736279000),
            balance=Balance(amount=FVal('0.010692337')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            validator_index=295601,
            timestamp=TimestampMS(1682110295000),
            balance=Balance(amount=FVal('0.011993962')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            validator_index=295603,
            timestamp=TimestampMS(1682110295000),
            balance=Balance(amount=FVal('0.011965595')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        )]
