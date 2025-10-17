from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.cctp.constants import USDC_IDENTIFIER_ARB
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.cctp.constants import CPT_CCTP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.polygon_pos.modules.cctp.constants import USDC_IDENTIFIER_POLYGON
from rotkehlchen.constants.assets import A_ETH, A_POLYGON_POS_MATIC, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd0Adc5d079Cc486b58F1B9A28B973355C4ec9e6f']])
def test_deposit_usdc_from_ethereum_to_arbitrum_one(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xac7bb45701a4311a2c662377a4764ac694a8f6438270c1ee8a4100d4a000a511')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, deposit_amount = TimestampMS(1716588659000), '0.000649402467435812', '1839.726596'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
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
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Ethereum to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=string_to_evm_address('0xc4922d64a24675E16e1586e3e3Aa56C06fABe907'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xd0Adc5d079Cc486b58F1B9A28B973355C4ec9e6f']])
def test_receive_usdc_on_arbitrum_one_from_ethereum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0x9da8beb8e9ad2428ad2de132d920d27c2d6c7e0604d2977669aab219e51fd323')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, deposit_amount = TimestampMS(1716589968000), '0.00000196702', '1839.726596'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
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
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Ethereum to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x75F3785B330aadbA5DB31535995568583EA8DEA8']])
def test_deposit_usdc_from_polygon_to_arbitrum_one(
        polygon_pos_inquirer: 'PolygonPOSInquirer',
        polygon_pos_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0x90128b2988d709e7719dc157aaf08ea76792934cac4e47fa01e93c80d21d30fd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, deposit_amount = TimestampMS(1716970880000), '0.00404958204', '4253.283606'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas),
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
            amount=FVal(deposit_amount),
            location_label=polygon_pos_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Polygon POS to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=string_to_evm_address('0x10f7835F827D6Cf035115E10c50A853d7FB2D2EC'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x75F3785B330aadbA5DB31535995568583EA8DEA8']])
def test_receive_usdc_on_arbitrum_one_from_polygon(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xad6aa5691bde79c4c97be04871d92e1cc2fa8e43984834716d09001da309dce0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, deposit_amount = TimestampMS(1716971722000), '0.00000345289', '4253.283606'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
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
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Polygon POS to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xFc99f58A8974A4bc36e60E2d490Bb8D72899ee9f']])
def test_receive_usdc_on_arbitrum_one_from_polygon_2(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xd067d3d8ed104af374b7cf101b8dea72ee4d9cf11a3b18dea9b2de4bb4d1e362')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, deposit_amount = TimestampMS(1716978796000), '1.541124'
    expected_events = [
        EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset(USDC_IDENTIFIER_ARB),
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {deposit_amount} USDC from Polygon POS to Arbitrum One via CCTP',
            tx_ref=tx_hash,
            counterparty=CPT_CCTP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
