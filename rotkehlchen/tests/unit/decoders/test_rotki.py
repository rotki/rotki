from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.rotki.constants import (
    CPT_ROTKI,
    ROTKI_SPONSORSHIP_CONTRACT_ADDRESS,
    ROTKI_SPONSORSHIP_TREASURY_ADDRESS,
)
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd161F7FA342DCefEafDEb0827B83a400F57ad0a4']])
def test_gold_sponsorship(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x8896c30e52bfc3a1044eca1cf126973845c46a3782e6d4f274590772b1213e55')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1756566359000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000243015590156846')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        address=None,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=262,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=(spend_amount := FVal('1200')),
        location_label=user_address,
        notes=f'Spend {spend_amount} USDC to purchase rotki Gold Sponsorship NFT',
        counterparty=CPT_ROTKI,
        address=ROTKI_SPONSORSHIP_TREASURY_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=263,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc721:0x3337286E850cf01B8A8B6094574f0dd6a2108B16/1'),
        amount=ONE,
        location_label=user_address,
        notes='Receive rotki Gold Sponsorship NFT',
        counterparty=CPT_ROTKI,
        address=ROTKI_SPONSORSHIP_TREASURY_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x23bc95F84BD43C1FCc2bc285fDa4Cb12f9AEE2df']])
def test_silver_sponsorship(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xeac2dce7712615c992b8bbfc85e6480be2d33cf7c184c5134d1369998cd94351')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1756562735000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000270510471626436')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        address=None,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=69,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x39b8B6385416f4cA36a20319F70D28621895279D'),
        amount=(spend_amount := FVal('600')),
        location_label=user_address,
        notes=f'Spend {spend_amount} EURe to purchase rotki Silver Sponsorship NFT',
        counterparty=CPT_ROTKI,
        address=ROTKI_SPONSORSHIP_TREASURY_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=70,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc721:0x3337286E850cf01B8A8B6094574f0dd6a2108B16/0'),
        amount=ONE,
        location_label=user_address,
        notes='Receive rotki Silver Sponsorship NFT',
        counterparty=CPT_ROTKI,
        address=ROTKI_SPONSORSHIP_TREASURY_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa7979BF6Ce644E4e36da2Ee65Db73c3f5A0dF895']])
def test_bronze_sponsorship(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe66898edb1bb96acfe83e9c2a6895c600b666641bacb2ef2060154f6e29cd112')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1758889799000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000220485364898432')),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        address=None,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=(spend_amount := FVal('0.05')),
        location_label=user_address,
        notes=f'Spend {spend_amount} ETH to purchase rotki Bronze Sponsorship NFT',
        counterparty=CPT_ROTKI,
        address=ROTKI_SPONSORSHIP_CONTRACT_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc721:0x3337286E850cf01B8A8B6094574f0dd6a2108B16/11'),
        amount=ONE,
        location_label=user_address,
        notes='Receive rotki Bronze Sponsorship NFT',
        counterparty=CPT_ROTKI,
        address=ROTKI_SPONSORSHIP_CONTRACT_ADDRESS,
    )]
