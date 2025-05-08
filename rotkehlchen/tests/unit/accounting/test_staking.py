import pytest

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.accounting.pnl import PNL, PnlTotals
from rotkehlchen.chain.ethereum.constants import SHAPPELA_TIMESTAMP
from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDailyStats,
    ValidatorDetails,
    ValidatorType,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent, EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.accounting import accounting_history_process, check_pnls_and_csv
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.tests.utils.messages import no_message_errors
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_sec_to_ms


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize(('db_settings', 'event_start_timestamp', 'expected_pnls'), [
    (
        {'eth_staking_taxable_after_withdrawal_enabled': False},
        1636638550000,
        [FVal('0.25114638241'), FVal('0.22035944359')],
    ), (
        {'eth_staking_taxable_after_withdrawal_enabled': True},
        1636638550000,
        [ZERO, ZERO],
    ), (
        {'eth_staking_taxable_after_withdrawal_enabled': True},
        ts_sec_to_ms(Timestamp(SHAPPELA_TIMESTAMP + 5000)),
        [FVal('0.09452788191'), FVal('0.09206375805')],
    ),
])
def test_kraken_staking_events(accountant, google_service, event_start_timestamp, expected_pnls):
    """
    Test that staking events from kraken are correctly processed
    """
    ts_addition = 3854824000
    history = [
        HistoryEvent(
            event_identifier=b'XXX',
            sequence_index=0,
            timestamp=event_start_timestamp + ts_addition,
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            amount=FVal(0.0000541090),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ), HistoryEvent(
            event_identifier=b'YYY',
            sequence_index=0,
            timestamp=event_start_timestamp,
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            amount=FVal(0.0000541090),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        )]
    _, events = accounting_history_process(
        accountant,
        start_ts=ts_ms_to_sec(event_start_timestamp),
        end_ts=ts_ms_to_sec(event_start_timestamp + 2 * ts_addition),
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls_csv = PnlTotals({
        AccountingEventType.STAKING: PNL(taxable=sum(expected_pnls), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls_csv, google_service)
    assert len(events) == sum(1 for x in expected_pnls if x != ZERO)
    for idx, event in enumerate(events):
        assert event.pnl.taxable == expected_pnls[idx]
        assert event.event_type == AccountingEventType.STAKING


@pytest.mark.parametrize('mocked_price_queries', [prices])
@pytest.mark.parametrize('db_settings', [{
    'eth_staking_taxable_after_withdrawal_enabled': False,
}])
def test_eth_staking_daily_stats(accountant, google_service):
    """Test ethereum staking daily stats are accounted for if the setting to count them is on"""
    history = [
        ValidatorDailyStats(
            validator_index=1,
            timestamp=1607727600,  # ETH price: 449.68 ETH/EUR
            pnl=FVal('0.05'),  # 0.05 * 449.68 = 22.484
        ), ValidatorDailyStats(
            validator_index=1,
            timestamp=1607814000,  # ETH price: 469.82 ETH/EUR
            pnl=FVal('-0.005'),  # -0.005 * 469.82 + 0.005 * 469.82 - 0.005*449.68 = -2.2484
        ), ValidatorDailyStats(
            validator_index=1,
            timestamp=1607900400,  # ETH price: 486.57 ETH/EUR
            pnl=FVal('0.04'),  # 0.04 * 486.57 = 19.4628
        ), ValidatorDailyStats(
            validator_index=2,
            timestamp=1607900400,
            pnl=FVal('0.045'),  # 0.045 * 486.57 = 21.89565
        ),
    ]

    accounting_history_process(
        accountant,
        start_ts=1606727600,
        end_ts=1640493376,
        history_list=history,
    )
    no_message_errors(accountant.msg_aggregator)
    expected_pnls = PnlTotals({  # 22.484 - 2.2484 + 19.4628 + 21.89565
        AccountingEventType.STAKING: PNL(taxable=FVal('61.59405'), free=ZERO),
    })
    check_pnls_and_csv(accountant, expected_pnls, google_service)


@pytest.mark.parametrize('ethereum_accounts', [['0xb8Cbbf78c7Ad1cDF4cA0e111B35491f3bFE027AC']])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_mev_events(accountant: Accountant, ethereum_accounts: list[ChecksumEvmAddress]) -> None:
    """Check that mev rewards and block rewards are correctly processed for accounting when
    they come as events.
    """
    fee_recipient = ethereum_accounts[0]
    events = [
        EthBlockEvent(
            identifier=13674,
            validator_index=610696,
            timestamp=TimestampMS(1687117319000),
            amount=FVal('0.126419309459217215'),
            fee_recipient=fee_recipient,
            fee_recipient_tracked=True,
            block_number=17508810,
            is_mev_reward=False,
        ), HistoryEvent(
            event_identifier='XXX',
            sequence_index=0,
            timestamp=TimestampMS(1687117319001),
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            amount=FVal(0.0000541090),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
    ]
    # Check accounting for a normal block produced without mev
    accountant.process_history(
        start_ts=Timestamp(0),
        end_ts=ts_now(),
        events=events,
    )
    processed_events = accountant.pots[0].processed_events
    assert processed_events[0].notes == 'Block reward of 0.126419309459217215 for block 17508810'
    assert processed_events[1].notes == 'Kraken ETH staking'

    accountant.pots[0].reset(
        settings=accountant.pots[0].settings,
        start_ts=accountant.pots[0].query_start_ts,
        end_ts=accountant.pots[0].query_end_ts,
        report_id=1,
    )
    # now check when a relayer is used and the block fee recipient is different
    mev_amount, mevbot_address, block_number, tx_hash = '0.126458404824519798', string_to_evm_address('0xA69babEF1cA67A37Ffaf7a485DfFF3382056e78C'), 17508810, make_evm_tx_hash()  # noqa: E501
    events = [
        EthBlockEvent(
            identifier=13674,
            validator_index=610696,
            timestamp=TimestampMS(1687117319000),
            amount=FVal('0.126419309459217215'),
            fee_recipient=mevbot_address,
            fee_recipient_tracked=False,
            block_number=block_number,
            is_mev_reward=False,
        ),
        EthBlockEvent(
            identifier=13675,
            validator_index=610696,
            timestamp=TimestampMS(1687117319000),
            amount=FVal(mev_amount),
            fee_recipient=fee_recipient,
            fee_recipient_tracked=True,
            block_number=block_number,
            is_mev_reward=True,
        ), EvmEvent(
            tx_hash=tx_hash,
            event_identifier=f'BP1_{block_number}',
            sequence_index=2,
            timestamp=TimestampMS(1687117319001),
            location=Location.ETHEREUM,
            location_label=fee_recipient,
            address=mevbot_address,
            asset=A_ETH2,
            amount=FVal(mev_amount),
            notes=(mev_notes := f'Receive {mev_amount} ETH from {mevbot_address} as mev reward for block {block_number} in {tx_hash.hex()}'),  # pylint: disable=no-member  # noqa: E501
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.MEV_REWARD,
        ), HistoryEvent(
            event_identifier='XXX',
            sequence_index=0,
            timestamp=TimestampMS(1687117319001),
            location=Location.KRAKEN,
            location_label='Kraken 1',
            asset=A_ETH2,
            amount=FVal(0.0000541090),
            notes=None,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
        ),
    ]

    accountant.process_history(
        start_ts=Timestamp(0),
        end_ts=ts_now(),
        events=events,
    )
    processed_events = accountant.pots[0].processed_events
    assert processed_events[0].notes == mev_notes
    assert processed_events[1].notes == 'Kraken ETH staking'


@pytest.mark.parametrize('ethereum_accounts', [['0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b']])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('use_dummy_pot', [True])
@pytest.mark.parametrize('use_clean_caching_directory', [True])
@pytest.mark.parametrize('db_settings', [{
    'eth_staking_taxable_after_withdrawal_enabled': True,
}])
def test_validator_exit_pnl(
        accountant: Accountant,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Regression test for https://github.com/rotki/rotki/issues/8095. Check that the PnL
    is calculated correctly for validators exiting with a balance over 32 ETH"""
    vindex1 = 45555
    with accountant.db.conn.write_ctx() as write_cursor:
        DBEth2(accountant.db).add_or_update_validators(write_cursor, validators=[
            ValidatorDetails(
                validator_index=vindex1,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a13223088320656fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),
            ),
        ])
    accountant.process_history(
        start_ts=Timestamp(0),
        end_ts=ts_now(),
        events=[
            EthWithdrawalEvent(
                identifier=9,
                validator_index=vindex1,
                timestamp=TimestampMS(1666693607000),
                amount=FVal(33),
                withdrawal_address=ethereum_accounts[0],
                is_exit=True,
            ),
        ],
    )
    assert accountant.pots[0].pnls.taxable == ONE  # 1 ETH
