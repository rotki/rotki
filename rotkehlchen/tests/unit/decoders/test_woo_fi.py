from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.woo_fi.constants import CPT_WOO_FI, WOO_CROSS_SWAP_ROUTER_V5
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    FVal,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_swap_token_to_token(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf68aaf2b718ce8cc1b16a3961885cf61a1538bcacf593127e64501e2af42242d')),  # noqa: E501,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1771520287000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000466714548'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        amount=FVal(spend_amount := '10'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in WOOFi',
        counterparty=CPT_WOO_FI,
        address=string_to_evm_address('0x5520385bFcf07Ec87C4c53A7d8d65595Dff69FA4'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:42161/erc20:0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f'),
        amount=FVal(receive_amount := '0.00015134'),
        location_label=user_address,
        notes=f'Receive {receive_amount} WBTC after WOOFi swap',
        counterparty=CPT_WOO_FI,
        address=string_to_evm_address('0x5520385bFcf07Ec87C4c53A7d8d65595Dff69FA4'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x7a27075aCcBbC212b703fafbdC82146214Ba0469']])
def test_swap_token_to_native(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x39db7fc22c237e649949443d596e065259d527bd1c093413cfcc14c2b9faf4a9')),  # noqa: E501,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1759058093000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000018437422976'),
        location_label=(user_address := optimism_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=Asset('eip155:10/erc20:0x9Bcef72be871e61ED4fBbc7630889beE758eb81D'),
        amount=FVal('0'),
        location_label=user_address,
        notes=f'Revoke rETH spending approval of {user_address} by 0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7',  # noqa: E501
        address=string_to_evm_address('0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:10/erc20:0x9Bcef72be871e61ED4fBbc7630889beE758eb81D'),
        amount=FVal(spend_amount := '0.1'),
        location_label=user_address,
        notes=f'Swap {spend_amount} rETH in WOOFi',
        counterparty=CPT_WOO_FI,
        address=string_to_evm_address('0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(receive_amount := '0.114269398031850807'),
        location_label=user_address,
        notes=f'Receive {receive_amount} ETH after WOOFi swap',
        counterparty=CPT_WOO_FI,
        address=string_to_evm_address('0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb7ca6DcBfFE3e53cd015F86bA7721d3912ADf749']])
def test_bridge_deposit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x394b832b9722803aa46c1c4547ec8d10a80ac05479f1483dbc8f8bfc7c586e89')),  # noqa: E501,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1770214811000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.001209661472600064'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
        amount=FVal(bridge_amount := '302'),
        location_label=user_address,
        notes=f'Bridge {bridge_amount} USDT from Ethereum to Arbitrum One via WOOFi',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(bridge_fee_amount := '0.000044440604064392'),
        location_label=user_address,
        notes=f'Spend {bridge_fee_amount} ETH as WOOFi bridge fee',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xfFbC6441Ea7Cd86F7c552f9BB825106B419c4041']])
def test_bridge_deposit_and_swap(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x221118a401c4656abfdda1080eed33d066b7f6004753b7dfb86bae61f30e0b44')),  # noqa: E501,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1770077975000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00128340456296965'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
        amount=FVal(spend_amount := '152.67085'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDT in WOOFi',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=FVal(bridge_amount := '152.537753'),
        location_label=user_address,
        notes=f'Receive {bridge_amount} USDC after WOOFi swap',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=FVal(bridge_amount),
        location_label=user_address,
        notes=f'Bridge {bridge_amount} USDC from Ethereum to Base via WOOFi',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(bridge_fee_amount := '0.000031978907291093'),
        location_label=user_address,
        notes=f'Spend {bridge_fee_amount} ETH as WOOFi bridge fee',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x901B1C0193316cad71BcA4004B7a485D380d8316']])
def test_bridge_withdrawal(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xd1cfab97be91c44e897e17cf31f256ea8199e3ea1c889630ca67998962218720')),  # noqa: E501,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=163,
        timestamp=TimestampMS(1771399301000),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
        amount=FVal(bridge_amount := '10.993256'),
        location_label=optimism_accounts[0],
        notes=f'Bridge {bridge_amount} USDC from Polygon POS to Optimism via WOOFi',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x2BddDaCAFAd9E834d515C40CC61407E55f8bD0A0']])
def test_bridge_withdrawal_and_swap(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x0f17b99ddcb548baff6f493f578aadb509cde5dd1396ef177db86098a2766a88')),  # noqa: E501,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1771399466000)),
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        amount=FVal(bridge_amount := '4.193303'),
        location_label=(user_address := polygon_pos_accounts[0]),
        notes=f'Bridge {bridge_amount} USDC from Arbitrum One to Polygon POS via WOOFi',
        counterparty=CPT_WOO_FI,
        address=WOO_CROSS_SWAP_ROUTER_V5,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'),
        amount=FVal(bridge_amount),
        location_label=user_address,
        notes=f'Swap {bridge_amount} USDC in WOOFi',
        counterparty=CPT_WOO_FI,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:137/erc20:0x0000000000000000000000000000000000001010'),
        amount=FVal(receive_amount := '37.774004660765756189'),
        location_label=user_address,
        notes=f'Receive {receive_amount} POL after WOOFi swap',
        counterparty=CPT_WOO_FI,
    )]
