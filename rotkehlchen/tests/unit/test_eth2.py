import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.v1.schemas import EthStakingHistoryStatsProfit
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.eth2.constants import CPT_ETH2, UNKNOWN_VALIDATOR_INDEX
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator, ValidatorDailyStats
from rotkehlchen.chain.ethereum.modules.eth2.utils import (
    DAY_AFTER_ETH2_GENESIS,
    scrape_validator_daily_stats,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
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
from rotkehlchen.utils.misc import ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
    from rotkehlchen.history.price import PriceHistorian

ADDR1 = string_to_evm_address('0xfeF0E7635281eF8E3B705e9C5B86e1d3B0eAb397')
ADDR2 = string_to_evm_address('0x00F8a0D8EE1c21151BCcB416bCa1C152f9952D19')


def test_get_validators_to_query_for_stats(database):
    db = DBEth2(database)
    now = ts_now()
    assert db.get_validators_to_query_for_stats(now) == []
    with database.user_write() as cursor:
        db.add_validators(cursor, [Eth2Validator(index=1, public_key='0xfoo1', ownership_proportion=ONE)])  # noqa: E501
    assert db.get_validators_to_query_for_stats(now) == [(1, 0, None)]

    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=1,
        timestamp=1607126400,
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=1,
        timestamp=1607212800,
        pnl=ZERO,
    )])
    assert db.get_validators_to_query_for_stats(now) == [(1, 1607212800, None)]

    # now add a daily stats entry closer than a day in the past and see we don't query anything
    db.add_validator_daily_stats([ValidatorDailyStats(
        validator_index=1,
        timestamp=now - 3600,
        pnl=ZERO,
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
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=3,
        timestamp=1617512800,
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=4,
        timestamp=1617512800,
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=4,
        timestamp=now - 7200,
        pnl=ZERO,
    )])
    assert db.get_validators_to_query_for_stats(now) == [(2, 0, None), (3, 1617512800, None)]
    assert db.get_validators_to_query_for_stats(1617512800 + DAY_IN_SECONDS * 2 + 2) == [(2, 0, None), (3, 1617512800, None)]  # noqa: E501

    # Let's make validator 3 have an exit after its last stat
    dbevents = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        dbevents.add_history_event(
            write_cursor=write_cursor,
            event=EthWithdrawalEvent(
                validator_index=3,
                timestamp=ts_sec_to_ms(1617512800 + DAY_IN_SECONDS),
                balance=Balance(amount=ONE),
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
                timestamp=ts_sec_to_ms(1617512800),
                balance=Balance(amount=ONE),
                withdrawal_address=make_evm_address(),
                is_exit=True,
            ),
        )
    assert db.get_validators_to_query_for_stats(now) == [(2, 0, None)]


DAILY_STATS_RE = re.compile(r'https://beaconcha.in/validator/(\d+)/stats')


def mock_scrape_validator_daily_stats(network_mocking: bool):

    def mock_scrape(url, **kwargs):  # pylint: disable=unused-argument
        match = DAILY_STATS_RE.search(url)
        if match is None:
            raise AssertionError(f'Unexpected validator stats query in test: {url}')

        validator_index = int(match.group(1))
        root_path = Path(__file__).resolve().parent.parent.parent
        file_path = root_path / 'tests' / 'data' / 'mocks' / 'test_eth2' / 'validator_daily_stats' / f'{validator_index}.html'  # noqa: E501
        return MockResponse(200, file_path.read_text(encoding='utf8'))

    return patch(
        'rotkehlchen.chain.ethereum.modules.eth2.utils.requests.get',
        side_effect=mock_scrape if network_mocking else requests.get,
    )


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats(network_mocking, price_historian):  # pylint: disable=unused-argument
    validator_index = 33710

    with mock_scrape_validator_daily_stats(network_mocking):
        stats = scrape_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=0,
            exit_ts=None,
        )

    assert len(stats) >= 81
    expected_stats = [ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607126400,    # 2020/12/05
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607212800,    # 2020/12/06
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607299200,    # 2020/12/07
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607385600,  # 2020/12/08
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607472000,  # 2020/12/09
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607558400,  # 2020/12/10
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607644800,  # 2020/12/11
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607731200,  # 2020/12/12
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607817600,  # 2020/12/13
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607904000,  # 2020/12/14
        pnl=ZERO,
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1607990400,  # 2020/12/15
        pnl=FVal('0.0119'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608076800,  # 2020/12/16
        pnl=FVal('0.01318'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608163200,  # 2020/12/17
        pnl=FVal('-0.00006'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608249600,  # 2020/12/18
        pnl=FVal('0.01286'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608336000,  # 2020/12/19
        pnl=FVal('0.01267'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608422400,  # 2020/12/20
        pnl=FVal('0.01442'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608508800,  # 2020/12/21
        pnl=FVal('0.01237'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608595200,  # 2020/12/22
        pnl=FVal('0.01213'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608681600,  # 2020/12/23
        pnl=FVal('0.012'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608768000,  # 2020/12/24
        pnl=FVal('0.01194'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1608854400,  # 2020/12/25
        pnl=FVal('0.01174'),
    )]
    stats.reverse()
    assert stats[:len(expected_stats)] == expected_stats

    # make sure that the 24/25 Dec 2022 0 stat, which is after exit is not there
    assert stats[-1].timestamp <= 1671753600
    assert stats[-1].pnl != ZERO
    assert stats[-2].timestamp <= 1671753600
    assert stats[-2].pnl != ZERO


@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_validator_daily_stats_with_last_known_timestamp(network_mocking, price_historian):  # pylint: disable=unused-argument
    validator_index = 33710
    with mock_scrape_validator_daily_stats(network_mocking):
        stats = scrape_validator_daily_stats(
            validator_index=validator_index,
            last_known_timestamp=1613520000,
            exit_ts=None,
        )

    assert len(stats) >= 6
    expected_stats = [ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613606400,    # 2021/02/18
        pnl=FVal('0.00784'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613692800,    # 2021/02/19
        pnl=FVal('0.00683'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613779200,    # 2021/02/20
        pnl=FVal('0.00798'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613865600,    # 2021/02/21
        pnl=FVal('0.01114'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1613952000,    # 2021/02/22
        pnl=FVal('0.00782'),
    ), ValidatorDailyStats(
        validator_index=validator_index,
        timestamp=1614038400,    # 2021/02/23
        pnl=FVal('0.00772'),
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
            timestamp=1613606400,    # 2021/02/18
            pnl=FVal('0.00784'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613692800,    # 2021/02/19
            pnl=FVal('0.00683'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613779200,    # 2021/02/20
            pnl=FVal('0.00798'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613865600,    # 2021/02/21
            pnl=FVal('0.01114'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1613952000,    # 2021/02/22
            pnl=FVal('0.00782'),
        ), ValidatorDailyStats(
            validator_index=validator_index,
            timestamp=1614038400,    # 2021/02/23
            pnl=FVal('0.00772'),
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
        dbeth2.edit_validator(
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
            exit_ts=None,
        )
    assert stats == [
        ValidatorDailyStats(
            validator_index=999,
            timestamp=DAY_AFTER_ETH2_GENESIS,
            pnl=FVal('0.01201'),
            ownership_percentage=ONE,
        ), ValidatorDailyStats(
            validator_index=999,
            timestamp=Timestamp(1606694400),
            pnl=ZERO,
            ownership_percentage=ONE,
        ),
    ]


@pytest.mark.skipif('CI' in os.environ, reason='do not run this in CI as it spams')
@pytest.mark.parametrize('default_mock_price_value', [FVal(1.55)])
def test_scrape_genesis_validator_stats_all(price_historian):  # pylint: disable=unused-argument
    """A test to see that the scraper of daily stats goes to the very first day of
    genesis for old validators despite UI actually showing pages"""
    stats = scrape_validator_daily_stats(
        validator_index=1,
        last_known_timestamp=Timestamp(0),
        exit_ts=None,
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
                public_key=Eth2PubKey('0xb016e31f633a21fbe42a015152399361184f1e2c0803d89823c224994af74a561c4ad8cfc94b18781d589d03e952cd5b'),
                ownership_proportion=FVal(0.5),
            ),
            Eth2Validator(
                index=1647,
                public_key=Eth2PubKey('0xb80777b022a115579f22674883996d0a904e51afaf0ddef4e577c7bc72ec4e14fc7714b8c58fb77ceb7b5162809d1475'),
                ownership_proportion=FVal(0.7),
            ),
            Eth2Validator(  # This validator is tracked but not owned by any of the addresses
                index=1757,
                public_key=Eth2PubKey('0xac3d4d453d58c6e6fd5186d8f231eb00ff5a753da3669c208157419055c7c562b7e317654d8c67783c656a956927209d'),
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
                balance=Balance(amount=FVal(32)),
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
                balance=Balance(amount=FVal('0.01')),
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
                balance=Balance(amount=FVal(32)),
                notes=f'Deposit 32 ETH to validator with pubkey {pubkey2}. Deposit index: 529464. Withdrawal credentials: 0x00a5a0074f28011e2f559e1214131da5f11b12845921b0d8e436f0cd37d683a8',  # noqa: E501
                counterparty=CPT_ETH2,
            )],
        )

    result = eth2._get_saved_pubkey_to_deposit_address()
    assert len(result) == 2
    assert result[pubkey1] == ADDR1
    assert result[pubkey2] == ADDR2


@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b', '0xF4fEae08C1Fa864B64024238E33Bfb4A3Ea7741d']])  # noqa: E501
@pytest.mark.parametrize('ethereum_modules', [['eth2']])
def test_eth_validator_stat_calculation(database, blockchain):
    """Test that filter works correctly and obtains stats for eth staking events"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    vindex1 = 45555
    vindex1_address = string_to_evm_address('0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b')
    vindex2 = 114543
    vindex2_address = string_to_evm_address('0xF4fEae08C1Fa864B64024238E33Bfb4A3Ea7741d')
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
    timestampms = TimestampMS(1666693607000)

    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, [
            EthBlockEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                balance=Balance(block_reward_1),
                fee_recipient=mev_builder_address,
                block_number=block_number,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                balance=Balance(mev_reward_1),
                fee_recipient=vindex1_address,
                block_number=block_number,
                is_mev_reward=True,
            ), EthBlockEvent(
                validator_index=vindex2,
                timestamp=timestampms,
                balance=Balance(block_reward_2),
                fee_recipient=mev_builder_address,
                block_number=block_number + 1,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=vindex2,
                timestamp=timestampms,
                balance=Balance(mev_reward_2),
                fee_recipient=vindex2_address,
                block_number=block_number + 1,
                is_mev_reward=True,
            ), EvmEvent(
                tx_hash=tx_hash,
                sequence_index=0,
                timestamp=timestampms,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                balance=Balance(mev_reward_1),
                location_label=vindex1_address,
                notes=f'Received {mev_reward_1} ETH from {mev_builder_address}',
            ), EvmEvent(
                tx_hash=tx_hash_2,
                sequence_index=0,
                timestamp=timestampms,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                balance=Balance(mev_reward_2),
                location_label=vindex2_address,
                notes=f'Received {mev_reward_2} ETH from {mev_builder_address}',
            ), EthWithdrawalEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                balance=Balance(withdrawal_1),
                withdrawal_address=vindex1_address,
                is_exit=False,
            ),
            EthBlockEvent(
                identifier=8,
                validator_index=vindex2,
                timestamp=TimestampMS(1671379127000),
                balance=Balance(no_mev_block_reward_2),
                fee_recipient=vindex2_address,
                block_number=16212625,
                is_mev_reward=False,
            ),
        ])

    schema = EthStakingHistoryStatsProfit(chains_aggregator=blockchain)

    def _process_data(data: dict[str, Any]) -> dict[str, Any]:
        """Extract filters from marshmallow schema"""
        arguments = schema.load(data)
        return {
            'withdrawals_filter_query': arguments['withdrawals_filter_query'],
            'execution_filter_query': arguments['execution_filter_query'],
        }

    # test a normal query
    assert dbeth2.get_validators_profit(**_process_data({})) == (withdrawal_1, mev_reward_1 + mev_reward_2 + no_mev_block_reward_2)  # noqa: E501
    # test filter by address
    assert dbeth2.get_validators_profit(**_process_data({'addresses': [vindex1_address]})) == (withdrawal_1, mev_reward_1)  # noqa: E501
    # test filter by validator index
    assert dbeth2.get_validators_profit(**_process_data({'validator_indices': [vindex1]})) == (withdrawal_1, mev_reward_1)  # noqa: E501
    # test filter by address with block without mev rewards
    assert dbeth2.get_validators_profit(**_process_data({'validator_indices': [vindex2]})) == (ZERO, mev_reward_2 + no_mev_block_reward_2)  # noqa: E501


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
        dbeth2.add_validators(write_cursor, [
            Eth2Validator(
                index=vindex1,
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a1322308832065v6fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),
                ownership_proportion=ONE,
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
                balance=Balance(FVal('0.126419309459217215')),
                fee_recipient=mev_builder_address,
                block_number=block_number,
                is_mev_reward=False,
            ), EthBlockEvent(
                validator_index=vindex1,
                timestamp=timestampms,
                balance=Balance(mev_reward),
                fee_recipient=vindex1_address,
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
                balance=Balance(mev_reward),
                location_label=vindex1_address,
                notes=f'Received {mev_reward} ETH from {mev_builder_address}',
            ),
        ])

    eth2.combine_block_with_tx_events()

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
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
        balance=Balance(mev_reward),
        location_label=vindex1_address,
        notes=f'Received {mev_reward} ETH from {mev_builder_address} as mev reward for block {block_number}',  # noqa: E501
        event_identifier=EthBlockEvent.form_event_identifier(block_number),
    )
    assert modified_event == events[2]

    with database.conn.read_ctx() as cursor:
        hidden_ids = dbevents.get_hidden_event_ids(cursor)
        assert hidden_ids == [2]


@pytest.mark.vcr()
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-04-30 21:52:55 GMT')
def test_refresh_activated_validators_deposits(eth2, database):
    """Test that if an eth deposit event is missing the index, the redetection task works"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    validator1 = Eth2Validator(
        index=30932,
        public_key=Eth2PubKey('0xa7d4c301a02b7dc747c0f8ff32579226588c7771e133e9b2817cc7a9a977f0004dbee4f4f7f89451a1f5f761e3bb8c81'),
    )
    validator2 = Eth2Validator(
        index=207003,
        public_key=Eth2PubKey('0x989620ffd512c08907841e28a2c472bbfad2e57c73f474814bf64bab3ae3b44436b1db7b05e4ccc1eb2c3f949a546278'),
    )
    validator3 = Eth2Validator(
        index=4523,
        public_key=Eth2PubKey('0x967c17368bcb6a90164d1af369115b3bf265b82c350fc78d9b1fa9389f2a216867ca02121f21c4be121f334ce2ac7f4f'),
    )
    with database.user_write() as write_cursor:
        dbeth2.add_validators(write_cursor, [validator1])  # first one is active and in DB at time of deposit decoding  # noqa: E501

    starting_events = [EthDepositEvent(
        identifier=1,
        tx_hash=make_evm_tx_hash(),
        validator_index=validator1.index,
        sequence_index=1,
        timestamp=360000,
        balance=Balance(FVal(32)),
        depositor=string_to_evm_address('0xA3E5ff1230a38243BB64Dc1423Df40B63a4CA0c3'),
    ), EthDepositEvent(
        identifier=2,
        tx_hash=make_evm_tx_hash(),
        validator_index=UNKNOWN_VALIDATOR_INDEX,  # actual value should be 207003
        sequence_index=2,
        timestamp=460000,
        balance=Balance(FVal(32)),
        depositor=string_to_evm_address('0xf879704602696cD6a567eA569F5D95b4dd51b5FD'),
        extra_data={'public_key': validator2.public_key},
    ), EthDepositEvent(
        identifier=3,
        tx_hash=make_evm_tx_hash(),
        validator_index=UNKNOWN_VALIDATOR_INDEX,  # actual value should be 4523
        sequence_index=3,
        timestamp=660000,
        balance=Balance(FVal(32)),
        depositor=string_to_evm_address('0xFCD50905214325355A57aE9df084C5dd40D5D478'),
        extra_data={'public_key': validator3.public_key},
    )]

    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor, starting_events)

    eth2.refresh_activated_validators_deposits()

    with database.conn.read_ctx() as cursor:
        new_events = dbevents.get_history_events(cursor, HistoryEventFilterQuery.make(), True)

    # make sure validator indices have been detected for the deposits
    assert isinstance(new_events, list)
    assert len(starting_events) == len(new_events)
    assert starting_events[0] == new_events[0], 'first event should not have been modified'
    edited_event_2 = starting_events[1]
    edited_event_2.extra_data = None
    edited_event_2.validator_index = validator2.index
    edited_event_2.notes = f'Deposit 32 ETH to validator {validator2.index}'
    assert edited_event_2 == new_events[1]
    edited_event_3 = starting_events[2]
    edited_event_3.extra_data = None
    edited_event_3.validator_index = validator3.index
    edited_event_3.notes = f'Deposit 32 ETH to validator {validator3.index}'
    assert edited_event_3 == new_events[2]

    # finally make sure validators are also added
    with database.conn.read_ctx() as cursor:
        assert dbeth2.get_validators(cursor) == [validator3, validator1, validator2]


@pytest.mark.vcr()
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-04-30 21:52:55 GMT')
def test_query_chunked_endpoint_with_offset_pagination(eth2):
    """This test makes sure that offset pagination works fine for beaconchain queries.

    It tries to do this by testing for block productions
    """
    validator_indices = range(450000, 450000 + 194)
    result = eth2.beaconchain._query_chunked_endpoint_with_pagination(
        indices_or_pubkeys=validator_indices,
        module='execution',
        endpoint='produced',
        limit=50,
    )
    assert len(result) == 474  # with the offset bug it was 251 (only first chunk worked)


def test_validator_daily_stats_empty(database):
    dbeth2 = DBEth2(database)
    with database.conn.read_ctx() as cursor:
        result = dbeth2.get_validator_daily_stats_and_limit_info(cursor, Eth2DailyStatsFilterQuery.make())  # noqa: E501

    assert result == ([], 0, ZERO)


def test_get_active_validator_indices(database):
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    active_index, exited_index, noevents_index = 1, 575645, 4242
    active_address, exited_address = string_to_evm_address('0x15F4B914A0cCd14333D850ff311d6DafbFbAa32b'), string_to_evm_address('0x08DeB6278D671E2a1aDc7b00839b402B9cF3375d')  # noqa: E501

    with database.user_write() as write_cursor:
        dbeth2.add_validators(write_cursor, [
            Eth2Validator(
                index=active_index,
                public_key=Eth2PubKey('0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c'),
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=exited_index,
                public_key=Eth2PubKey('0x800041b1eff8af7a583caa402426ffe8e5da001615f5ce00ba30ea8e3e627491e0aa7f8c0417071d5c1c7eb908962d8e'),
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=noevents_index,
                public_key=Eth2PubKey('0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288'),
                ownership_proportion=ONE,
            ),
        ])

        dbevents.add_history_events(write_cursor, history=[
            EthWithdrawalEvent(
                validator_index=active_index,
                timestamp=TimestampMS(1699319051000),
                balance=Balance(FVal('0.017197')),
                withdrawal_address=active_address,
                is_exit=False,
            ), EthWithdrawalEvent(
                validator_index=active_index,
                timestamp=TimestampMS(1699976207000),
                balance=Balance(FVal('0.017250')),
                withdrawal_address=active_address,
                is_exit=False,
            ), EthWithdrawalEvent(
                validator_index=exited_index,
                timestamp=TimestampMS(1699648427000),
                balance=Balance(FVal('0.017073')),
                withdrawal_address=exited_address,
                is_exit=False,
            ), EthWithdrawalEvent(
                validator_index=exited_index,
                timestamp=TimestampMS(1699976207000),
                balance=Balance(FVal('32.007250')),
                withdrawal_address=exited_address,
                is_exit=True,
            ),
        ])

    with database.conn.read_ctx() as cursor:
        assert dbeth2.get_active_validator_indices(cursor) == {active_index, noevents_index}
