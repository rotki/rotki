import pytest

from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.arbitrum_one.modules.airdrops.decoder import ARBITRUM_ONE_AIRDROP
from rotkehlchen.chain.arbitrum_one.modules.arbitrum_governor.constants import GOVERNOR_ADDRESSES
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ARB, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0c5b7A89b3689d86Ed473caE4E7CB00381949861']])
def test_arbitrum_airdrop_claim(arbitrum_one_inquirer, arbitrum_one_accounts):
    """Data taken from
    https://arbiscan.io/tx/0xa230fc4d5e61db1d9be044215b00cb6ad1775b413a240ea23a98117153f6264e
    """
    tx_hash = deserialize_evm_tx_hash('0xa230fc4d5e61db1d9be044215b00cb6ad1775b413a240ea23a98117153f6264e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user_address = TimestampMS(1689935876000), arbitrum_one_accounts[0]
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000032717'),
            location_label=user_address,
            notes='Burn 0.000032717 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_ARB,
            amount=FVal('625'),
            location_label=user_address,
            notes='Claimed 625 ARB from arbitrum airdrop',
            counterparty=CPT_ARBITRUM_ONE,
            address=ARBITRUM_ONE_AIRDROP,
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_vote_cast(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x10b9c5adb845151365bf6977d76b728fad60b64372ce0bde6ae52602b01c282b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user_address = TimestampMS(1707677598000), arbitrum_one_accounts[0]
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0000821946'),
            location_label=user_address,
            notes='Burn 0.0000821946 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Vote FOR arbitrum_one governance proposal https://www.tally.xyz/gov/arbitrum/proposal/28300903567340237987946172947371304329455149918972967618773111648600015289785',
            counterparty=CPT_ARBITRUM_ONE,
            address=GOVERNOR_ADDRESSES[0],
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_vote_cast_2(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf58c9b1ee6643d6af1fd3b5edbfb311bd86eb3417da561fd1650f12be775d71a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas = TimestampMS(1713188011000), '0.00000252921'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=arbitrum_one_accounts[0],
            notes='Vote FOR arbitrum_one governance proposal https://www.tally.xyz/gov/arbitrum/proposal/42524710257895482033293584464762477376427316183960646909542733545381165923770',
            tx_hash=tx_hash,
            counterparty=CPT_ARBITRUM_ONE,
            address=GOVERNOR_ADDRESSES[3],
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_vote_cast_treasury(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8f5eed6ec89eeccbdfa141b91129118a8294d35a1b44f9e7d570945d17f42765')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas = TimestampMS(1717152106000), '0.00000270109'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=arbitrum_one_accounts[0],
            notes="Vote AGAINST arbitrum_one governance proposal https://www.tally.xyz/gov/arbitrum/proposal/53472400873981607449547539050199074000442490831067826984987297151333310022877 with reasoning: IMO games or arbitrum is a path that is interesting but the amounts are big and I'm not sure how they adjust to the industry. This is giving a lot of money and might be the wrong path where games that no one enjoy get developed and then nothing happens after it. How the money will be spent is described but I believe the amounts are more than what is needed for such a program",  # noqa: E501
            tx_hash=tx_hash,
            counterparty=CPT_ARBITRUM_ONE,
            address=GOVERNOR_ADDRESSES[1],
        ),
    ]
    assert expected_events == events
