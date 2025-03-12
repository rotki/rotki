from typing import Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.rainbow.constants import (
    CPT_RAINBOW_SWAPS,
    RAINBOW_ROUTER_CONTRACT,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

A_AIT: Final = Asset('eip155:1/erc20:0x89d584A1EDB3A70B3B07963F9A3eA5399E38b136')
A_BUOY: Final = Asset('eip155:1/erc20:0x289Ff00235D2b98b0145ff5D4435d3e92f9540a6')
A_AXGT: Final = Asset('eip155:1/erc20:0xDd66781D0E9a08D4FBb5eC7BAc80B691BE27F21D')
A_ZIG: Final = Asset('eip155:1/erc20:0xb2617246d0c6c0087f18703d576831899ca94f01')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xfe25d6300D33e19E15AeeFEFD0Aafb319Dd61ae1']])
def test_rainbow_swap_eth_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xcd6afacf1efce38186b6cf9164792c4034d33d3f071c5e28c0b79ce5ab0223a9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    swap_amount, received_amount, gas_fees, fee_amount, timestamp, user_address = '0.2', '28827.267041421686554081', '0.000114360530468618', '0.00199745', TimestampMS(1741808351000), ethereum_accounts[0]  # noqa: E501
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
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AIT,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} AIT as the result of a swap in Rainbow',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH a Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]

    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0a471798F7f609A0B7fAC97051E57Be1c434FdeF']])
def test_rainbow_swap_token_to_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd34d7393151a3c0f2d23d0df4d8f0b4a000be7613277e831ef0860191e68f855')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    swap_amount, received_amount, gas_fees, fee_amount, timestamp, user_address = '1010.887928111872496631', '0.089068967427375408', '0.000147805218572058', '0.00089852786738257', TimestampMS(1741892171000), ethereum_accounts[0]  # noqa: E501
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
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BUOY,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} BOOE in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH a Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]

    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB80177697e160eFC91d4B1ec295ABE6Ce0c0Fe1f']])
def test_rainbow_swap_token_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4f85ee11bbc401240755b083106e0811e6b60ef7972063a51596934cbb6ed43f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_fees, swap_amount, received_amount, approve_amount, fee_amount, timestamp, user_address = '0.000364910690805408', '77911.038010822816755701', '45110.517197738477939043', '115792089237316195423570985008687907853269984665640563961546.545997090312884234', '662.243823091993942423', TimestampMS(1741889531000), ethereum_accounts[0]  # noqa: E501
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
        sequence_index=281,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ZIG,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set ZIG spending approval of {user_address} by {RAINBOW_ROUTER_CONTRACT} to {approve_amount}',  # noqa: E501
        address=RAINBOW_ROUTER_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=282,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ZIG,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ZIG in Rainbow',
        address=RAINBOW_ROUTER_CONTRACT,
        counterparty=CPT_RAINBOW_SWAPS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=283,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AXGT,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} AXGT as the result of a swap in Rainbow',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=284,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ZIG,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} ZIG a Rainbow fee',
        counterparty=CPT_RAINBOW_SWAPS,
        address=RAINBOW_ROUTER_CONTRACT,
    )]

    assert expected_events == events
