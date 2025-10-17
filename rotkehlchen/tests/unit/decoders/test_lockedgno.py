import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.lockedgno.constants import (
    CPT_LOCKEDGNO,
    LOCKED_GNO_ADDRESS,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_GNO
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xfcA5BDce638Fb8b80438bdb41F5CedcAA8893bc7']])
def test_lock_gno(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe74bd8d81a057942d734d16303d74b9ae01dcd5659488f7955c36d6be5b107fe')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1643833498000)
    amount_str = '5.207408513473562376'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.009134740180642554'),
            location_label=user_address,
            notes='Burn 0.009134740180642554 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=365,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_GNO,
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Deposit {amount_str} GNO to the locking contract',
            counterparty=CPT_LOCKEDGNO,
            address=LOCKED_GNO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=366,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x4f8AD938eBA0CD19155a835f617317a6E788c868'),
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Receive {amount_str} locked GNO from the locking contract',
            counterparty=CPT_LOCKEDGNO,
            address=LOCKED_GNO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc62b361FdC14210dA59b9F5c3Ba7FAa7d61893a4']])
def test_unlock_gno(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x60b03b2bf3861c68a508f54a233d9ed742ddcd57899e730c57cc10f2939b0df0')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1682246147000)
    amount_str = '7.232204655685847974'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003240606189784113'),
            location_label=user_address,
            notes='Burn 0.003240606189784113 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=115,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_GNO,
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Receive {amount_str} GNO back from the locking contract',
            counterparty=CPT_LOCKEDGNO,
            address=LOCKED_GNO_ADDRESS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=116,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0x4f8AD938eBA0CD19155a835f617317a6E788c868'),
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Return {amount_str} locked GNO to the locking contract',
            counterparty=CPT_LOCKEDGNO,
            address=LOCKED_GNO_ADDRESS,
        ),
    ]
    assert events == expected_events
