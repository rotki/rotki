import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.constants import CPT_GITCOIN
from rotkehlchen.chain.evm.decoding.eas.constants import CPT_EAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_attest_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf843f6d09e8dec2ee2d1b5fdeade9a9744857f598cf593b6c259166c32dfd05a')  # noqa: E501
    user_address = optimism_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1700569289000)
    gas_amount_str = '0.000136427902240075'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount_str),
            location_label=user_address,
            notes=f'Burn {gas_amount_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.ATTEST,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Attest to https://optimism.easscan.org/attestation/view/0x3045bf8797f8e528219d48b23d28b661be5be17d13c28f61f4f6cced1b349c65',
            counterparty=CPT_EAS,
            address=string_to_evm_address('0x4200000000000000000000000000000000000021'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_attest_gitcoin_mint(arbitrum_one_inquirer, arbitrum_one_accounts):
    """A test for minting gitcoin impact donation attestation"""
    tx_hash = deserialize_evm_tx_hash('0x5e93b5da1e2f22921f2ec0f7efc357f2ad4aafa70d387f87306c11b78f54b2c2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas, amount, uid = arbitrum_one_accounts[0], TimestampMS(1744315569000), '0.000010227716042', '0.0007722', '0x07afc8aecb89b381f08f87491901614b55059f2432c21e46681d9f5de2a13ced'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas),
        location_label=user_address,
        notes=f'Burn {gas} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.MINT,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(amount),
        location_label=user_address,
        notes=f'Mint donation impact attestation 0x07afc8aecb89b381f08f87491901614b55059f2432c21e46681d9f5de2a13ced for a fee of {amount} ETH',  # noqa: E501
        counterparty=CPT_GITCOIN,
        address=string_to_evm_address('0xeb2AddD987c2C4efF3237Ed6d829c214198c0189'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.ATTEST,
        asset=A_ETH,
        amount=ZERO,
        location_label=user_address,
        notes=f'Attest to https://arbitrum.easscan.org/attestation/view/{uid}',
        counterparty=CPT_EAS,
        address=string_to_evm_address('0xbD75f629A22Dc1ceD33dDA0b68c546A1c035c458'),
    )]
    assert events == expected_events
