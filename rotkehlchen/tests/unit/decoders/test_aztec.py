from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.aztec.constants import (
    A_AZTEC,
    AZTEC_STAKING_DATA,
    CPT_AZTEC,
    GSE,
    STAKING_REGISTRY,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x16425074e97d06392D602f1c2eB5ef9178cf97c9']])
def test_stake_with_provider(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x761a58d876bbe82646bc08e9981e745d286e3ad84d35669530a7b64f3c5fb00a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1777475507000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000706664379141137'),
            location_label=ethereum_accounts[0],
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=681,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_AZTEC,
            amount=FVal(stake_amount := '200000'),
            location_label=ethereum_accounts[0],
            notes=f'Stake {stake_amount} AZTEC with Aztec provider 57',
            counterparty=CPT_AZTEC,
            address=STAKING_REGISTRY,
            extra_data={AZTEC_STAKING_DATA: {
                'allocation': 9500,
                'attester': '0xeefBEC48D3750d3D523faeF283dCf50765dd4F6D',
                'rollup': '0xAe2001f7e21d5EcABf6234E9FDd1E76F50F74962',
                'split': '0xB1CD3a55f266DD76cB5c78aFa63c2E50A908C1F9',
                'total_allocation': 10000,
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x614387Bec1a22d428A496782C54d2FC51fc4711C']])
def test_stake_via_provider_helper(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xf6756aa15fbe3a517f7b297cd976335709f354188153658ff0fb7cf8c893f67e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1776684707000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00213653164390208'),
            location_label=ethereum_accounts[0],
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=384,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_AZTEC,
            amount=FVal(stake_amount := '200000'),
            location_label=ethereum_accounts[0],
            notes=f'Stake {stake_amount} AZTEC with Aztec provider 20',
            counterparty=CPT_AZTEC,
            address=STAKING_REGISTRY,
            extra_data={AZTEC_STAKING_DATA: {
                'allocation': 9700,
                'attester': '0x8A6dDe2562CD00c9F9D34587153B85D9533BB541',
                'rollup': '0xAe2001f7e21d5EcABf6234E9FDd1E76F50F74962',
                'split': '0xf639927b8F8c37ebD45d7fd492Cf6c9bFa00b850',
                'total_allocation': 10000,
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x16425074e97d06392D602f1c2eB5ef9178cf97c9']])
def test_governance_registration(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x761a58d876bbe82646bc08e9981e745d286e3ad84d35669530a7b64f3c5fb00a'),
    )
    tx_hash = deserialize_evm_tx_hash('0x8d5a2f9f22c46b3249365637db8c91e005c409c8ffffbe3adebfc0ea215d896b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=584,
        timestamp=TimestampMS(1777476623000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.GOVERNANCE,
        asset=A_AZTEC,
        amount=ZERO,
        location_label=ethereum_accounts[0],
        notes='Register 200000 AZTEC stake for Aztec governance with attester 0xeefBEC48D3750d3D523faeF283dCf50765dd4F6D',  # noqa: E501
        counterparty=CPT_AZTEC,
        address=GSE,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbB86cDfD0ac4593ebc012be31f8806d036B7703a']])
def test_governance_redelegation(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x336e4e6411fa90b6db6d9db143b7e161685fb0af40f7d1a1486fc942183f83c5'),
    )
    tx_hash = deserialize_evm_tx_hash('0x3fd7d3ad5262125ef3fb80292a01d933919f5ca11e6c87ccadf27016fee18591')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1786986959000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000245873731870389'),
            location_label=ethereum_accounts[0],
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=137,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_AZTEC,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Change Aztec governance delegate for attester '
                  '0x28b51b0443f43cCe8b3f9807e448dBCaeA056d90 from '
                  '0x9064Fb41156D300196d5Eb95E0B3c1f08eBc39a8 to '
                  '0xbB86cDfD0ac4593ebc012be31f8806d036B7703a',
            counterparty=CPT_AZTEC,
            address=GSE,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x16425074e97d06392D602f1c2eB5ef9178cf97c9']])
def test_staking_rewards(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x761a58d876bbe82646bc08e9981e745d286e3ad84d35669530a7b64f3c5fb00a'),
    )
    tx_hash = deserialize_evm_tx_hash('0x2e24b174cfd45fc7a8002f404ecebf65188520519658b0b943a98ca00d8eb063')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1779805811000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000046638289164438'),
            location_label=ethereum_accounts[0],
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=662,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_AZTEC,
            amount=FVal(reward_amount := '2992.499999999999999999'),
            location_label=ethereum_accounts[0],
            notes=f'Receive {reward_amount} AZTEC staking rewards',
            counterparty=CPT_AZTEC,
            address=string_to_evm_address('0xB1CD3a55f266DD76cB5c78aFa63c2E50A908C1F9'),
        ),
    ]
