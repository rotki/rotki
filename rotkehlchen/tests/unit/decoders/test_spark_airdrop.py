from typing import Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

A_SPK: Final = Asset('eip155:1/erc20:0xc20059e0317DE91738d13af027DfC4a50781b066')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD4fb8777b51fcF2aB468619E97b27FD49E672fC0']])
def test_spark_airdrop_claim(ethereum_inquirer, ethereum_accounts):
    """Test decoding of Spark airdrop claim transaction"""
    tx_hash = deserialize_evm_tx_hash(
        '0xe0ce13ffe3e9fe43fd7a80eb04604e857d388167cd30aa86f581369377a47131',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, claimed_amount = ethereum_accounts[0], TimestampMS(1750283303000), '0.000095432422616478', '5400'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=398,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_SPK,
            amount=FVal(claimed_amount),
            location_label=user_address,
            notes=f'Claim {claimed_amount} SPK from Spark airdrop',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0xCBA0C0a2a0B6Bb11233ec4EA85C5bFfea33e724d'),
            extra_data={'airdrop_identifier': 'spark'},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1e5f2AdD8B9a96652838A0A8291E94DEE408eB6d']])
def test_spark_staking(ethereum_inquirer, ethereum_accounts):
    """Test decoding of Spark token staking transaction"""
    tx_hash = deserialize_evm_tx_hash(
        '0xdd39f4868976c5df5705c83bb0af1a55094d759c5ee9a6513f21e6494517f0d5',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    user_address, timestamp, gas_amount, staked_amount = ethereum_accounts[0], TimestampMS(1750212503000), '0.000263240428824864', '2169.948625059716493489'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=255,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_SPK,
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Deposit {staked_amount} SPK for staking',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0xc6132FAF04627c8d05d6E759FAbB331Ef2D8F8fD'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=257,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xc6132FAF04627c8d05d6E759FAbB331Ef2D8F8fD'),
            amount=FVal(staked_amount),
            location_label=user_address,
            notes=f'Receive {staked_amount} stSPK for deposited SPK',
            counterparty=CPT_SPARK,
            address=string_to_evm_address('0x0000000000000000000000000000000000000000'),
        ),
    ]
    assert events == expected_events
