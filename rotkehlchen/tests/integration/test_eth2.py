from contextlib import nullcontext
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.ethereum.modules.eth2.structures import ValidatorDetails, ValidatorType
from rotkehlchen.chain.ethereum.modules.eth2.utils import epoch_to_timestamp, form_withdrawal_notes
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.eth2 import DBEth2
from rotkehlchen.db.filtering import EthWithdrawalFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.eth2 import EthBlockEvent, EthWithdrawalEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Eth2PubKey,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.modules.eth2.eth2 import Eth2
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x23F02E9272EAc1F12F5be76D48b4a15323778f08', '0xCb2a5c130709a4C6c4BA39368879A523C0060c71',
]])
@pytest.mark.parametrize('query_method', ['etherscan', 'blockscout'])
@pytest.mark.freeze_time('2024-02-04 23:50:00 GMT')
def test_withdrawals(eth2: 'Eth2', database, ethereum_accounts, query_method):
    """Test that when withdrawals are queried, they are properly saved in the DB.

    Test that the sources we can query agree with each other.
    """
    with database.user_write() as write_cursor:
        # Add validators for both addresses so that withdrawals get queried.
        DBEth2(database).add_or_update_validators(write_cursor, [
            ValidatorDetails(validator_index=1, public_key=Eth2PubKey('0xfoo1'), withdrawal_address=ethereum_accounts[0], validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
            ValidatorDetails(validator_index=2, public_key=Eth2PubKey('0xfoo2'), withdrawal_address=ethereum_accounts[1], validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
        ])

    to_ts = ts_now()
    with (
        patch.object(eth2.ethereum.etherscan, 'get_withdrawals', side_effect=RemoteError) if query_method == 'blockscout' else nullcontext(),  # noqa: E501
        patch.object(eth2, 'detect_exited_validators', side_effect=lambda *args, **kwargs: None),
    ):
        eth2.query_services_for_validator_withdrawals(addresses=ethereum_accounts, to_ts=to_ts)
    dbevents = DBHistoryEvents(database)
    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(),
            group_by_event_ids=False,
        )

    assert len(events) == 94
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
                amount=FVal('0.001188734'),
                withdrawal_address=ethereum_accounts[1],
                is_exit=False,
            )
            continue
        if idx == 1:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=583243,
                timestamp=TimestampMS(1682309531000),
                amount=FVal('0.001650449'),
                withdrawal_address=ethereum_accounts[0],
                is_exit=False,
            )
            continue
        if idx == 4:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=582738,
                timestamp=TimestampMS(1683060887000),
                amount=FVal('0.045701079'),
                withdrawal_address=ethereum_accounts[1],
                is_exit=False,
            )
            continue
        if idx == 33:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=583243,
                timestamp=TimestampMS(1688958443000),
                amount=FVal('0.049877787'),
                withdrawal_address=ethereum_accounts[0],
                is_exit=False,
            )
            continue
        if idx == 66:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=582738,
                timestamp=TimestampMS(1698368939000),
                amount=FVal('0.016899759'),
                withdrawal_address=ethereum_accounts[1],
                is_exit=False,
            )
            continue
        if idx == 67:
            assert x == EthWithdrawalEvent(
                identifier=1,
                validator_index=583243,
                timestamp=TimestampMS(1698369239000),
                amount=FVal('0.016747361'),
                withdrawal_address=ethereum_accounts[0],
                is_exit=False,
            )
            continue

        assert x.is_exit_or_blocknumber is False
        assert x.asset == A_ETH
        assert isinstance(x.amount, FVal)
        assert FVal('0.01') <= x.amount <= FVal('0.06')

    assert account0_events == 47
    assert account1_events == 47


# @pytest.mark.vcr
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2023-04-24 21:00:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [[
    '0x0fdAe061cAE1Ad4Af83b27A96ba5496ca992139b', '0x76b23B82c8dCf1635a9DF63Fe6D9AafAaF042A9B',
]])
def test_block_production(eth2: 'Eth2', database, ethereum_accounts):
    """Test that providing validators that have both pure block production and running
    mev-boost works and detects the block production events.
    """
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    vindex1, vindex2 = 45555, 56562
    vindex1_address, vindex2_address = ethereum_accounts[0], ethereum_accounts[1]
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [
            ValidatorDetails(
                validator_index=vindex1,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xadd9843b2eb53ccaf5afb52abcc0a13223088320656fdfb162360ca53a71ebf8775dbebd0f1f1bf6c3e823d4bf2815f7'),
                ownership_proportion=ONE,
            ), ValidatorDetails(
                validator_index=vindex2,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0x8cd650758f377763bf7ebaf7fe60cb14b4b05f3ffe750820abf4ae70bc4bf25f84ccdff3a92489e1435ebf94768a03f1'),
                ownership_proportion=ONE,
            ),
        ])

    eth2.beacon_inquirer.beaconchain.get_and_store_produced_blocks([vindex1, vindex2])

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(to_ts=Timestamp(1682370000)),
            group_by_event_ids=False,
        )

    expected_events = [EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1666693607000),
        amount=FVal('0.126419309459217215'),
        fee_recipient=string_to_evm_address('0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990'),
        fee_recipient_tracked=False,
        block_number=15824493,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1666693607000),
        amount=FVal('0.126458404824519798'),
        fee_recipient=vindex1_address,
        fee_recipient_tracked=True,
        block_number=15824493,
        is_mev_reward=True,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1668068651000),
        amount=FVal('0.095134860916352597'),
        fee_recipient=string_to_evm_address('0x95222290DD7278Aa3Ddd389Cc1E1d165CC4BAfe5'),
        fee_recipient_tracked=False,
        block_number=15938405,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1668068651000),
        amount=FVal('0.109978419256414016'),
        fee_recipient=vindex1_address,
        fee_recipient_tracked=True,
        block_number=15938405,
        is_mev_reward=True,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1670267915000),
        amount=FVal('0.025900962606266958'),
        fee_recipient=vindex2_address,
        fee_recipient_tracked=True,
        block_number=16120623,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1671379127000),
        amount=FVal('0.02290370247079784'),
        fee_recipient=vindex2_address,
        fee_recipient_tracked=True,
        block_number=16212625,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1674734363000),
        amount=FVal('0.012922327272245232'),
        fee_recipient=vindex2_address,
        fee_recipient_tracked=True,
        block_number=16490846,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1675143275000),
        amount=FVal('0.016091543022603308'),
        fee_recipient=vindex2_address,
        fee_recipient_tracked=True,
        block_number=16524748,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1675926299000),
        amount=FVal('0.156090536122554115'),
        fee_recipient=string_to_evm_address('0xAAB27b150451726EC7738aa1d0A94505c8729bd1'),
        fee_recipient_tracked=False,
        block_number=16589592,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1675926299000),
        amount=FVal('0.155599501480976115'),
        fee_recipient=vindex1_address,
        fee_recipient_tracked=True,
        block_number=16589592,
        is_mev_reward=True,
    ), EthBlockEvent(
        validator_index=vindex2,
        timestamp=TimestampMS(1676596919000),
        amount=FVal('0.004759289463309382'),
        fee_recipient=vindex2_address,
        fee_recipient_tracked=True,
        block_number=16645139,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1681593839000),
        amount=FVal('0.013231650982632651'),
        fee_recipient=string_to_evm_address('0xFeebabE6b0418eC13b30aAdF129F5DcDd4f70CeA'),
        fee_recipient_tracked=False,
        block_number=17055026,
        is_mev_reward=False,
    ), EthBlockEvent(
        validator_index=vindex1,
        timestamp=TimestampMS(1681593839000),
        amount=FVal('0.013233591104431482'),
        fee_recipient=vindex1_address,
        fee_recipient_tracked=True,
        block_number=17055026,
        is_mev_reward=True,
    )]
    for x in events:  # do not compare identifiers
        x.identifier = None
    assert expected_events == events


@pytest.mark.vcr
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
            amount=FVal('0.016073'),
            withdrawal_address=slashed_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=2,
            validator_index=slashed_index,
            timestamp=TimestampMS(1681571243000),
            amount=slashed_exit_amount,
            withdrawal_address=slashed_address,
            is_exit=False,
        ),
        EthWithdrawalEvent(
            identifier=3,
            validator_index=active_index,
            timestamp=TimestampMS(1699319051000),
            amount=FVal('0.017197'),
            withdrawal_address=active_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=4,
            validator_index=exited_index,
            timestamp=TimestampMS(1699648427000),
            amount=FVal('0.017073'),
            withdrawal_address=exited_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=5,
            validator_index=active_index,
            timestamp=TimestampMS(1699976207000),
            amount=FVal('0.017250'),
            withdrawal_address=active_address,
            is_exit=False,
        ), EthWithdrawalEvent(
            identifier=6,
            validator_index=exited_index,
            timestamp=TimestampMS(1699976207000),
            amount=exit_amount,
            withdrawal_address=exited_address,
            is_exit=False,
        ),
    ]

    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor=write_cursor, validators=[
            ValidatorDetails(
                validator_index=active_index,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c'),
            ), ValidatorDetails(
                validator_index=exited_index,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0x800041b1eff8af7a583caa402426ffe8e5da001615f5ce00ba30ea8e3e627491e0aa7f8c0417071d5c1c7eb908962d8e'),
            ), ValidatorDetails(
                validator_index=slashed_index,
                validator_type=ValidatorType.DISTRIBUTING,
                public_key=Eth2PubKey('0xb02c42a2cda10f06441597ba87e87a47c187cd70e2b415bef8dc890669efe223f551a2c91c3d63a5779857d3073bf288'),
            ),
        ])

        dbevents.add_history_events(write_cursor, history=withdrawal_events)

    eth2.detect_exited_validators()
    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EthWithdrawalFilterQuery.make(),
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
        database: 'DBHandler',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that if an address has no withdrawals we correctly handle it"""
    with database.user_write() as write_cursor:
        # Add a validator associated with the address so that withdrawals get queried.
        DBEth2(database).add_or_update_validators(write_cursor, [
            ValidatorDetails(validator_index=1, public_key=Eth2PubKey('0xfoo1'), withdrawal_address=ethereum_accounts[0], validator_type=ValidatorType.DISTRIBUTING),  # noqa: E501
        ])

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
        assert cursor.execute('SELECT name FROM key_value_cache').fetchone()[0] == 'ethwithdrawalsts_0xc37b40ABdB939635068d3c5f13E7faF686F03B65'  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2024-02-07 10:00:00 GMT')
def test_beacon_node_rpc_queries(eth2: 'Eth2'):
    # Test setting rpc endpoint both with/without trailing slash. Also unsetting
    eth2.beacon_inquirer.set_rpc_endpoint('http://42.42.42.42:6969')  # without trailing slash
    assert eth2.beacon_inquirer.node is not None
    eth2.beacon_inquirer.set_rpc_endpoint('')  # unset beacon rpc endpoint
    assert eth2.beacon_inquirer.node is None
    eth2.beacon_inquirer.set_rpc_endpoint('http://42.42.42.42:6969/')  # type: ignore  # with trailing slash -- not sure why it says this is unreachable
    assert eth2.beacon_inquirer.node is not None

    # now let's test balances
    indices = list(range(1074000, 1074100))
    validators = [Eth2PubKey('0xa2f870e998e823e5c53527407dd4d17ca80de5416fc756154cd68862a0a8ada2910e4b2bf2c7a5152bd20e5e06900b7e')] + indices  # noqa: E501

    with patch.object(eth2.beacon_inquirer.beaconchain, '_query', wraps=eth2.beacon_inquirer.beaconchain._query) as beaconchain_query:  # noqa: E501
        balances = eth2.beacon_inquirer.get_balances(indices_or_pubkeys=validators, has_premium=True)  # noqa: E501
        assert beaconchain_query.call_count == 0, 'beaconcha.in should not have been queried'
        assert len(balances) == len(validators)
        assert all(x.amount > 32 for x in balances.values())

        # now let's test validator data
        validator_data = eth2.beacon_inquirer.get_validator_data(validators)
        assert len(validator_data) == len(validators)
        for entry in validator_data:
            if entry.public_key == validators[0]:
                assert entry.validator_index == 1086866
            else:
                assert entry.validator_index in indices

        assert beaconchain_query.call_count == 0, 'beaconcha.in should not have been queried'


@pytest.mark.freeze_time('2024-02-07 10:00:00 GMT')
@pytest.mark.parametrize('network_mocking', [False])
def test_details_with_beacon_node(eth2: 'Eth2'):
    """Check that when we have a beacon node setup the function
    get_validator_data processes the validator details and queries
    access the correct keys.
    """
    with patch(  # create the beacon node attribute
        'rotkehlchen.chain.ethereum.modules.eth2.beacon.BeaconNode.query',
        new=lambda *args, **kwargs: {'version': 1},
    ):
        eth2.beacon_inquirer.set_rpc_endpoint('http://42.42.42.42:6969/')

    assert eth2.beacon_inquirer is not None

    mocked_node_response = [{
        'balance': '32011774971',
        'index': '197823',
        'status': 'active_ongoing',
        'validator': {
            'activation_eligibility_epoch': '0',
            'activation_epoch': '0',
            'effective_balance': '32000000000',
            'exit_epoch': '18446744073709551615',
            'pubkey': '800003d8af8aa481646da46d0d00ed2659a5bb303e0d88edf468abc1259a1f23ccf12eaeaa3f80511cfeaf256904a72a',  # noqa: E501
            'slashed': False,
            'withdrawable_epoch': '9223372036854775806',  # modified to be just before BEACONCHAIN_MAX_EPOCH  # noqa: E501
            'withdrawal_credentials': '0x01000000000000000000000015f4b914a0ccd14333d850ff311d6dafbfbaa32b',  # noqa: E501
        },
    }]
    beaconchain_validator_data = [{'activationeligibilityepoch': 51362, 'activationepoch': 51967, 'balance': 0, 'effectivebalance': 0, 'exitepoch': 248121, 'lastattestationslot': 7939840, 'name': '', 'pubkey': '0x800003d8af8aa481646da46d0d00ed2659a5bb303e0d88edf468abc1259a1f23ccf12eaeaa3f80511cfeaf256904a72a', 'slashed': False, 'status': 'exited', 'validatorindex': 197823, 'withdrawableepoch': 248377, 'withdrawalcredentials': '0x010000000000000000000000e839a3e9efb32c6a56ab7128e51056585275506c', 'total_withdrawals': 35525369118}]  # noqa: E501

    with (
        patch.object(
            eth2.beacon_inquirer.node,
            'query_chunked',
            new=lambda *args, **kwargs: mocked_node_response,
        ),
        patch.object(
            eth2.beacon_inquirer.beaconchain,
            'get_validator_data',
            wraps=lambda *args, **kwargs: beaconchain_validator_data,
        ) as patched_beaconchain,
    ):
        details = eth2.beacon_inquirer.get_validator_data(indices_or_pubkeys=[1])
        assert patched_beaconchain.call_count == 1
        assert details[0].exited_timestamp == epoch_to_timestamp(248121)


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('network_mocking', [False])
@pytest.mark.freeze_time('2025-02-04 08:55:00 GMT')
@pytest.mark.parametrize('ethereum_accounts', [['0x6b3A8798E5Fb9fC5603F3aB5eA2e8136694e55d0']])
def test_block_with_mev_and_block_reward_and_multiple_mev_txs(
        eth2: 'Eth2',
        database,
        ethereum_inquirer,
        ethereum_accounts,
):
    """Test that proposing validators that get both the block fee recipient and a mev reward on top
    are properly seen in rotki. Also that when MEV reward
    is sent in multiple transactions they are all marked as such and moved into the block event.
    """
    dbevents = DBHistoryEvents(database)
    dbeth2 = DBEth2(database)
    vindex = 191912
    with database.user_write() as write_cursor:
        dbeth2.add_or_update_validators(write_cursor, [
            ValidatorDetails(
                validator_index=vindex,
                public_key=Eth2PubKey('0xa5a07d88d03f4763b7341cb10c547e128b5a924d4c0b7b1d9ce8294d22584ad97c3092be9c68caad172b058d461a1c6b'),
                ownership_proportion=ONE,
                validator_type=ValidatorType.DISTRIBUTING,
            ),
        ])

    tx_hashes_and_amounts = [
        (deserialize_evm_tx_hash('0xcb7ebe40e13e7b9fa7eff0c03e727618b2d68a00b7d9e23599ac1cbb20f36864'), '0.000108734081255623'),  # noqa: E501
        (deserialize_evm_tx_hash('0x02be96ca70adc0f0c826cf2c3466681c53bbf68270fd5b6647a962e0e9bfe41a'), '0.000112625190291071'),  # noqa: E501
        (deserialize_evm_tx_hash('0x2327159d6b747407352de9860f86b0bfa8266f9dc7dc967ba05dc015e51d6bc1'), '0.000177763139489933'),  # noqa: E501
    ]
    for tx_hash, _ in tx_hashes_and_amounts:
        get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    eth2.beacon_inquirer.beaconchain.get_and_store_produced_blocks([vindex])
    eth2.combine_block_with_tx_events()
    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                from_ts=Timestamp(1738537200),  # 03/02/2025
                to_ts=Timestamp(1738655703),  # 04/02/2025 08:55 UTC
            ),
            group_by_event_ids=False,
        )

    timestamp, user_address, mevbot_address, block_number = TimestampMS(1738655099000), ethereum_accounts[0], string_to_evm_address('0xA69babEF1cA67A37Ffaf7a485DfFF3382056e78C'), 21771728  # noqa: E501
    expected_events: list[HistoryBaseEntry] = [EthBlockEvent(
        identifier=4,
        validator_index=vindex,
        timestamp=timestamp,
        amount=FVal('0.013925706716354256'),
        fee_recipient=user_address,
        fee_recipient_tracked=True,
        block_number=block_number,
        is_mev_reward=False,
    ), EthBlockEvent(
        identifier=5,
        validator_index=vindex,
        timestamp=timestamp,
        amount=FVal('0.022204362489834771'),
        fee_recipient=user_address,
        fee_recipient_tracked=True,
        block_number=block_number,
        is_mev_reward=True,
    )]
    expected_events += [EvmEvent(
        identifier=1 + counter,
        event_identifier=f'BP1_{block_number}',
        tx_hash=tx_hash,
        sequence_index=2 + counter,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.MEV_REWARD,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=user_address,
        address=mevbot_address,
        notes=f'Receive {amount} ETH from {mevbot_address} as mev reward for block {block_number} in {tx_hash.hex()}',  # noqa: E501
        extra_data={'validator_index': vindex},
    ) for counter, (tx_hash, amount) in enumerate(tx_hashes_and_amounts)]
    assert events == expected_events
