
import pytest

from rotkehlchen.chain.ethereum.modules.makerdao.constants import MKR_ADDRESS
from rotkehlchen.chain.ethereum.modules.sky.constants import (
    CPT_SKY,
    DAI_TO_USDS_CONTRACT,
    SKY_ASSET,
    SUSDS_ASSET,
    SUSDS_CONTRACT,
    USDS_ASSET,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_MKR
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfb10EFE8d84E73061ABDfa5F87f26aFC1f0a98f5']])
def test_migrate_dai(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xda915701a7634628d8301d44a4e122599f05a1281286ab416f5101c79a24e408')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726732211000)
    gas_amount, migrated_amount = '0.001933756075256005', '10086.448037727051859359'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=115,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_DAI,
        amount=FVal(migrated_amount),
        location_label=ethereum_accounts[0],
        notes=f'Migrate {migrated_amount} DAI to USDS',
        counterparty=CPT_SKY,
        address=DAI_TO_USDS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=120,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=USDS_ASSET,
        amount=FVal(migrated_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {migrated_amount} USDS from DAI->USDS migration',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xaE6396d2fB733e124f9b1C3BF922cF17fE1CC75A']])
def test_redeem_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2e5bac2cb234a4388d45754656bad35cc03c7dde7745de10b5b605ff28187d52')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726736615000)
    gas_amount, returned_amount, withdrawn_amount = '0.002553705360907168', '76400.28490997120343213', '76424.11'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=SUSDS_ASSET,
        amount=FVal(returned_amount),
        location_label=ethereum_accounts[0],
        notes=f'Return {returned_amount} sUSDS to sUSDS contract',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=USDS_ASSET,
        amount=FVal(withdrawn_amount),
        location_label=ethereum_accounts[0],
        notes=f'Withdraw {withdrawn_amount} USDS from sUSDS contract',
        counterparty=CPT_SKY,
        address=SUSDS_CONTRACT,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2618d8078253b4765fd4ea56b3840c212830E9a3']])
def test_deposit_susds(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe9ca86a0ce9c0226d65203805b77d13697ad5e579989505562638095dc45cac4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726754135000)
    gas_amount, deposited_amount, withdrawn_amount = '0.003750084090503928', '5114.68', '5112.913299374006156278'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=309,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=USDS_ASSET,
        amount=FVal(deposited_amount),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {deposited_amount} USDS to sUSDS contract',
        counterparty=CPT_SKY,
        address=SUSDS_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=311,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=SUSDS_ASSET,
        amount=FVal(withdrawn_amount),
        location_label=ethereum_accounts[0],
        notes=f'Withdraw {withdrawn_amount} sUSDS from sUSDS contract',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4Bb80Ba800f39b9237ce6e05a338962885d5F474']])
def test_migrate_maker(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xbfa0b5489a1f4b28c416d0ef8cbcbbc9d7d4fea8c3f1d53830b2cd5f78252b79')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1726760855000)
    gas_amount, migrated_amount, received_amount = '0.00127609766341068', '0.75001216', '18000.29184'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_MKR,
        amount=FVal(migrated_amount),
        location_label=ethereum_accounts[0],
        notes=f'Migrate {migrated_amount} MKR to SKY',
        counterparty=CPT_SKY,
        address=MKR_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MIGRATE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=SKY_ASSET,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} SKY from MKR->SKY migration',
        counterparty=CPT_SKY,
        address=ZERO_ADDRESS,
    )]
    assert expected_events == events
