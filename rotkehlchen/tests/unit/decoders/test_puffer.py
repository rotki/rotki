import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import (
    EIGEN_TOKEN_ID,
)
from rotkehlchen.chain.ethereum.modules.puffer.constants import (
    CPT_PUFFER,
    HEDGEY_DELEGATEDCLAIMS_CAMPAIGN,
    PUFFER_TOKEN_ID,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6872a0E272f9De4a7FEF217f2fF9ac297fc72aeb']])
def test_pufferxeigen_s2_airdrop(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4e42f307effc0dc7fdfbf72d54a9a86b4b0d96cf1a14f1069717e2d637bf5561')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, claim_amount = TimestampMS(1726953011000), '0.001071196143585596', '9.61696139158485'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=407,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(EIGEN_TOKEN_ID),
        amount=FVal(claim_amount),
        location_label=ethereum_accounts[0],
        notes=f'Claim {claim_amount} EIGEN from PufferXEigen S2 airdrop',
        counterparty=CPT_PUFFER,
        address=HEDGEY_DELEGATEDCLAIMS_CAMPAIGN,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3D8a392BdF76Cf1bB17e9C118d7F390B6c409934']])
def test_puffer_s1_airdrop_2_campaigns(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5f5111b2ebdc3fa8f7bcf4659d898fafc00fc7df5e727f1edabf246ee89c68f9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, claim_amount1, claim_amount2 = TimestampMS(1728945107000), '0.002975374594297972', '70', '210'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=210,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(PUFFER_TOKEN_ID),
        amount=FVal(claim_amount1),
        location_label=ethereum_accounts[0],
        notes=f'Claim {claim_amount1} PUFFER from Puffer S1 airdrop',
        counterparty=CPT_PUFFER,
        address=HEDGEY_DELEGATEDCLAIMS_CAMPAIGN,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=212,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(PUFFER_TOKEN_ID),
        amount=FVal(claim_amount2),
        location_label=ethereum_accounts[0],
        notes=f'Claim {claim_amount2} PUFFER from Puffer S1 airdrop',
        counterparty=CPT_PUFFER,
        address=HEDGEY_DELEGATEDCLAIMS_CAMPAIGN,
    )]
    assert events == expected_events
