import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_HOP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_hop_l2_deposit(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee
    """
    tx_hash = deserialize_evm_tx_hash('0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1653219722000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001964214783875487')),
            location_label=ADDY,
            notes='Burned 0.001964214783875487 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.2')),
            location_label=ADDY,
            notes='Bridge 0.2 ETH to Optimism at the same address via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f'),
        )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_hop_optimism_eth_receive(database, optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0x8394c39e1f030a04aa8359f0322257632282a7dfa419b3c9ffc8ab61205a815d
    """
    tx_hash = deserialize_evm_tx_hash('0x8394c39e1f030a04aa8359f0322257632282a7dfa419b3c9ffc8ab61205a815d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1653220466000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.200077923923235647')),
            location_label=ADDY,
            notes='Bridge 0.200077923923235647 ETH via hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
            extra_data={'sent_amount': '0.2'},
        )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('optimism_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_hop_optimism_eth_receive_no_event(database, optimism_inquirer, optimism_accounts):
    """Data taken from
    https://optimistic.etherscan.io/tx/0x3e18e3a0220857ecce91ad79065f10a663128926854b6087161fd0364c7f76f5

    Test that HOP bridge events that have no TRANSFER_FROM_L1_COMPLETED event are decoded.
    """
    tx_hash = deserialize_evm_tx_hash('0x3e18e3a0220857ecce91ad79065f10a663128926854b6087161fd0364c7f76f5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    user_address = optimism_accounts[0]
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1666977475000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.03958480553397407')),
            location_label=user_address,
            notes='Bridge 0.03958480553397407 ETH via hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        )]
    assert events == expected_events
