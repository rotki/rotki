from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.hyperliquid.modules.kittenswap.constants import CPT_KITTENSWAP
from rotkehlchen.constants.assets import A_HYPE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.hyperliquid import HYPERLIQUID_PUBLIC_RPC_NODES
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.hyperliquid.node_inquirer import HyperliquidInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xFB3A939Cb06eeF36E1ceD48bdba1fcEe177Ac7f4']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_kittenswap_hype_for_khype(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x773daa37d6035cd7e991acc49776e5a02a4cfd71c94f5c3f0c113096660e679e')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1761149165000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.0000692189184'),
            location_label=(user_address := hyperliquid_accounts[0]),
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_HYPE,
            amount=FVal(hype_amount := '5'),
            location_label=user_address,
            notes=f'Swap {hype_amount} HYPE in KittenSwap',
            counterparty=CPT_KITTENSWAP,
            address=string_to_evm_address('0xF75584eF6673aD213a685a1B58Cc0330B8eA22Cf'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:999/erc20:0xfD739d4e423301CE9385c1fb8850539D657C296D'),
            amount=FVal(khype_amount := '4.980253651738044784'),
            location_label=user_address,
            notes=f'Receive {khype_amount} kHYPE as the result of a swap in KittenSwap',
            counterparty=CPT_KITTENSWAP,
            address=string_to_evm_address('0xF75584eF6673aD213a685a1B58Cc0330B8eA22Cf'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('hyperliquid_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [HYPERLIQUID_PUBLIC_RPC_NODES])
def test_kittenswap_receive_before_spend(
        hyperliquid_inquirer: HyperliquidInquirer,
        hyperliquid_accounts: list[ChecksumEvmAddress],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=hyperliquid_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xab4c51d5298b7c322969410ee768454ae7c833daa54ad1b3c3df97f26634efb8')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1759404831000)),
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_HYPE,
            amount=FVal(gas_amount := '0.00005729206762'),
            location_label=(user_address := hyperliquid_accounts[0]),
            notes=f'Burn {gas_amount} HYPE for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=(usdt0 := Asset('eip155:999/erc20:0xB8CE59FC3717ada4C02eaDF9682A9e934F625ebb')),
            amount=FVal(0),
            location_label=user_address,
            notes=f'Revoke USDT0 spending approval of {user_address} by {(router := string_to_evm_address("0x0a0758d937d1059c356D4714e57F5df0239bce1A"))}',  # noqa: E501
            address=router,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_subtype=HistoryEventSubType.SPEND,
            asset=usdt0,
            amount=FVal(usdt0_amount := '44.42406'),
            location_label=user_address,
            notes=f'Swap {usdt0_amount} USDT0 in KittenSwap',
            counterparty=CPT_KITTENSWAP,
            address=router,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.HYPERLIQUID,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_HYPE,
            amount=FVal(hype_amount := '0.893418842588613752'),
            location_label=user_address,
            notes=f'Receive {hype_amount} HYPE as the result of a swap in KittenSwap',
            counterparty=CPT_KITTENSWAP,
            address=router,
        ),
    ]
