from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.magpie.constants import CPT_MAGPIE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.types import ChecksumEvmAddress

# Router addresses for each chain
BASE_MAGPIE_V3_ROUTER = string_to_evm_address('0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B')
BASE_MAGPIE_V3_1_ROUTER = string_to_evm_address('0x5E766616AaBFB588E23a8EA854e9dbd1042afFD3')
ARBITRUM_MAGPIE_V3_ROUTER = string_to_evm_address('0x34CdCe58CBdC6C54f2AC808A24561D0AB18Ca8Be')
ETHEREUM_MAGPIE_V3_1_ROUTER = string_to_evm_address('0xA6E941eaB67569ca4522f70d343714fF51d571c4')
POLYGON_MAGPIE_V3_1_ROUTER = string_to_evm_address('0xA6E941eaB67569ca4522f70d343714fF51d571c4')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x3a20BA3678C5c40F7CD48EB373fF8a501d170534']])
def test_magpie_eth_to_token_swap(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie ETH to token swap on Base"""
    tx_hash = deserialize_evm_tx_hash(
        '0xe0694a8b16649877e82f7039e6e61265552e62c83d274e3994f4f8855a4eb352',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    timestamp = TimestampMS(1747100759000)
    gas_amount = '0.000000857490760886'  # actual gas from test
    spend_amount = '0.00005'  # 50000000000000 / 10^18
    receive_amount = '3.603360047987326035'  # actual amount from test
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} ETH in Magpie',
            counterparty=CPT_MAGPIE,
            address=BASE_MAGPIE_V3_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:8453/erc20:0xA88594D404727625A9437C3f886C7643872296AE'),
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} WELL from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=BASE_MAGPIE_V3_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xF9c6Fc43a385362C9C8364bF9C5236314607c0A5']])
def test_magpie_token_to_token_swap(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie token to token swap on Base"""
    tx_hash = deserialize_evm_tx_hash(
        '0xe8551212a0bb6f59a38883161ec11393f03ba6e8f2f71e8d3c41df0bfe0a71c6',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]

    timestamp = TimestampMS(1747098901000)
    gas_amount = '0.000005597469523105'  # actual gas from output
    rabby_fee_amount = '0.009750330804687233'  # Fee to Rabby
    spend_amount = '3.890381991070206089'  # VIRTUAL swapped (router amount)
    receive_amount = '7.574831'  # USDC received
    virtual_asset = Asset('eip155:8453/erc20:0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b')
    usdc_asset = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')  # USDC

    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=118,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=virtual_asset,
            amount=FVal('3.890381991070206089'),
            location_label=user_address,
            notes=(
                'Set VIRTUAL spending approval of 0xF9c6Fc43a385362C9C8364bF9C5236314607c0A5 '
                'by 0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B to 3.890381991070206089'
            ),
            address=BASE_MAGPIE_V3_ROUTER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=120,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=virtual_asset,
            amount=ZERO,
            location_label=user_address,
            notes=(
                'Revoke VIRTUAL spending approval of 0xF9c6Fc43a385362C9C8364bF9C5236314607c0A5 '
                'by 0xEF42f78d25f4c681dcaD2597fA04877ff802eF4B'
            ),
            address=BASE_MAGPIE_V3_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=121,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=virtual_asset,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} VIRTUAL in Magpie',
            counterparty=CPT_MAGPIE,
            address=BASE_MAGPIE_V3_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=122,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=usdc_asset,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} USDC from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=BASE_MAGPIE_V3_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=123,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.FEE,
            asset=virtual_asset,
            amount=FVal(rabby_fee_amount),
            location_label=user_address,
            notes=f'Pay {rabby_fee_amount} VIRTUAL as Rabby interface fee',
            counterparty=CPT_MAGPIE,
            address=BASE_MAGPIE_V3_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xa304816C9c78505714f24FC13222fE07Ce0cc711']])
def test_magpie_arbitrum_token_to_token_swap(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie token to token swap on Arbitrum"""
    tx_hash = deserialize_evm_tx_hash(
        '0xfb27923fce50ff6769e364c48b8fd32d1bf83e4c2b67bdc49d12627873c5908a',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address = arbitrum_one_accounts[0]

    timestamp = TimestampMS(1747117715000)
    gas_amount = '0.0000023453'  # actual gas from transaction
    rabby_fee_amount = '2.240491123389503579'  # TROVE Fee to Rabby
    spend_amount = '893.955958232411928011'  # TROVE swapped (router amount)
    receive_amount = '0.000813622663851767'  # ETH received
    trove_asset = Asset('eip155:42161/erc20:0x982239D38Af50B0168dA33346d85Fb12929c4c07')

    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=7,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=trove_asset,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=(
                'Set TROVE spending approval of 0xa304816C9c78505714f24FC13222fE07Ce0cc711 '
                'by 0x34CdCe58CBdC6C54f2AC808A24561D0AB18Ca8Be to 893.955958232411928011'
            ),
            address=string_to_evm_address('0x34CdCe58CBdC6C54f2AC808A24561D0AB18Ca8Be'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=trove_asset,
            amount=ZERO,
            location_label=user_address,
            notes=(
                'Revoke TROVE spending approval of 0xa304816C9c78505714f24FC13222fE07Ce0cc711 '
                'by 0x34CdCe58CBdC6C54f2AC808A24561D0AB18Ca8Be'
            ),
            address=string_to_evm_address('0x34CdCe58CBdC6C54f2AC808A24561D0AB18Ca8Be'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=trove_asset,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} TROVE in Magpie',
            counterparty=CPT_MAGPIE,
            address=string_to_evm_address('0x9164424A33a89202040F02170431073c59eFa1A9'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} ETH from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=string_to_evm_address('0x9164424A33a89202040F02170431073c59eFa1A9'),
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_subtype=HistoryEventSubType.FEE,
            asset=trove_asset,
            amount=FVal(rabby_fee_amount),
            location_label=user_address,
            notes=f'Pay {rabby_fee_amount} TROVE as Rabby interface fee',
            counterparty=CPT_MAGPIE,
            address=string_to_evm_address('0x9164424A33a89202040F02170431073c59eFa1A9'),
        ),
    ]

    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe4B13d4de7E85E2a763BD440Bc9bf921C69Bc905']])
def test_magpie_ethereum_usds_to_usdc_swap(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie USDS to USDC swap on Ethereum with Rabby fee"""
    tx_hash = deserialize_evm_tx_hash(
        '0x8a764813d69a773b1883eb5b64e33a7fd168f65865027fe20e0774943a10f764',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]

    timestamp = TimestampMS(1749670655000)
    gas_amount = '0.000536018493464816'  # actual gas cost
    rabby_fee_amount = '0.015'  # USDS fee to Rabby
    spend_amount = '5.985'  # USDS amount to Magpie
    receive_amount = '5.983651'  # USDC received
    usds_asset = Asset('eip155:1/erc20:0xdC035D45d973E3EC169d2276DDab16f1e407384F')
    usdc_asset = Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48')

    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=usds_asset,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} USDS in Magpie',
            counterparty=CPT_MAGPIE,
            address=ETHEREUM_MAGPIE_V3_1_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=usdc_asset,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} USDC from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=ETHEREUM_MAGPIE_V3_1_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.FEE,
            asset=usds_asset,
            amount=FVal(rabby_fee_amount),
            location_label=user_address,
            notes=f'Pay {rabby_fee_amount} USDS as Rabby interface fee',
            counterparty=CPT_MAGPIE,
            address=ETHEREUM_MAGPIE_V3_1_ROUTER,
        ),
    ]

    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x6361f989EFf9fE22E8a8C08aCe34f0d30b760a4E']])
def test_magpie_polygon_pol_to_usdc_swap(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test decoding a Magpie POL to USDC swap on Polygon"""
    tx_hash = deserialize_evm_tx_hash(
        '0x68ee836e5e78f30d084f88e47450217af0d199a8b24784ec799b837aa458888a',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=polygon_pos_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address = polygon_pos_accounts[0]

    timestamp = TimestampMS(1749654622000)
    gas_amount = '0.022836'  # actual gas from events
    spend_amount = '24.988096505635070242'  # POL sent to Magpie (actual from events)
    receive_amount = '5.809487'  # USDC received (actual from events)
    pol_asset = Asset('eip155:137/erc20:0x0000000000000000000000000000000000001010')  # POL native
    usdc_asset = Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359')  # USDC.e

    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=pol_asset,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} POL for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=pol_asset,
            amount=FVal(spend_amount),
            location_label=user_address,
            notes=f'Swap {spend_amount} POL in Magpie',
            counterparty=CPT_MAGPIE,
            address=POLYGON_MAGPIE_V3_1_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=usdc_asset,
            amount=FVal(receive_amount),
            location_label=user_address,
            notes=f'Receive {receive_amount} USDC from Magpie swap',
            counterparty=CPT_MAGPIE,
            address=POLYGON_MAGPIE_V3_1_ROUTER,
        ),
    ]

    assert expected_events == events
