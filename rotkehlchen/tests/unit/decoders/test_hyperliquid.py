import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.modules.hyperliquid.constants import BRIDGE_ADDRESS, CPT_HYPER
from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import ChecksumEvmAddress, Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x4E60C2E7181EDFc5471C0cBC8D485706d1b35686']])
def test_deposit(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0x2aa0a70af2347ccc4ba3d5f4eddd362c7cd8118c0f2a3617d4b4fcf78c929ea7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1740826458000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount := '0.0000004985'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=7,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(deposited_amount := '500.59'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {deposited_amount} USDC in Hyperliquid',
            address=BRIDGE_ADDRESS,
            counterparty=CPT_HYPER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x9d1c6D4103B5Bcd0da055d968CCF5808178604ca']])
def test_withdrawal(
        arbitrum_one_inquirer: ArbitrumOneInquirer,
        arbitrum_one_accounts: list[ChecksumEvmAddress],
):
    tx_hash = deserialize_evm_tx_hash('0xe57fcce52a6b66fcf1e4435591a43bb65f87141df34756a441a7f816b6f61311')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1740828178000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(amount := '60.49'),
            location_label=arbitrum_one_accounts[0],
            notes=f'Withdraw {amount} USDC from Hyperliquid',
            address=BRIDGE_ADDRESS,
            counterparty=CPT_HYPER,
        ),
    ]
