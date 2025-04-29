import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.juicebox.constants import CPT_JUICEBOX, TERMINAL_3_1_2
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_donation(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xf7873b900aa9bb0453b70bc57c7eef54af37346c58edfd4768eb74567279e06e',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1706095919000)
    donated_amount, gas_fees = '2', '0.00306450894012447'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        amount=FVal(donated_amount),
        location_label=user_address,
        notes=f'Donate {donated_amount} ETH at Juicebox to project Defend Roman Storm with memo: "Opensource is not a crime. Privacy is normal. Thank you for fighting for us and good luck.\nhttps://jbm.infura-ipfs.io/ipfs/QmT9hZuHJjGidc8nrdZYskwRbr2hai9rwVodjCuvUNTvKL https://jbm.infura-ipfs.io/ipfs/QmXWAeCpUdLYrzYbpxWq4Ajnhf5trssicHPwGRkPWY5Fx9"',  # noqa: E501
        address=TERMINAL_3_1_2,
        counterparty=CPT_JUICEBOX,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=278,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:1/erc721:0x723932B58a7c6AEf036d1Fe17654E845d0f0fae5/4000000011'),
        amount=ONE,
        location_label=user_address,
        notes='Receive an NFT for donating via Juicebox',
        counterparty=CPT_JUICEBOX,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=280,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset('eip155:1/erc721:0x723932B58a7c6AEf036d1Fe17654E845d0f0fae5/3000000016'),
        amount=ONE,
        location_label=user_address,
        notes='Receive an NFT for donating via Juicebox',
        counterparty=CPT_JUICEBOX,
        address=ZERO_ADDRESS,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x15b850a67A6ceDd218e368f1Cab11403f45a42f4']])
def test_fund_raising(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xd4b8b0857d4cce83f0ce7310a0ed1a8f6360bae331bb4e8bd9217b1370b05bee',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1706711399000)
    paid_amount, gas_fees = '0.4', '0.003792515741532086'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal(paid_amount),
        location_label=user_address,
        notes=f'Pay {paid_amount} ETH at Juicebox to project octra community raise',
        address=TERMINAL_3_1_2,
        counterparty=CPT_JUICEBOX,
    )]
    assert expected_events == events
