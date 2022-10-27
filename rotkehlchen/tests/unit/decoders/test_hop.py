import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.hop.constants import CPT_HOP
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])  # noqa: E501
def test_hop_l2_deposit(database, ethereum_manager, function_scope_messages_aggregator):
    """Data taken from
    https://etherscan.io/tx/0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee
    """
    # TODO: For faster tests hard-code the transaction and the logs here so no remote query needed
    tx_hash = deserialize_evm_tx_hash('0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        ethereum_manager=ethereum_manager,
        database=database,
        msg_aggregator=function_scope_messages_aggregator,
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
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.2')),
            location_label=ADDY,
            notes='Bridge 0.2 ETH to Optimism at the same address via Hop protocol',
            counterparty=CPT_HOP,
        )]
    assert expected_events == events
