import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.modules.octant.constants import CPT_OCTANT, OCTANT_DEPOSITS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH, A_GLM
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_lock_glm(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x29944efad254413b5eccdd5f13f14642ab830dbf51d5f2cfc59cf4957f33671a')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1697572739000)
    gas_str = '0.000721453620442015'
    approval_str = '199999000'
    amount_str = '1000'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=347,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GLM,
            balance=Balance(amount=FVal(approval_str)),
            location_label=user_address,
            notes=f'Set GLM spending approval of {user_address} by {OCTANT_DEPOSITS} to {approval_str}',  # noqa: E501
            address=OCTANT_DEPOSITS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=348,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GLM,
            balance=Balance(amount=FVal(amount_str)),
            location_label=user_address,
            notes=f'Lock {amount_str} GLM in Octant',
            counterparty=CPT_OCTANT,
            address=OCTANT_DEPOSITS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa8258ED271BB9be9d7E16c5818E45eF6F2577d92']])
def test_unlock_glm(database, ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x6705075bef0c3d9167c95a4a6c4911d6cc4055365e12fc445acd1039b157b1ab')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hex,
    )
    timestamp = TimestampMS(1697527487000)
    gas_str = '0.000482531053547631'
    amount_str = '500'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_str)),
            location_label=user_address,
            notes=f'Burned {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=180,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GLM,
            balance=Balance(amount=FVal(amount_str)),
            location_label=user_address,
            notes=f'Unlock {amount_str} GLM from Octant',
            counterparty=CPT_OCTANT,
            address=OCTANT_DEPOSITS,
        ),
    ]
    assert events == expected_events
