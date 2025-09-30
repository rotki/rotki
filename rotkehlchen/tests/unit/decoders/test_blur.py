from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.blur.constants import (
    BLUR_IDENTIFIER,
    BLUR_STAKING_CONTRACT,
    CPT_BLUR,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_blur_claim_and_stake(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list[ChecksumEvmAddress]):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x09b9d311c62dadc69a06f39daa5206760f38ef48d9e8473f27a9cf2d599133c9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, stake_amount, gas_fees = TimestampMS(1702156943000), '6350.3577325406', '0.005302886935404245'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=82,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=Asset(BLUR_IDENTIFIER),
            amount=FVal(stake_amount),
            location_label=ethereum_accounts[0],
            notes=f'Claim {stake_amount} BLUR from Blur airdrop',
            counterparty=CPT_BLUR,
            address=string_to_evm_address('0xeC2432a227440139DDF1044c3feA7Ae03203933E'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=83,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(BLUR_IDENTIFIER),
            amount=FVal(stake_amount),
            location_label=ethereum_accounts[0],
            notes=f'Stake {stake_amount} BLUR',
            counterparty=CPT_BLUR,
            product=EvmProduct.STAKING,
            address=BLUR_STAKING_CONTRACT,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x76107ad6A0c2AefDC5c19ee047add3D72aFb4984']])
def test_blur_stake(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list[ChecksumEvmAddress]):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xdae4c4cc02aea1a4063295aabf75c7fd30618a4fb364209270d215d2d33b7221')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, stake_amount, gas_fees = TimestampMS(1715478947000), '903.93', '0.000533750631510369'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=154,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset(BLUR_IDENTIFIER),
            amount=FVal(stake_amount),
            location_label=ethereum_accounts[0],
            notes=f'Stake {stake_amount} BLUR',
            counterparty=CPT_BLUR,
            address=BLUR_STAKING_CONTRACT,
            product=EvmProduct.STAKING,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC60dC16A1bBaEb6dB99912aE8AD2359565BC5423']])
def test_blur_unstake(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts: list[ChecksumEvmAddress]):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x494259cae7bf1d68c185f5d35ad5991e28a20089b44f30453da6967dd5a5270a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, unstake_amount, gas_fees = TimestampMS(1716377543000), '2333.05', '0.000802495016237112'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fees} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=242,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset(BLUR_IDENTIFIER),
            amount=FVal(unstake_amount),
            location_label=ethereum_accounts[0],
            notes=f'Unstake {unstake_amount} BLUR',
            tx_hash=tx_hash,
            address=BLUR_STAKING_CONTRACT,
            counterparty=CPT_BLUR,
        ),
    ]
    assert expected_events == events
