import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.fluence.constants import (
    CPT_FLUENCE,
    DEV_REWARD_DISTRIBUTOR,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_airdrop_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc04e88de26d3466e64a243c15db181342152d0b771b0e8e224920ea9b28fe7e0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1712868707000)
    gas_amount_str, claimed_amount = '0.00203104493516988', '5000'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=196,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x6081d7F04a8c31e929f25152d4ad37c83638C62b'),
            amount=FVal(claimed_amount),
            location_label=ethereum_accounts[0],
            notes=f'Claim {claimed_amount} FLT-DROP from Fluence dev rewards',
            counterparty=CPT_FLUENCE,
            address=DEV_REWARD_DISTRIBUTOR,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_airdrop_swap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1db2028d68fbdc19e770307dd968c24c8fa4211b26eb512a938223f89d11450a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount_str, claimed_amount = TimestampMS(1718357447000), '0.00059501796565782', '5000'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=EvmToken('eip155:1/erc20:0x6081d7F04a8c31e929f25152d4ad37c83638C62b'),
            amount=FVal(claimed_amount),
            location_label=ethereum_accounts[0],
            notes=f'Burn {claimed_amount} FLT-DROP',
            counterparty=CPT_FLUENCE,
            address=DEV_REWARD_DISTRIBUTOR,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=EvmToken('eip155:1/erc20:0x236501327e701692a281934230AF0b6BE8Df3353'),
            amount=FVal(claimed_amount),
            location_label=ethereum_accounts[0],
            notes=f'Claim {claimed_amount} FLT by burning FLT-DROP',
            counterparty=CPT_FLUENCE,
            address=DEV_REWARD_DISTRIBUTOR,
        ),
    ]
    assert events == expected_events
