from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BSC_BNB, A_ETH, A_OP, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3eD56F271Ea3B86523e44ff1eE0D21f40d68d94F']])
def test_swap_eth_to_token(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a swap from native to token via the V4 router and pool manager."""
    tx_hash = deserialize_evm_tx_hash('0x4a3d3205385105f5159b905c8a1471a6328452909d826f55ef2f0690381d9aa7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755181019000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000981255025667122'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(spend_amount := '0.201453662983962514'),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=(universal_router := string_to_evm_address('0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af')),  # noqa: E501
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(receive_amount := '930.157818'),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC after a swap in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=universal_router,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        amount=FVal(fee_amount := '2.325394'),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDC as a Uniswap V4 fee',
        counterparty=CPT_UNISWAP_V4,
        address=universal_router,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xB2Fb1E31bAFFaCeE52D4B9AB79009EcCCCB856e5']])
def test_swap_token_to_eth(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a swap from token to native via the V4 router and a V3 pool."""
    tx_hash = deserialize_evm_tx_hash('0x3ea90c2f3882c798185d135307a5ee3c366790c62bf9755f1035ff6bd9fb5381')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755267925000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000007410256564'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:42161/erc20:0xc87B37a581ec3257B734886d9d3a581F5A9d056c'),
        amount=FVal(spend_amount := '3908.26'),
        location_label=user_address,
        notes=f'Swap {spend_amount} ATH in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=(universal_router := string_to_evm_address('0x5cbddc44F31067dF328aA7a8Da03aCa6F2EdD2aD')),  # noqa: E501
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(receive_amount := '0.029015039707052972'),
        location_label=user_address,
        notes=f'Receive {receive_amount} ETH after a swap in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=universal_router,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(fee_amount := '0.000072537599267632'),
        location_label=user_address,
        notes=f'Spend {fee_amount} ETH as a Uniswap V4 fee',
        counterparty=CPT_UNISWAP_V4,
        address=universal_router,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x09ae5e9e7E64F68fB9085EA4Cda20Dfb8428Ba46']])
def test_swap_token_to_token(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a swap from token to token via the V4 router and pool manager."""
    tx_hash = deserialize_evm_tx_hash('0xb1501f9d4d188c769cd1bda14a5fe87e828470fbef968bb8e5e7b702344e8e73')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755523647000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000046217643623'),
        location_label=(user_address := optimism_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=76,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_usdce := Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607')),
        amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640564039457584007913128.639935'),  # noqa: E501
        location_label=user_address,
        notes=f'Set USDC.e spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=77,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_usdce,
        amount=ONE,
        location_label=user_address,
        notes='Swap 1 USDC.e in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=(universal_router := string_to_evm_address('0x9a13F98Cb987694C9F086b1F5eB990EeA8264Ec3')),  # noqa: E501
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=78,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
        amount=FVal(receive_amount := '0.999889'),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC after a swap in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=universal_router,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x5dFF28ea9284C853baA4b8316Aeaf558e3d12488']])
def test_swap_token_to_bnb(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a swap from token to native on a non-ETH chain."""
    tx_hash = deserialize_evm_tx_hash('0xf4da4f7c2da6f02db3de87a2d11b1da3a37a7b92bbfad0f09d9bc9cfd0282793')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755538889000)),
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('BNB'),
        amount=FVal(gas_amount := '0.00001673050033461'),
        location_label=(user_address := binance_sc_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} BNB for gas',
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_bsc_eth := Asset('eip155:56/erc20:0x2170Ed0880ac9A755fd29B2688956BD959F933F8')),
        amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640564039457.578777913129639935'),  # noqa: E501
        location_label=user_address,
        notes=f'Set ETH spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {approval_amount}',  # noqa: E501
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_bsc_eth,
        amount=FVal(spend_amount := '0.00523'),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=(pool_address := string_to_evm_address('0x0f338Ec12d3f7C3D77A4B9fcC1f95F3FB6AD0EA6')),  # noqa: E501
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BSC_BNB,
        amount=FVal(receive_amount := '0.026932753345635391'),
        location_label=user_address,
        notes=f'Receive {receive_amount} BNB after a swap in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=pool_address,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(fee_amount := '0.000067331883364088'),
        location_label=user_address,
        notes=f'Spend {fee_amount} BNB as a Uniswap V4 fee',
        counterparty=CPT_UNISWAP_V4,
        address=pool_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [[
    '0x66C1158AE808bF4f7Da691616edb1dFAC1ddb58d',
    '0x070143e489aa791C10b3b39c7CAdf45c36BA9e60',
]])
def test_multi_pool_swap_to_second_address(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a swap routed through two V3 pools with the result
    sent to a second address.
    """
    tx_hash = deserialize_evm_tx_hash('0x8ed162b0235bcd00361e1c888628985d406c9307e8d1b9544ab979eb67e5b606')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755280243000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000226223279121'),
        location_label=optimism_accounts[0],
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OP,
        amount=FVal(spend_amount := '2.029975300816905024'),
        location_label=optimism_accounts[0],
        notes=f'Swap {spend_amount} OP in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=(pool_address := string_to_evm_address('0xB2Ac2E5A3684411254d58B1C5A542212b782114D')),  # noqa: E501
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
        amount=FVal(receive_amount := '1.468375'),
        location_label=optimism_accounts[1],
        notes=f'Receive {receive_amount} USDC after a swap in Uniswap V4',
        counterparty=CPT_UNISWAP_V4,
        address=pool_address,
    )]
