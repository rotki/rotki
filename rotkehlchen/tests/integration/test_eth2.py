from contextlib import nullcontext
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator
from rotkehlchen.chain.ethereum.modules.eth2.utils import form_withdrawal_notes
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import EthWithdrawalFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent, EthWithdrawalEvent
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x23F02E9272EAc1F12F5be76D48b4a15323778f08', '0xCb2a5c130709a4C6c4BA39368879A523C0060c71',
]])
@pytest.mark.parametrize('query_method', ['etherscan', 'blockscout'])
@pytest.mark.freeze_time('2023-11-19 19:58:00 GMT')
def test_withdrawals(eth2: 'Eth2', database, ethereum_accounts, query_method):
    """Test that when withdrawals are queried, they are properly saved in the DB.

    Test that the sources we can query agree with each other.
    """
    to_ts = ts_now()
    patch_ctx = patch.object(eth2.ethereum.etherscan, 'get_withdrawals', side_effect=RemoteError) if query_method == 'blockscout' else nullcontext()  # noqa: E501

    with patch_ctx:  # type: ignore[attr-defined]
        eth2.query_services_for_validator_withdrawals(addresses=ethereum_accounts, to_ts=to_ts)
    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )

    assert len(events) == 74
    account0_events, account1_events = 0, 0
    for idx, x in enumerate(events):
        assert isinstance(x, EthWithdrawalEvent)
        if x.location_label == ethereum_accounts[0]:
            assert x.validator_index == 583243
            account0_events += 1
        elif x.location_label == ethereum_accounts[1]:
            assert x.validator_index == 582738
            account1_events += 1
        else:
            raise AssertionError('unexpected event')

        x.identifier = 1  # ignore identifiers at equality check
        if idx == 0:  # for some indices check full event
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=582738,
                timestamp=TimestampMS(1682309159000),
                balance=Balance(amount=FVal('0.001188734')),
                withdrawal_address=ethereum_accounts[1],
                is_exit=False,
            )
            continue
        if idx == 1:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=583243,
                timestamp=TimestampMS(1682309531000),
                balance=Balance(amount=FVal('0.001650449')),
                withdrawal_address=ethereum_accounts[0],
                is_exit=False,
            )
            continue
        if idx == 4:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=582738,
                timestamp=TimestampMS(1683060887000),
                balance=Balance(amount=FVal('0.045701079')),
                withdrawal_address=ethereum_accounts[1],
                is_exit=False,
            )
            continue
        if idx == 33:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=583243,
                timestamp=TimestampMS(1688958443000),
                balance=Balance(amount=FVal('0.049877787')),
                withdrawal_address=ethereum_accounts[0],
                is_exit=False,
            )
            continue
        if idx == 66:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=582738,
                timestamp=TimestampMS(1698368939000),
                balance=Balance(amount=FVal('0.016899759')),
                withdrawal_address=ethereum_accounts[1],
                is_exit=False,
            )
            continue
        if idx == 67:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=583243,
                timestamp=TimestampMS(1698369239000),
                balance=Balance(amount=FVal('0.016747361')),
                withdrawal_address=ethereum_accounts[0],
                is_exit=False,
            )
            continue

        assert x.is_exit_or_blocknumber is False
        assert x.asset == A_ETH
        assert isinstance(x.balance.amount, FVal)
        assert FVal('0.01') <= x.balance.amount <= FVal('0.06')

    assert account0_events == 37
    assert account1_events == 37


@pytest.mark.vcr()
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-04-24 21:00:00 GMT')
def test_block_production(eth2: 'Eth2', database):
    """Test that providing validators that have both pure block production and running
    mev-boost works and detects the block production events.
    """
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    vindex1, vindex2 = 45555, 56562
    vindex1_address = string_to_evm_address('0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b')
    vindex2_address = string_to_evm_address('0x76b23B82c8dCf1635a9DF63Fe6D9AafAaF042A9B')
    with database.user_write() as write_cursor:
        dbeth2.add_validators(write_cursor, [
            Eth2Validator(
                index=vindex1,
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a13223088320656fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=vindex2,
                public_key=Eth2PubKey('0x8cd650758f377763bf7ebaf7fe60cb14b4b05f3ffe750820abf4ae70bc4bf25f84ccdff3a92489e1435ebf94768a03f1'),
                ownership_proportion=ONE,
            ),
        ])

    eth2.beaconchain.get_and_store_produced_blocks([vindex1, vindex2])

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )

    assert events == [EthBlockEvent(
        identifier=12,
        validator_index=vindex1,
        timestamp=TimestampMS(1666693607000),
        balance=Balance(FVal('0.126419309459217215')),
        fee_recipient=string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990'),
        block_number=15824493,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=13,
        validator_index=vindex1,
        timestamp=TimestampMS(1666693607000),
        balance=Balance(FVal('0.126458404824519798')),
        fee_recipient=vindex1_address,
        block_number=15824493,
        is_mev_reward=True,
    ), EthBlockEvent(
        identifier=10,
        validator_index=vindex1,
        timestamp=TimestampMS(1668068651000),
        balance=Balance(FVal('0.095134860916352597')),
        fee_recipient=string_to_evm_address('0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5'),
        block_number=15938405,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=11,
        validator_index=vindex1,
        timestamp=TimestampMS(1668068651000),
        balance=Balance(FVal('0.109978419256414016')),
        fee_recipient=vindex1_address,
        block_number=15938405,
        is_mev_reward=True,
    ), EthBlockEvent(
        identifier=9,
        validator_index=vindex2,
        timestamp=TimestampMS(1670267915000),
        balance=Balance(FVal('0.025900962606266958')),
        fee_recipient=vindex2_address,
        block_number=16120623,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=8,
        validator_index=vindex2,
        timestamp=TimestampMS(1671379127000),
        balance=Balance(FVal('0.02290370247079784')),
        fee_recipient=vindex2_address,
        block_number=16212625,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=7,
        validator_index=vindex2,
        timestamp=TimestampMS(1674734363000),
        balance=Balance(FVal('0.012922327272245232')),
        fee_recipient=vindex2_address,
        block_number=16490846,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=6,
        validator_index=vindex2,
        timestamp=TimestampMS(1675143275000),
        balance=Balance(FVal('0.016091543022603308')),
        fee_recipient=vindex2_address,
        block_number=16524748,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=4,
        validator_index=vindex1,
        timestamp=TimestampMS(1675926299000),
        balance=Balance(FVal('0.156090536122554115')),
        fee_recipient=string_to_evm_address('0xAAB27b150451726EC7738aa1d0A94505c8729bd1'),
        block_number=16589592,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=5,
        validator_index=vindex1,
        timestamp=TimestampMS(1675926299000),
        balance=Balance(FVal('0.155599501480976115')),
        fee_recipient=vindex1_address,
        block_number=16589592,
        is_mev_reward=True,
    ), EthBlockEvent(
        identifier=3,
        validator_index=vindex2,
        timestamp=TimestampMS(1676596919000),
        balance=Balance(FVal('0.004759289463309382')),
        fee_recipient=vindex2_address,
        block_number=16645139,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=1,
        validator_index=vindex1,
        timestamp=TimestampMS(1681593839000),
        balance=Balance(FVal('0.013231650982632651')),
        fee_recipient=string_to_evm_address('0xFeebabE6b0418eC13b30aAdF129F5DcDd4f70CeA'),
        block_number=17055026,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=2,
        validator_index=vindex1,
        timestamp=TimestampMS(1681593839000),
        balance=Balance(FVal('0.013233591104431482')),
        fee_recipient=vindex1_address,
        block_number=17055026,
        is_mev_reward=True,
    )]


@pytest.mark.vcr()
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-11-19 16:30:00 GMT')
def test_withdrawals_detect_exit(eth2: 'Eth2', database):
    """Test that detecting an exit for slashed and exited validators work fine"""
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    active_index, exited_index, slashed_index = 1, 575645, 20075
    active_address, exited_address, slashed_address = string_to_evm_address('0x15F4B914A0cCd14333D850ff311d6DafbFbAa32b'), string_to_evm_address('0x08DeB6278D671E2a1aDc7b00839b402B9cF3375d'), string_to_evm_address('0x1f9bB27d0C66fEB932f3F8B02620A128d072f3d8')  # noqa: E501
    slashed_exit_amount, exit_amount = FVal('31.408009'), FVal('32.001442')
    withdrawal_events = [
        EthWithdrawalEvent(
            identifier=1,
            validator_index=slashed_index,
            timestamp=TimestampMS(1680982251000),
            balance=Balance(FVal('0.016073')),
            withdrawal_address=slashed_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=2,
            validator_index=slashed_index,
            timestamp=TimestampMS(1681571243000),
            balance=Balance(slashed_exit_amount),
            withdrawal_address=slashed_address,
            is_exit=False,
        ),
        EthWithdrawalEvent(
            identifier=3,
            validator_index=active_index,
            timestamp=TimestampMS(1699319051000),
            balance=Balance(FVal('0.017197')),
            withdrawal_address=active_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=4,
            validator_index=exited_index,
            timestamp=TimestampMS(1699648427000),
            balance=Balance(FVal('0.017073')),
            withdrawal_address=exited_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=5,
            validator_index=active_index,
            timestamp=TimestampMS(1699976207000),
            balance=Balance(FVal('0.017250')),
            withdrawal_address=active_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=6,
            validator_index=exited_index,
            timestamp=TimestampMS(1699976207000),
            balance=Balance(exit_amount),
            withdrawal_address=exited_address,
            is_exit=False,
        ),
    ]

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
                index=slashed_index,
                public_key=Eth2PubKey('0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288'),
                ownership_proportion=ONE,
            ),
        ])

        dbevents.add_history_events(write_cursor, history=withdrawal_events)

    eth2.detect_exited_validators()
    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )

    # check that the two exits were detected
    withdrawal_events[1].is_exit_or_blocknumber = True  # slashed exit
    withdrawal_events[1].notes = form_withdrawal_notes(is_exit=True, validator_index=slashed_index, amount=slashed_exit_amount)  # noqa: E501
    withdrawal_events[5].is_exit_or_blocknumber = True  # normal exit
    withdrawal_events[5].notes = form_withdrawal_notes(is_exit=True, validator_index=exited_index, amount=exit_amount)  # noqa: E501
    assert withdrawal_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.freeze_time('2023-11-20 07:07:55 GMT')
def test_query_no_withdrawals(
        eth2: 'Eth2',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that if an address has no withdrawals we correctly handle it"""
    etherscan_patch = patch.object(eth2.ethereum.etherscan, 'get_withdrawals', side_effect=eth2.ethereum.etherscan.get_withdrawals)  # noqa: E501
    blockscout_patch = patch.object(eth2.ethereum.blockscout, 'query_withdrawals', side_effect=eth2.ethereum.blockscout.query_withdrawals)  # noqa: E501

    with etherscan_patch as etherscan_mock, blockscout_patch as blockscout_mock:
        eth2.query_single_address_withdrawals(
            address=ethereum_accounts[0],
            to_ts=ts_now(),
        )
        assert etherscan_mock.call_count == 1, 'etherscan should be called once'
        assert blockscout_mock.call_count == 0, 'blockscout should not be called'

    with eth2.database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 0
        assert cursor.execute('SELECT * FROM used_query_ranges').fetchone()[0] == 'ethwithdrawalsts_0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # noqa: E501
