from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthBlockEvent, EthWithdrawalEvent
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.types import Eth2PubKey, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2


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
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
            has_premium=True,
            group_by_event_ids=False,
        )
        assert events == [EthWithdrawalEvent(
            identifier=5,
            validator_index=295601,
            timestamp=TimestampMS(1681392599000),
            balance=Balance(amount=FVal('1.631508097')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=8,
            validator_index=295603,
            timestamp=TimestampMS(1681392599000),
            balance=Balance(amount=FVal('1.581794994')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=1,
            validator_index=7287,
            timestamp=TimestampMS(1681567319000),
            balance=Balance(amount=FVal('36.411594425')),
            withdrawal_address=string_to_evm_address('0x4231B2f83CB7C833Db84ceC0cEAAa9959f051374'),
            is_exit=True,
        ), EthWithdrawalEvent(
            identifier=2,
            validator_index=7288,
            timestamp=TimestampMS(1681567319000),
            balance=Balance(amount=FVal('36.422259087')),
            withdrawal_address=string_to_evm_address('0x4231B2f83CB7C833Db84ceC0cEAAa9959f051374'),
            is_exit=True,
        ), EthWithdrawalEvent(
            identifier=4,
            validator_index=295601,
            timestamp=TimestampMS(1681736279000),
            balance=Balance(amount=FVal('0.010870946')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=7,
            validator_index=295603,
            timestamp=TimestampMS(1681736279000),
            balance=Balance(amount=FVal('0.010692337')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=3,
            validator_index=295601,
            timestamp=TimestampMS(1682110295000),
            balance=Balance(amount=FVal('0.011993962')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=6,
            validator_index=295603,
            timestamp=TimestampMS(1682110295000),
            balance=Balance(amount=FVal('0.011965595')),
            withdrawal_address=string_to_evm_address('0xB9D7934878B5FB9610B3fE8A5e441e8fad7E293f'),
            is_exit=False,
        )]


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
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a13223088320656fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),  # noqa: E501
                ownership_proportion=ONE,
            ), Eth2Validator(
                index=vindex2,
                public_key=Eth2PubKey('0x8cd650758f377763bf7ebaf7fe60cb14b4b05f3ffe750820abf4ae70bc4bf25f84ccdff3a92489e1435ebf94768a03f1'),  # noqa: E501
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
