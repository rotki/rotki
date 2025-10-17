from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.uniswap.constants import CPT_UNISWAP_V4
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_ETH,
    A_OP,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_WETH_POLYGON,
)
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
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer


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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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
        tx_ref=tx_hash,
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


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x7E25f8488D25152437dBECC787F655966DD00C67']])
def test_create_lp_position(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x2277ee48d4e5394a59500a9f70ab29c12b27b28398973e6ca2666143dd690358')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755608652000)),
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_amount := '0.012086010300538782'),
        location_label=(user_address := polygon_pos_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} POL for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=446,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_oauto := Asset('eip155:137/erc20:0x7f426F6Dc648e50464a0392E60E1BB465a67E9cf')),
        amount=FVal(oauto_approval := '577.561778438973357269'),
        location_label=user_address,
        notes=f'Set oAUTO spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {oauto_approval}',  # noqa: E501
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=448,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=(a_usdt := Asset('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')),
        amount=FVal(usdt_approval := '637.938815'),
        location_label=user_address,
        notes=f'Set USDT spending approval of {user_address} by 0x000000000022D473030F116dDEE9F6B43aC78BA3 to {usdt_approval}',  # noqa: E501
        address=string_to_evm_address('0x000000000022D473030F116dDEE9F6B43aC78BA3'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=449,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=a_oauto,
        amount=FVal(oauto_amount := '0.027630635454744533'),
        location_label=user_address,
        notes=f'Deposit {oauto_amount} oAUTO to Uniswap V4 oAUTO/USDT LP',
        counterparty=CPT_UNISWAP_V4,
        address=(pool_manager := string_to_evm_address('0x67366782805870060151383F4BbFF9daB53e5cD6')),  # noqa: E501
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=450,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=a_usdt,
        amount=FVal(usdt_amount := '10'),
        location_label=user_address,
        notes=f'Deposit {usdt_amount} USDT to Uniswap V4 oAUTO/USDT LP',
        counterparty=CPT_UNISWAP_V4,
        address=pool_manager,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=451,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:137/erc721:0x1Ec2eBf4F37E7363FDfe3551602425af0B3ceef9/39018'),
        amount=ONE,
        location_label=user_address,
        notes='Create Uniswap V4 LP with id 39018',
        counterparty=CPT_UNISWAP_V4,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_create_lp_position_with_native_refund(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding of a lp creation with a native token deposit where a small amount of the
    deposited native token is returned (receive amount is subtracted from the deposit and the
    receive event is removed).
    """
    tx_hash = deserialize_evm_tx_hash('0xa604ae170e78c203330605619e82c82337daf8d1af52b78cdf82db82c3f9deb4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755696178000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000004281262202'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.009160753478273742'),
        location_label=user_address,
        notes=f'Deposit {eth_amount} ETH to Uniswap V4 ETH/USDC LP',
        counterparty=CPT_UNISWAP_V4,
        address=string_to_evm_address('0xd88F38F930b7952f2DB2432Cb002E7abbF3dD869'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
        amount=FVal('50'),
        location_label=user_address,
        notes='Deposit 50 USDC to Uniswap V4 ETH/USDC LP',
        counterparty=CPT_UNISWAP_V4,
        address=string_to_evm_address('0x360E68faCcca8cA495c1B759Fd9EEe466db9FB32'),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:42161/erc721:0xd88F38F930b7952f2DB2432Cb002E7abbF3dD869/61908'),
        amount=ONE,
        location_label=user_address,
        notes='Create Uniswap V4 LP with id 61908',
        counterparty=CPT_UNISWAP_V4,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x8605355cA4E07C1B2cEB548a052876A18028d7Fd']])
def test_increase_liquidity(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xe65d2fe847aa7e8143f01f67567f2659efa750eaa254421aeb27ba090df5ea2e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755539811000)),
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000000225013656822'),
        location_label=(user_address := optimism_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
        amount=FVal(usdc_amount := '0.458611'),
        location_label=user_address,
        notes=f'Deposit {usdc_amount} USDC to Uniswap V4 USDC/OP LP',
        counterparty=CPT_UNISWAP_V4,
        address=(pool_manager := string_to_evm_address('0x9a13F98Cb987694C9F086b1F5eB990EeA8264Ec3')),  # noqa: E501
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_OP,
        amount=FVal(op_amount := '0.799999094140701646'),
        location_label=user_address,
        notes=f'Deposit {op_amount} OP to Uniswap V4 USDC/OP LP',
        counterparty=CPT_UNISWAP_V4,
        address=pool_manager,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x076E7D08170036FFa56142372723c03326ee27E9']])
def test_exit_lp_position(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xd96f3bdbdcb28e0e038a14afd343858a8dc72ddb41c16651a07d9422b6b04694')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755608207000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00005128618368435'),
        location_label=(user_address := ethereum_accounts[0]),
        counterparty=CPT_GAS,
        notes=f'Burn {gas_amount} ETH for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:1/erc721:0xbD216513d74C8cf14cf4747E6AaA6420FF64ee9e/51028'),
        amount=ONE,
        location_label=user_address,
        notes='Exit Uniswap V4 LP with id 51028',
        counterparty=CPT_UNISWAP_V4,
        address=ZERO_ADDRESS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.01122274372981923'),
        location_label=user_address,
        notes=f'Withdraw {eth_amount} ETH from Uniswap V4 ETH/USDC LP',
        counterparty=CPT_UNISWAP_V4,
        address=(pool_manager := string_to_evm_address('0x000000000004444c5dc75cB358380D2e3dE08A90')),  # noqa: E501
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_USDC,
        amount=FVal(usdc_amount := '175118.699175'),
        location_label=user_address,
        notes=f'Withdraw {usdc_amount} USDC from Uniswap V4 ETH/USDC LP',
        counterparty=CPT_UNISWAP_V4,
        address=pool_manager,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x2fCC69eaa8c9F33538CBac50eb5432c422825e6D']])
def test_decrease_liquidity(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x550832040e57647103a03e23eba5ce869f8a96c3e8b92f1f9258024a286e2525')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1755609920000)),
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal('0.005868403632678156'),
        location_label=(user_address := polygon_pos_accounts[0]),
        counterparty=CPT_GAS,
        notes='Burn 0.005868403632678156 POL for gas',
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal('20.49016382840257149'),
        location_label=user_address,
        notes='Withdraw 20.49016382840257149 POL from Uniswap V4 POL/WETH LP',
        counterparty=CPT_UNISWAP_V4,
        address=(pool_manager := string_to_evm_address('0x67366782805870060151383F4BbFF9daB53e5cD6')),  # noqa: E501
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_WETH_POLYGON,
        amount=FVal('0.001429032787070825'),
        location_label=user_address,
        notes='Withdraw 0.001429032787070825 WETH from Uniswap V4 POL/WETH LP',
        counterparty=CPT_UNISWAP_V4,
        address=pool_manager,
    )]
