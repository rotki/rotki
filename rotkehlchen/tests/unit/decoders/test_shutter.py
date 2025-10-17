import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.shutter.constants import (
    CPT_SHUTTER,
    SHUTTER_AIDROP_CONTRACT,
)
from rotkehlchen.constants.assets import A_ETH, A_SHU
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xCc60Eb2f64E7AD9b6924939B7985970D29A0108c']])
def test_airdrop_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3f20929de51baefdc688997a05bde1e32120cb7d4e0fda5da3963b1a620d0a8b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1706703155000)
    gas_amount_str, claimed_amount = '0.006946508605618104', '1086.95652173913'
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
            sequence_index=132,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_SHU,
            amount=FVal(claimed_amount),
            location_label=ethereum_accounts[0],
            notes=f'Claim {claimed_amount} SHU from shutter airdrop into the vesting contract: 0x22714964e6b9F17798A9e1AD3f2BAb87279876FC',  # noqa: E501
            counterparty=CPT_SHUTTER,
            address=SHUTTER_AIDROP_CONTRACT,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'shutter'},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x36bE40f9bd613dFf47294E7e10D4cae072E06A2D']])
def test_shu_delegation(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x46a476b09c85d2278f1ac889e943d7f47d029d0985719cc2a73d589a73cb2473')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1705596215000)
    gas_amount_str = '0.00549203889835413'
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
            sequence_index=479,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_SHU,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Change SHU Delegate for 0x561075538e7B20613Aa0C3fAa8459ac293011584 from {ethereum_accounts[0]} to 0x9Cc9C7F874eD77df06dCd41D95a2C858cd2a2506',  # noqa: E501
            counterparty=CPT_SHUTTER,
        ),
    ]
    assert events == expected_events
