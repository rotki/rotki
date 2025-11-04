from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V2
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_POL
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xE7C3e5D4D38bd0e767f9913cfc5Cd8CF25280cAD']])
def test_swap(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x458e77cd77833f48d314edcea1323dd123c3b1f5d4a4b375674cfc4292810548')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1747572751000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POL,
        amount=FVal(gas_amount := '0.01856947464736948'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),
        amount=FVal(approve_amount := '999999888'),
        location_label=user_address,
        notes=f'Set DAI spending approval of {user_address} by 0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff to {approve_amount}',  # noqa: E501
        address=string_to_evm_address('0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),
        amount=FVal(spend_amount := '112'),
        location_label=user_address,
        notes=f'Swap {spend_amount} DAI in Quickswap V2',
        counterparty=CPT_QUICKSWAP_V2,
        address=string_to_evm_address('0x882df4B0fB50a229C3B4124EB18c759911485bFb'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=3,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0xeB51D9A39AD5EEF215dC0Bf39a8821ff804A0F01'),
        amount=FVal(receive_amount := '6.56009079'),
        location_label=user_address,
        notes=f'Receive {receive_amount} LGNS as the result of a swap in Quickswap V2',
        counterparty=CPT_QUICKSWAP_V2,
        address=string_to_evm_address('0x882df4B0fB50a229C3B4124EB18c759911485bFb'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0xBc426D4c5d5d86CC657f331c58b054cf2f14C0E5']])
def test_add_liquidity(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x7f8e11dae4291f0e5829af1d1fd023c9aa32e41f1546ca16765eb15aa1672bd1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    pool_address = string_to_evm_address('0x5C72ECd763Be11E8E202490bAC14B12402E77716')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1756221523000)),
        location=Location.POLYGON_POS,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POL,
        amount=FVal(gas_amount := '0.090286647653894201'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Burn {gas_amount} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=1,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:137/erc20:0x8893CA7df4c27c8001599688deA31B514d169e59'),
        amount=FVal(deposit1_amount := '23814000000000'),
        location_label=user_address,
        notes=f'Deposit {deposit1_amount} BabyWLFI to Quickswap V2 LP {pool_address}',
        extra_data={'pool_address': pool_address},
        counterparty=CPT_QUICKSWAP_V2,
        address=pool_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=2,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        amount=FVal(deposit2_amount := '4072.304372'),
        location_label=user_address,
        notes=f'Deposit {deposit2_amount} USDC to Quickswap V2 LP {pool_address}',
        extra_data={'pool_address': pool_address},
        counterparty=CPT_QUICKSWAP_V2,
        address=pool_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        sequence_index=3,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:137/erc20:0x5C72ECd763Be11E8E202490bAC14B12402E77716'),
        amount=FVal(receive_amount := '0.000311412678473733'),
        location_label=user_address,
        notes=f'Receive {receive_amount} UNI-V2 USDC-BabyWLFI from Quickswap V2 pool',
        counterparty=CPT_QUICKSWAP_V2,
        address=pool_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x3520f30bC0dFa7C2A3577B23Ad689BaD81D6709c']])
def test_remove_liquidity(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc648a3e4b22fcbffd5375bd3515fc7a41f19cc6f1c3863f475f85a189bfcd8f2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    pool_address = string_to_evm_address('0x3099A7C284610897baAa43cBDC06469E44A06ce1')
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1755330089000)),
        location=Location.BASE,
        sequence_index=0,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000299046567323'),
        location_label=(user_address := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.BASE,
        sequence_index=1,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x3099A7C284610897baAa43cBDC06469E44A06ce1'),
        amount=FVal(spend_amount := '0.000001121717184194'),
        location_label=user_address,
        notes=f'Send {spend_amount} UNI-V2 WETH-USDC to Quickswap V2 pool',
        counterparty=CPT_QUICKSWAP_V2,
        address=pool_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.BASE,
        sequence_index=2,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x4200000000000000000000000000000000000006'),
        amount=FVal(weth_amount := '0.016920866385895595'),
        location_label=user_address,
        notes=f'Remove {weth_amount} WETH from Quickswap V2 LP {pool_address}',
        extra_data={'pool_address': pool_address},
        counterparty=CPT_QUICKSWAP_V2,
        address=pool_address,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        location=Location.BASE,
        sequence_index=3,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=FVal(usdc_amount := '75.240037'),
        location_label=user_address,
        notes=f'Remove {usdc_amount} USDC from Quickswap V2 LP {pool_address}',
        extra_data={'pool_address': pool_address},
        counterparty=CPT_QUICKSWAP_V2,
        address=pool_address,
    )]
