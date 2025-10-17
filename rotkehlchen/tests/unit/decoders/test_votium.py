import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.votium.constants import CPT_VOTIUM, VOTIUM_CONTRACTS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_GNO
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x362C51b56D3c8f79aecf367ff301d1aFd42EDCEA']])
def test_votium_claim_1(ethereum_inquirer, ethereum_accounts):
    """Test for votium contract 1 (MultiMerkleStash)"""
    tx_hash = deserialize_evm_tx_hash('0x75b81b2edd454a7b564cc55a6b676e2441e155401bde99a38d867028081d2c30')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, amount = TimestampMS(1646375440000), '0.005264399856069432', '12.369108326706528256'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=351,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken('eip155:1/erc20:0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0'),
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Receive {amount} FXS from votium bribe',
            counterparty=CPT_VOTIUM,
            address=VOTIUM_CONTRACTS[0],
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x96CC80292fa3A7045611EB84aE09DF8bd15936d2']])
def test_votium_claim_2(ethereum_inquirer, ethereum_accounts):
    """Test for votium contract 2 (veCRV Merkle Stash)"""
    tx_hash = deserialize_evm_tx_hash('0x27b48aa8f0f02e8e35f182925e2efb2a299a1410641d96de4de98666d28b36c7')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, amount = TimestampMS(1678972523000), '0.001771703400663612', '0.130390330817010288'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=167,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_GNO,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Receive {amount} GNO from votium bribe',
            counterparty=CPT_VOTIUM,
            address=VOTIUM_CONTRACTS[1],
        )]
    assert events == expected_events
