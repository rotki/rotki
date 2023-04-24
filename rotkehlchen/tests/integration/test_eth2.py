import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.eth2 import EthBlockEvent
from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.types import Eth2PubKey, TimestampMS


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
        events = dbevents.get_all_history_events(cursor, HistoryEventFilterQuery.make(), True, False)  # noqa: E501

    assert events == [EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1666693607000),
        balance=Balance(FVal('0.126419309459217215')),
        fee_recipient=string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990'),
        block_number=15824493,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1666693607000),
        balance=Balance(FVal('0.126458404824519798')),
        fee_recipient=vindex1_address,
        block_number=15824493,
        is_mev_reward=True,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1668068651000),
        balance=Balance(FVal('0.095134860916352597')),
        fee_recipient=string_to_evm_address('0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5'),
        block_number=15938405,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1668068651000),
        balance=Balance(FVal('0.109978419256414016')),
        fee_recipient=vindex1_address,
        block_number=15938405,
        is_mev_reward=True,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1670267915000),
        balance=Balance(FVal('0.025900962606266958')),
        fee_recipient=vindex2_address,
        block_number=16120623,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1671379127000),
        balance=Balance(FVal('0.02290370247079784')),
        fee_recipient=vindex2_address,
        block_number=16212625,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1674734363000),
        balance=Balance(FVal('0.012922327272245232')),
        fee_recipient=vindex2_address,
        block_number=16490846,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1675143275000),
        balance=Balance(FVal('0.016091543022603308')),
        fee_recipient=vindex2_address,
        block_number=16524748,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1675926299000),
        balance=Balance(FVal('0.156090536122554115')),
        fee_recipient=string_to_evm_address('0xAAB27b150451726EC7738aa1d0A94505c8729bd1'),
        block_number=16589592,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1675926299000),
        balance=Balance(FVal('0.155599501480976115')),
        fee_recipient=vindex1_address,
        block_number=16589592,
        is_mev_reward=True,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1676596919000),
        balance=Balance(FVal('0.004759289463309382')),
        fee_recipient=vindex2_address,
        block_number=16645139,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1681593839000),
        balance=Balance(FVal('0.013231650982632651')),
        fee_recipient=string_to_evm_address('0xFeebabE6b0418eC13b30aAdF129F5DcDd4f70CeA'),
        block_number=17055026,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1681593839000),
        balance=Balance(FVal('0.013233591104431482')),
        fee_recipient=vindex1_address,
        block_number=17055026,
        is_mev_reward=True,
    )]
