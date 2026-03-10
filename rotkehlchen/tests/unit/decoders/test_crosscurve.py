from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.crosscurve.constants import CPT_CROSSCURVE
from rotkehlchen.chain.evm.types import (
    EvmIndexer,
    SerializableChainIndexerOrder,
    string_to_evm_address,
)
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChainID,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer

OPTIMISM_INDEXER_ORDER = [{
    'evm_indexers_order': SerializableChainIndexerOrder(
        order={ChainID.OPTIMISM: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN, EvmIndexer.ROUTESCAN]},  # noqa: E501
    ),
}]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', OPTIMISM_INDEXER_ORDER)
@pytest.mark.parametrize('optimism_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_crosscurve_bridge_send(optimism_inquirer: 'OptimismInquirer', optimism_accounts: list[ChecksumEvmAddress]) -> None:  # noqa: E501
    """Data taken from
    https://optimistic.etherscan.io/tx/0xa2f971ba5af848948e0930ab0f86b70751d595e7c79111aa863681a117924e71
    """
    tx_hash = deserialize_evm_tx_hash('0xa2f971ba5af848948e0930ab0f86b70751d595e7c79111aa863681a117924e71')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, gas, fee_amount, bridge_amount = TimestampMS(1757661563000), '0.000000012981416497', '0.000009019739891817', '119.844544'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=(user_address := optimism_accounts[0]),
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=user_address,
            notes=f'Pay {fee_amount} ETH as CrossCurve bridge fee',
            counterparty=CPT_CROSSCURVE,
            address=string_to_evm_address('0xA2A786ff9148f7C88EE93372Db8CBe9e94585c74'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=354,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via CrossCurve',
            counterparty=CPT_CROSSCURVE,
            address=string_to_evm_address('0x0ECD8bfdABd6005c9F325f222E1f6427E4db39e1'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xAc305b47BB34AD6BB566288050920e9307fd23A7']])
def test_crosscurve_bridge_send_arbitrum(arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts: list[ChecksumEvmAddress]) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x03177504cf5ed18c8cc29bc19a08c9f3ffb23d7f66b62ca43cdcba92346d621c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, gas, fee_amount, bridge_amount = TimestampMS(1741867858000), '0.00001096576', '0.000001467792495776', '12.694988'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=(user_address := arbitrum_one_accounts[0]),
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(fee_amount),
            location_label=user_address,
            notes=f'Pay {fee_amount} ETH as CrossCurve bridge fee',
            counterparty=CPT_CROSSCURVE,
            address=string_to_evm_address('0xA2A786ff9148f7C88EE93372Db8CBe9e94585c74'),
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via CrossCurve',
            counterparty=CPT_CROSSCURVE,
            address=string_to_evm_address('0xaB54E380B074E537e2E965BF816d00EcB22F5133'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xAc305b47BB34AD6BB566288050920e9307fd23A7']])
def test_crosscurve_bridge_receive_via_curve(arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts: list[ChecksumEvmAddress]) -> None:  # noqa: E501
    """CrossCurve uses Curve pool liquidity to deliver bridged assets. The resulting event
    would normally be decoded as a Curve withdrawal, but should be re-decoded as a bridge receive.
    """
    tx_hash = deserialize_evm_tx_hash('0x6d7d84478fe237e905ebfa831d2abe107d8cf5b0969cf8eaa5306f992ad85c24')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, receive_amount = TimestampMS(1729787659000), '452.673538'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=49,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
            amount=FVal(receive_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Bridge {receive_amount} USDC.e via CrossCurve',
            counterparty=CPT_CROSSCURVE,
            address=string_to_evm_address('0x7f90122BF0700F9E7e1F688fe926940E8839F353'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_crosscurve_bridge_receive(gnosis_inquirer: 'GnosisInquirer', gnosis_accounts: list[ChecksumEvmAddress]) -> None:  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xd2c1698e07e82e0d0b61c5d22fb2c5f993f21a515322ba890678e772a13d0e08')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, receive_amount = TimestampMS(1757661890000), '101.714686532017583041'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=50,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(receive_amount),
            location_label=(gnosis_accounts[0]),
            notes=f'Bridge {receive_amount} EURe via CrossCurve',
            counterparty=CPT_CROSSCURVE,
            address=string_to_evm_address('0x056C6C5e684CeC248635eD86033378Cc444459B0'),
        ),
    ]
