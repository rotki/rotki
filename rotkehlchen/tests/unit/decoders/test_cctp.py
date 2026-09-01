from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.cctp.constants import USDC_IDENTIFIER_ARB
from rotkehlchen.chain.base.modules.cctp.constants import USDC_IDENTIFIER_BASE
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.cctp.constants import CPT_CCTP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.modules.cctp.constants import USDC_IDENTIFIER_POLYGON
from rotkehlchen.constants.assets import A_ETH, A_POL, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.base import BASE_MAINNET_NODE
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_manager_connect_at_start', [(BASE_MAINNET_NODE,)])
@pytest.mark.parametrize('base_accounts', [['0x34B741a3D0ef8c8ef6dd490C305c5C5ca20aCa59']])
def test_receive_usdc_on_base_from_solana_v2(
        base_inquirer: BaseInquirer,
        base_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x2aeac6a78077f8a43886c282b00942285b8e607ea9099a7d4fd1b316b631b58c')  # noqa: E501
    with patch('rotkehlchen.chain.evm.transactions.EvmTransactions._query_and_save_internal_transactions_for_parent_hash'):  # Base's indexers have not indexed this recent transaction's internal calls yet  # noqa: E501
        events, _ = get_decoded_events_of_transaction(
            evm_inquirer=base_inquirer,
            tx_hash=tx_hash,
        )
    assert events == [EvmEvent(
        sequence_index=460,
        timestamp=TimestampMS(1788256855000),
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=Asset(USDC_IDENTIFIER_BASE),
        amount=FVal('7.269273'),
        location_label=base_accounts[0],
        notes='Bridge 7.269273 USDC from Solana to Base via CCTP',
        tx_ref=tx_hash,
        counterparty=CPT_CCTP,
        address=ZERO_ADDRESS,
        extra_data={'bridge': {
            'from_chain': 'solana',
            'to_chain': 8453,
            'to_address': base_accounts[0],
            'transfer_id': '0xd25fe41da9c2a8241548e59c92d2b4cccd0ebc26c9d73f7a95393dcad33d31b4',
        }},
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD156fFB54871F4562744d6Be5d6321B5BffCa3B6']])
def test_deposit_usdc_from_ethereum_to_solana_v2(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1ac8683e92b064b579244f4ca2161e54e01a343c879fb3b18ff29f69a5162dbe')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events[-1] == EvmEvent(
        sequence_index=216,
        timestamp=TimestampMS(1774849751000),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_USDC,
        amount=FVal('148.760322'),
        location_label=ethereum_accounts[0],
        notes='Bridge 148.760322 USDC from Ethereum to Solana via CCTP',
        tx_ref=tx_hash,
        counterparty=CPT_CCTP,
        address=string_to_evm_address('0xfd78EE919681417d192449715b2594ab58f5D002'),
        extra_data={'bridge': {
            'from_chain': 1,
            'to_chain': 'solana',
            'from_address': ethereum_accounts[0],
            'to_address': '3WzSRoiRj7GwrMzavq1Hu2TRQX2Y2qTVftnXeGZsxPUF',
        }},
    )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd0Adc5d079Cc486b58F1B9A28B973355C4ec9e6f']])
def test_deposit_usdc_from_ethereum_to_arbitrum_one(
        ethereum_inquirer: EthereumInquirer,
        ethereum_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xac7bb45701a4311a2c662377a4764ac694a8f6438270c1ee8a4100d4a000a511')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1716588659000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.000649402467435812'),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=300,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            amount=FVal(deposit_amount := '1839.726596'),
            location_label=ethereum_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Ethereum to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=string_to_evm_address('0xc4922d64a24675E16e1586e3e3Aa56C06fABe907'),
            extra_data={'bridge': {
                'from_chain': 1,
                'to_chain': 42161,
                'from_address': ethereum_accounts[0],
                'to_address': ethereum_accounts[0],
                'transfer_id': '62883',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xd0Adc5d079Cc486b58F1B9A28B973355C4ec9e6f']])
def test_receive_usdc_on_arbitrum_one_from_ethereum(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x9da8beb8e9ad2428ad2de132d920d27c2d6c7e0604d2977669aab219e51fd323')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1716589968000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.00000196702'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset(USDC_IDENTIFIER_ARB),
            amount=FVal(deposit_amount := '1839.726596'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Ethereum to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=ZERO_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 1,
                'to_chain': 42161,
                'to_address': arbitrum_one_accounts[0],
                'transfer_id': '62883',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x75F3785B330aadbA5DB31535995568583EA8DEA8']])
def test_deposit_usdc_from_polygon_to_arbitrum_one(
        polygon_pos_inquirer: PolygonPOSInquirer,
        polygon_pos_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x90128b2988d709e7719dc157aaf08ea76792934cac4e47fa01e93c80d21d30fd')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1716970880000)),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal(gas := '0.00404958204'),
            location_label=polygon_pos_accounts[0],
            notes=f'Burn {gas} POL for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=432,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset(USDC_IDENTIFIER_POLYGON),
            amount=FVal(deposit_amount := '4253.283606'),
            location_label=polygon_pos_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Polygon POS to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=string_to_evm_address('0x10f7835F827D6Cf035115E10c50A853d7FB2D2EC'),
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'from_address': polygon_pos_accounts[0],
                'to_address': polygon_pos_accounts[0],
                'transfer_id': '104742',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x75F3785B330aadbA5DB31535995568583EA8DEA8']])
def test_receive_usdc_on_arbitrum_one_from_polygon(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xad6aa5691bde79c4c97be04871d92e1cc2fa8e43984834716d09001da309dce0')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1716971722000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas := '0.00000345289'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=18,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset(USDC_IDENTIFIER_ARB),
            amount=FVal(deposit_amount := '4253.283606'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Polygon POS to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=ZERO_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'to_address': arbitrum_one_accounts[0],
                'transfer_id': '104742',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xFc99f58A8974A4bc36e60E2d490Bb8D72899ee9f']])
def test_receive_usdc_on_arbitrum_one_from_polygon_2(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xd067d3d8ed104af374b7cf101b8dea72ee4d9cf11a3b18dea9b2de4bb4d1e362')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            sequence_index=1,
            timestamp=TimestampMS(1716978796000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset(USDC_IDENTIFIER_ARB),
            amount=FVal(deposit_amount := '1.541124'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Polygon POS to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=ZERO_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 42161,
                'to_address': arbitrum_one_accounts[0],
                'transfer_id': '104835',
            }},
        ),
    ]
