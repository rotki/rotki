from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.firebird_finance.constants import CPT_FIREBIRD_FINANCE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BSC_BNB, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_swap_erc20_tokens(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9e97c7f79e788ebaa815cbee019f1dbb6cb80c4dd5bb0957fd989af130d85445')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, approval_amount, out_amount, in_amount = arbitrum_one_accounts[0], TimestampMS(1704018154000), '0.0001858737', '999999999999999999999174', '825', '1286.844424'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x912CE59144191C1204E64559FE8253a0e49E6548'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set ARB spending approval of {user_address} by 0x0c6134Abc08A1EafC3E2Dc9A5AD023Bb08Da86C3 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x0c6134Abc08A1EafC3E2Dc9A5AD023Bb08Da86C3'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:42161/erc20:0x912CE59144191C1204E64559FE8253a0e49E6548'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} ARB in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0x1f5A3c42F26b72c917B3625c7a964ca33600Fa25'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} USDC as the result of a swap in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0x1f5A3c42F26b72c917B3625c7a964ca33600Fa25'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xA739d838855E7253e41d5A6EEBD6e874c479aac5']])
def test_swap_eth_for_erc20_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe44fe9c5cdd8b1b2d0ab0691fc9633d49146bf665575a83e0c6a3e9e70e70203')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = ethereum_accounts[0], TimestampMS(1672529231000), '0.004636897380394857', '0.4', '1007.80191074694080899'  # noqa: E501
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
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} ETH in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xe0C38b2a8D09aAD53f1C67734B9A95E43d5981c0'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x777172D858dC1599914a1C4c6c9fC48c99a60990'),
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} SOLID as the result of a swap in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xe0C38b2a8D09aAD53f1C67734B9A95E43d5981c0'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('optimism_accounts', [['0xc15534EA729972fc21AEDE69cB7Ca16D60E8D342']])
def test_swap_erc20_token_for_eth(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc19f8f547c49c3f35dae993b713d95cce79aa425563fd28aeaca2510ebb95059')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = optimism_accounts[0], TimestampMS(1708454525000), '0.000261272046054672', '24.828647237813394885', '0.03345269400143805'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0x4200000000000000000000000000000000000042'),
            amount=FVal(out_amount),
            location_label=user_address,
            notes=f'Swap {out_amount} OP in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xDda1aFE34928450FFf2af5C051E5E0c0853e21C9'),
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(in_amount),
            location_label=user_address,
            notes=f'Receive {in_amount} ETH as the result of a swap in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xDda1aFE34928450FFf2af5C051E5E0c0853e21C9'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x887e8b6119B38C60cb03CAb204C0A704c6E0A473']])
def test_swap_erc20_token_for_bnb(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x38196d5c4c890ba5fbc897868da0fba917394f64daedb95c494fbf2c4da1145a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, out_amount, in_amount, approve_amount = binance_sc_accounts[0], TimestampMS(1708623602000), '0.0003746295', '2.643598626182094592', '0.006965207273931161', '115792089237316195423570985008687907853269984665640564039454.940409286947545343'  # noqa: E501
    a_frax = Asset('eip155:56/erc20:0x90C97F71E18723b0Cf0dfa30ee176Ab653E89F40')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} BNB for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_frax,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set FRAX spending approval of {user_address} by 0x92e4F29Be975C1B1eB72E77De24Dccf11432a5bd to {approve_amount}',  # noqa: E501
        address=string_to_evm_address('0x92e4F29Be975C1B1eB72E77De24Dccf11432a5bd'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_frax,
        amount=FVal(out_amount),
        location_label=user_address,
        notes=f'Swap {out_amount} FRAX in Firebird Finance',
        counterparty=CPT_FIREBIRD_FINANCE,
        address=string_to_evm_address('0x0852Dba413446B2fd8Cc0e45c96b7F226b09e992'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BSC_BNB,
        amount=FVal(in_amount),
        location_label=user_address,
        notes=f'Receive {in_amount} BNB as the result of a swap in Firebird Finance',
        counterparty=CPT_FIREBIRD_FINANCE,
        address=string_to_evm_address('0x0852Dba413446B2fd8Cc0e45c96b7F226b09e992'),
    )]
