import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.firebird_finance.constants import CPT_FIREBIRD_FINANCE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_swap_erc20_tokens(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9e97c7f79e788ebaa815cbee019f1dbb6cb80c4dd5bb0957fd989af130d85445')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_amount, approval_amount, out_amount, in_amount = arbitrum_one_accounts[0], TimestampMS(1704018154000), '0.0001858737', '999999999999999999999174', '825', '1286.844424'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=13,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x912CE59144191C1204E64559FE8253a0e49E6548'),
            balance=Balance(FVal(approval_amount)),
            location_label=user_address,
            notes=f'Set ARB spending approval of {user_address} by 0x0c6134Abc08A1EafC3E2Dc9A5AD023Bb08Da86C3 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x0c6134Abc08A1EafC3E2Dc9A5AD023Bb08Da86C3'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=14,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:42161/erc20:0x912CE59144191C1204E64559FE8253a0e49E6548'),
            balance=Balance(FVal(out_amount)),
            location_label=user_address,
            notes=f'Swap {out_amount} ARB in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0x1f5A3c42F26b72c917B3625c7a964ca33600Fa25'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=15,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            balance=Balance(FVal(in_amount)),
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
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            balance=Balance(FVal(out_amount)),
            location_label=user_address,
            notes=f'Swap {out_amount} ETH in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xe0C38b2a8D09aAD53f1C67734B9A95E43d5981c0'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:1/erc20:0x777172D858dC1599914a1C4c6c9fC48c99a60990'),
            balance=Balance(FVal(in_amount)),
            location_label=user_address,
            notes=f'Receive {in_amount} SOLID as the result of a swap in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xf65F4aB80491fB8Db2ECD1fFC63e779261bf0B36'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xc15534EA729972fc21AEDE69cB7Ca16D60E8D342']])
def test_swap_erc20_token_for_eth(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc19f8f547c49c3f35dae993b713d95cce79aa425563fd28aeaca2510ebb95059')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, out_amount, in_amount = optimism_accounts[0], TimestampMS(1708454525000), '0.000261272046054672', '24.828647237813394885', '0.03345269400143805'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_amount)),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0x4200000000000000000000000000000000000042'),
            balance=Balance(FVal(out_amount)),
            location_label=user_address,
            notes=f'Swap {out_amount} OP in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xDda1aFE34928450FFf2af5C051E5E0c0853e21C9'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.TRADE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            balance=Balance(FVal(in_amount)),
            location_label=user_address,
            notes=f'Receive {in_amount} ETH as the result of a swap in Firebird Finance',
            counterparty=CPT_FIREBIRD_FINANCE,
            address=string_to_evm_address('0xDda1aFE34928450FFf2af5C051E5E0c0853e21C9'),
        ),
    ]
    assert events == expected_events
