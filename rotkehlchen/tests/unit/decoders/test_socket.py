import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import CPT_SOCKET, GATEWAY_ADDRESS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_optimism_to_arb_bridge(optimism_inquirer, optimism_accounts):
    evmhash = deserialize_evm_tx_hash('0xe8c9cffe2a2bbccf81cf8dd34f9b89c01b00ae3f0ff74eab089de96f4624165c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=evmhash)
    user_address = optimism_accounts[0]
    bridged_amount, gas_amount = '360.791433', '0.000035854553456552'
    timestamp = TimestampMS(1705844449000)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
            amount=FVal(bridged_amount),
            location_label=user_address,
            notes=f'Bridge {bridged_amount} USDC to {user_address} at Arbitrum One using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_bridge_eth(arbitrum_one_inquirer, arbitrum_one_accounts):
    evmhash = deserialize_evm_tx_hash('0xb1e29bebca0300ff02ee478dfa6c0c2197169761e1c0dcc87418c53a6530d3a5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=evmhash,
    )
    user_address = arbitrum_one_accounts[0]
    bridged_amount, gas_amount = '0.01', '0.0000464928'
    timestamp = TimestampMS(1696328657000)
    assert events == [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridged_amount),
            location_label=user_address,
            notes=f'Bridge {bridged_amount} ETH to {user_address} at Base using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
        ),
    ]
