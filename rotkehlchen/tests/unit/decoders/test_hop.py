import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_HOP
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr
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
    expected_events = [
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1653219722000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.001964214783875487')),
            location_label=ADDY,
            notes='Burned 0.001964214783875487 ETH for gas',
            counterparty=CPT_GAS,
        ), HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=1,
            timestamp=1653219722000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.2')),
            location_label=ADDY,
            notes='Bridge 0.2 ETH to Optimism at the same address via Hop protocol',
            counterparty=CPT_HOP,
        )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
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
        HistoryBaseEntry(
            event_identifier=tx_hash,
            sequence_index=0,
            timestamp=1653220466000,
            location=Location.BLOCKCHAIN,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.200077923923235647')),
            location_label=ADDY,
            notes='Bridge 0.200077923923235647 ETH via hop protocol',
            counterparty=CPT_HOP,
            extra_data={'sent_amount': '0.2'},
        )]
    assert expected_events == events
