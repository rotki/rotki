from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.hop.constants import HOP_GOVERNOR
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_ARB,
    A_ETH,
    A_OP,
    A_USDC,
    A_WETH_ARB,
    A_WETH_BASE,
    A_WETH_POLYGON,
    A_XDAI,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_get_unique_cache_value
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    HOP_PROTOCOL_LP,
    CacheType,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.manager import BaseManager
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
    from rotkehlchen.inquirer import Inquirer

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_hop_l2_deposit(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1653219722000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001964214783875487'),
            location_label=ADDY,
            notes='Burn 0.001964214783875487 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.2'),
            location_label=ADDY,
            notes='Bridge 0.2 ETH to Optimism via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f'),
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD8245043a3f339400dcfFFc7A9E6F22a264b933D']])
def test_hop_l2_deposit_usdc(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xac42ca2d88194c0ee219f6c71c98fe566667151a1dc235d17d993b6985342062')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_fee, bridge_amount = TimestampMS(1710955643000), '0.005802319111323689', '3700'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fee),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=363,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            amount=FVal(bridge_amount),
            location_label=ethereum_accounts[0],
            notes=f'Bridge {bridge_amount} USDC to Arbitrum One via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_hop_optimism_eth_receive(optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0x8394c39e1f030a04aa8359f0322257632282a7dfa419b3c9ffc8ab61205a815d
    """
    tx_hash = deserialize_evm_tx_hash('0x8394c39e1f030a04aa8359f0322257632282a7dfa419b3c9ffc8ab61205a815d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1653220466000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.200077923923235647'),
            location_label=ADDY,
            notes='Bridge 0.200077923923235647 ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_hop_optimism_eth_receive_no_event(optimism_inquirer, optimism_accounts):
    """Data taken from
    https://optimistic.etherscan.io/tx/0x3e18e3a0220857ecce91ad79065f10a663128926854b6087161fd0364c7f76f5

    Test that HOP bridge events that have no TRANSFER_FROM_L1_COMPLETED event are decoded.
    """
    tx_hash = deserialize_evm_tx_hash('0x3e18e3a0220857ecce91ad79065f10a663128926854b6087161fd0364c7f76f5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    bridge_amount, timestamp, user_address = '0.03958480553397407', TimestampMS(1666977475000), optimism_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc009D690942DbAaC8d5b15B20EFb24fCbFF77Ddd']])
def test_hop_usdc_bridge(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdca89892d6a738c2ea278d93a5e1757b2f946f4e24c4aa02d59a0abf6a8e5f4b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1715038763000), '9006.683634', ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=167,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_hop_eth_bridge_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4f1e95506c10f061ddfe28a7437f3b651959ff17f1e2a7a148c8896147ee357e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1643122781000), '0.10392672200478311', optimism_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc5DE997A4809c15b64560b04E1141416B1a2A71e']])
def test_hop_eth_bridge_gnosis(gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8765cf6596ff1794679509fcc0ecd5adf921464859f08992944f6d6a7e905d98')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1715179605000), '0.008909890056139906', gnosis_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} WETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x03D7f750777eC48d39D080b020D83Eb2CB4e3547'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x0B8B3648060b97447C023E9EE227BB92E35B30FE']])
def test_hop_usdc_bridge_gnosis(gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd00e4cd1223d962ef841c16977142856c1f54d4e87fae417c58520270e3a9420')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1710961255000), '23.482715', gnosis_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2021,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x76b22b8C1079A44F1211D867D68b1eda76a635A7'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x3b6a814bFbfdae6649Bc3753018e746B8e605342']])
def test_hop_hop_bridge_gnosis(gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x93a644818341e6ac22e499ac1ab73c11b6d8e55ff52ecc529125dc28790d7df1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1697084045000), '6854.931542581763573457', gnosis_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} HOP via Hop protocol',
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x8f7043fF95c088b5727bF7889b4d868DF92F6a58']])
def test_hop_eth_bridge_polygon_pos(polygon_pos_inquirer: 'PolygonPOSInquirer', polygon_pos_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xcb26a59c87d41de4d6dd688a9ff8400b4e981f7e38d25787616ec0f81b4dccca')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, bridge_amount, user_address = TimestampMS(1715182468000), '0.00371160659018274', polygon_pos_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=30,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_WETH_POLYGON,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} WETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xc315239cFb05F1E130E7E28E603CEa4C014c57f0'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xC0b263b8315FAABC27BC0479a5A547281c049C1c']])
def test_hop_eth_bridge_base(base_inquirer: 'BaseInquirer', base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd78eb0f79fa4af1e140641ef260499a6e138b6398d2c4cdcd2e7c488ee8cb20e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, bridge_amount, user_address = TimestampMS(1715184391000), '0.895370313537560075', base_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x10541b07d8Ad2647Dc6cD67abd4c03575dade261'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x32C885EcE06EBC8F6bEf6C2052E400226C087e08']])
def test_hop_eth_bridge_l2_to_l1_arbitrum_one(arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x4fb91812763e6af24465ee014a306b8322beb612aa51f26b657772447744ae94')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1715614190000)
    bridge_amount, gas_fee, hop_fee, user_address = '0.194877831029822766', '0.00000323542', '0.004034870881159123', arbitrum_one_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fee),
            location_label=user_address,
            notes=f'Burn {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH to Ethereum via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(hop_fee),
            location_label=user_address,
            notes=f'Spend {hop_fee} ETH as a hop fee',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x32C885EcE06EBC8F6bEf6C2052E400226C087e08']])
def test_hop_eth_bridge_l2_to_l1_ethereum(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x15704d966705b423b1f747d9413a474f35647e676a5f7ec2bed5ae83bf4f5e38')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1715614211000), '0.194877831029822766', ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0a6c69327d517568E6308F1E1CD2fD2B2b3cd4BF']])
def test_hop_magic_bridge_l2_to_l1_arbitrum_one(arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x05c2c5f18e9acc193f34c611e176d9e65f34d420ba80c7546e0ba0c124d510e3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1715564239000)
    bridge_amount, gas_fee, bridge_fee, user_address = '690.640743549100305130', '0.00000257294', '5.136762511171047454', arbitrum_one_accounts[0]  # noqa: E501
    approval_amount = '115792089237316195423570985008687907853269984665640563953113.341386879395299329'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fee),
            location_label=user_address,
            notes=f'Burn {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x539bdE0d7Dbd336b79148AA742883198BBF60342'),
            amount=FVal(approval_amount),
            location_label=user_address,
            notes=f'Set MAGIC spending approval of {user_address} by 0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=17,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:42161/erc20:0x539bdE0d7Dbd336b79148AA742883198BBF60342'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} MAGIC to Ethereum via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=Asset('eip155:42161/erc20:0x539bdE0d7Dbd336b79148AA742883198BBF60342'),
            amount=FVal(bridge_fee),
            location_label=user_address,
            notes=f'Spend {bridge_fee} MAGIC as a hop fee',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xebe61c49901a46c954e37B8945Bfb87D238F8f45']])
def test_hop_usdc_bridge_l2_to_l1_ethereum(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xc76dbb99825d1e53488426b5cf93f7ff71b5fd1fccd41259537e84824a950cc9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, user_address = TimestampMS(1715208275000), '60786.713495', ethereum_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=182,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xebe61c49901a46c954e37B8945Bfb87D238F8f45']])
def test_hop_usdc_bridge_l2_to_l1_gnosis(gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0c6084399c873b06407f073acec89ffd9693ac0c7df4befd9e45e4178b5ae869')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, bridge_amount, gas_fees, user_address = TimestampMS(1715204760000), '60786.713495', '0.0001299435', gnosis_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_fees),
            location_label=user_address,
            notes=f'Burn {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=462,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0x9ec9551d4A1a1593b0ee8124D98590CC71b3B09D'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Burn {bridge_amount} of Hop hUSDC',
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D', '0xA63734db2c674122EEd383aea7698C68aAbf749e']])  # noqa: E501
def test_hop_eth_bridge_arbitrum_custom_recipient(arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x88b6fce15afacab9fa77caaf8d42d30d7a517f9f5ae6b7d6c37795309ac90383')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, bridge_amount, hop_fee, user_address = TimestampMS(1715946201000), '0.00000266018', '0.000880551717232904', '0.000118862618614123', arbitrum_one_accounts[0]  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH to Base at address {arbitrum_one_accounts[1]} via Hop protocol',  # noqa: E501
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(hop_fee),
            location_label=user_address,
            notes=f'Spend {hop_fee} ETH as a hop fee',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('base_accounts', [['0xAE70bC0Cbe03ceF2a14eCA507a2863441C6Df7A1']])
def test_hop_add_liquidity(
        inquirer: 'Inquirer',
        base_manager: 'BaseManager',
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xa50286f6288ca13452a490d766aaf969d20cce7035b514423a7b1432fd329cc5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, gas, lp_amount, lp_token_amount = TimestampMS(1714582939000), '0.000013783759721971', '0.025', '0.023220146656543904'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=base_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WETH_BASE,
            amount=FVal(lp_amount),
            location_label=base_accounts[0],
            notes=f'Deposit {lp_amount} WETH to Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D'),
            amount=FVal(lp_token_amount),
            location_label=base_accounts[0],
            notes=f'Receive {lp_token_amount} HOP-LP-ETH after providing liquidity in Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
    assert EvmToken('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D').protocol == HOP_PROTOCOL_LP  # noqa: E501
    with GlobalDBHandler().conn.read_ctx() as cursor:
        assert globaldb_get_unique_cache_value(
            cursor=cursor,
            key_parts=(
                CacheType.HOP_POOL_ADDRESS,
                '8453',
                '0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D',
            ),
        ) == '0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'

    inquirer.inject_evm_managers([(base_inquirer.chain_id, base_manager)])
    assert inquirer.find_usd_price(Asset('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D')).is_close(2047.7888340254)  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_hop_add_liquidity_2(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x52ab27e8f15148c0f41df0114429321d2a1e9411f2ea2fe7c8fb9c663bc09ecb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, lp_amount, lp_amount_2, lp_token_amount, approval_amount_1, approval_amount_2 = TimestampMS(1716391406000), '0.00000298668', '0.001', '0.005129453530970625', '0.005676129314105837', '115792089237316195423570985008687907853269984665640564039457.583007913129639935', '115792089237316195423570985008687907853269984665640564039457.57887845959866931'  # noqa: E501
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
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_WETH_ARB,
            amount=FVal(approval_amount_1),
            location_label=arbitrum_one_accounts[0],
            notes=f'Set WETH spending approval of {arbitrum_one_accounts[0]} by 0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97 to {approval_amount_1}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97'),
        ), EvmEvent(
            sequence_index=7,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xDa7c0de432a9346bB6e96aC74e3B61A36d8a77eB'),
            amount=FVal(approval_amount_2),
            location_label=arbitrum_one_accounts[0],
            notes=f'Set hETH spending approval of {arbitrum_one_accounts[0]} by 0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97 to {approval_amount_2}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97'),
        ), EvmEvent(
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_WETH_ARB,
            amount=FVal(lp_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {lp_amount} WETH to Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97'),
        ), EvmEvent(
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xDa7c0de432a9346bB6e96aC74e3B61A36d8a77eB'),
            amount=FVal(lp_amount_2),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {lp_amount_2} hETH to Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97'),
        ), EvmEvent(
            sequence_index=10,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a'),
            amount=FVal(lp_token_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {lp_token_amount} HOP-LP-ETH after providing liquidity in Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xA38b8E0cA73916fD611Bbf9E854FDBB25865e42a']])
def test_hop_remove_liquidity(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xc3662d3d68f845dd848c9df2aef4efedf9c9a01580872619a2f4eaafdbf98feb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, gas, lp_amount, withdrawn = TimestampMS(1714729295000), '0.000019101983974486', '0.75', '0.807405509354959205'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=base_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=35,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D'),
            amount=ZERO,
            location_label=base_accounts[0],
            notes=f'Revoke HOP-LP-ETH spending approval of {base_accounts[0]} by 0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
        ), EvmEvent(
            sequence_index=36,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D'),
            amount=FVal(lp_amount),
            location_label=base_accounts[0],
            notes=f'Return {lp_amount} HOP-LP-ETH',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            sequence_index=37,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WETH_BASE,
            amount=FVal(withdrawn),
            location_label=base_accounts[0],
            notes=f'Withdraw {withdrawn} WETH from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x8Df3480a31B5a32508Cd1E29A6Ff84fd03b96430']])
def test_hop_remove_liquidity_2(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x4995c8896bb845ab506b759530d35e306d6ef5418630b60bbf26ca0fae90fcaa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, gas, lp_amount, withdrawn_1, withdrawn_2 = TimestampMS(1716298905000), '0.000020283535960823', '0.014812373943526529', '0.008484007194088721', '0.007520340659511852'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=base_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=174,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D'),
            amount=ZERO,
            location_label=base_accounts[0],
            notes=f'Revoke HOP-LP-ETH spending approval of {base_accounts[0]} by 0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
        ), EvmEvent(
            sequence_index=175,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xe9605BEc1c5C3E81F974F80b8dA9fBEFF4845d4D'),
            amount=FVal(lp_amount),
            location_label=base_accounts[0],
            notes=f'Return {lp_amount} HOP-LP-ETH',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            sequence_index=176,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_WETH_BASE,
            amount=FVal(withdrawn_1),
            location_label=base_accounts[0],
            notes=f'Withdraw {withdrawn_1} WETH from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
        ), EvmEvent(
            sequence_index=177,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:8453/erc20:0xC1985d7a3429cDC85E59E2E4Fcc805b857e6Ee2E'),
            amount=FVal(withdrawn_2),
            location_label=base_accounts[0],
            notes=f'Withdraw {withdrawn_2} hETH from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x0ce6c85cF43553DE10FC56cecA0aef6Ff0DD444d'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xCe0945D35cCc4ccA674e13D3cc2918843C4B56d6']])
def test_hop_remove_liquidity_usdc_gnosis(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x5833d34d7f20ee4e71b902dac85a025f40739a1d646091553104a3e345a38f81')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, gas, lp_amount, withdrawn, withdrawn_2, approval_amount = TimestampMS(1716258450000), '0.000645488318952488', '2.138240168467212015', '0.258527', '2.026586', '0.861759831532787985'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=85,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:100/erc20:0x9D373d22FD091d7f9A6649EB067557cc12Fb1A0A'),
            amount=FVal(approval_amount),
            location_label=gnosis_accounts[0],
            notes=f'Set HOP-LP-USDC spending approval of {gnosis_accounts[0]} by 0x5C32143C8B198F392d01f8446b754c181224ac26 to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x5C32143C8B198F392d01f8446b754c181224ac26'),
        ), EvmEvent(
            sequence_index=86,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:100/erc20:0x9D373d22FD091d7f9A6649EB067557cc12Fb1A0A'),
            amount=FVal(lp_amount),
            location_label=gnosis_accounts[0],
            notes=f'Return {lp_amount} HOP-LP-USDC',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            sequence_index=87,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(withdrawn),
            location_label=gnosis_accounts[0],
            notes=f'Withdraw {withdrawn} USDC from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x5C32143C8B198F392d01f8446b754c181224ac26'),
        ), EvmEvent(
            sequence_index=88,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:100/erc20:0x9ec9551d4A1a1593b0ee8124D98590CC71b3B09D'),
            amount=FVal(withdrawn_2),
            location_label=gnosis_accounts[0],
            notes=f'Withdraw {withdrawn_2} hUSDC from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x5C32143C8B198F392d01f8446b754c181224ac26'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_current_price_queries', [False])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_hop_stake(
        inquirer: 'Inquirer',
        arbitrum_one_manager: 'ArbitrumOneManager',
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x6329984b82cb85903fee9fef61fb77cdf848ff6344056156da2e66676ad91473')  # noqa: E501
    get_decoded_events_of_transaction(  # decode the deposit tx to process the LP token
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=deserialize_evm_tx_hash('0x52ab27e8f15148c0f41df0114429321d2a1e9411f2ea2fe7c8fb9c663bc09ecb'),
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, stake_amount, approval_amount = TimestampMS(1716391575000), '0.00000183398', '0.005676129314105837', '115792089237316195423570985008687907853269984665640564039457.578331783815534098'  # noqa: E501
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
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a'),
            amount=FVal(stake_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Stake {stake_amount} HOP-LP-ETH in Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            product=EvmProduct.STAKING,
            address=string_to_evm_address('0x755569159598f3702bdD7DFF6233A317C156d3Dd'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a'),
            amount=FVal(approval_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Set HOP-LP-ETH spending approval of {arbitrum_one_accounts[0]} by 0x755569159598f3702bdD7DFF6233A317C156d3Dd to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x755569159598f3702bdD7DFF6233A317C156d3Dd'),
        ),
    ]
    assert events == expected_events
    inquirer.inject_evm_managers([(arbitrum_one_inquirer.chain_id, arbitrum_one_manager)])
    assert inquirer.find_usd_price(Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a')).is_close(1995.56814825)  # noqa: E501


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_hop_stake_2(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xe0c1f6f152422784a4e4346d84af7d32fda95eab17da257f3fdc5121f4a6fbc8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, stake_amount, approval_amount = TimestampMS(1718269403000), '0.00000199918', '0.005676129314105837', '115792089237316195423570985008687907853269984665640564039457.578331783815534098'  # noqa: E501
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
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=43,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a'),
            amount=FVal(stake_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Stake {stake_amount} HOP-LP-ETH in Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            product=EvmProduct.STAKING,
            address=string_to_evm_address('0x00001fcF29c5Fd7846E4332AfBFaA48701D727f5'),
        ), EvmEvent(
            sequence_index=44,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a'),
            amount=FVal(approval_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Set HOP-LP-ETH spending approval of {arbitrum_one_accounts[0]} by 0x00001fcF29c5Fd7846E4332AfBFaA48701D727f5 to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x00001fcF29c5Fd7846E4332AfBFaA48701D727f5'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x73F809c0B3cF18d40463D05Ba4b95067cb51393B']])
def test_hop_claim_rewards(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x905c1f8cf4b94d49b18f14fc7c403df653f731999ef5262b6aa92dbe5ad0423f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, reward_amount = TimestampMS(1716445828000), '0.00000098192', '1.556162863261353191'  # noqa: E501
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
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=13,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC'),
            amount=FVal(reward_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Claim {reward_amount} HOP from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x755569159598f3702bdD7DFF6233A317C156d3Dd'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xA252bd92293B0eb9BEB1C2cF72F794F8a3a54348']])
def test_hop_claim_rewards_2(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x85b7ca62b27f78f59bcb9fd52ab18c05f3f143ff4df00c70d4f9a3edfa5eea19')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, reward_amount = TimestampMS(1718278937000), '0.00000171746', '1.305947476028639625'  # noqa: E501
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
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_ARB,
            amount=FVal(reward_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Claim {reward_amount} ARB from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x00001fcF29c5Fd7846E4332AfBFaA48701D727f5'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xCA16fAf47686aCFEbD6CFC74419fcC9Cbf833067']])
def test_hop_claim_merkle_rewards(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x7f8114d30702cd540154b01a666ef6a7cf4dab8c4d657efa9e0503413243d2f3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, reward_amount = TimestampMS(1747908883000), '0.000000228471368276', '0.18'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=15,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_OP,
            amount=FVal(reward_amount),
            location_label=optimism_accounts[0],
            notes=f'Claim {reward_amount} OP from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x45269F59aA76bB491D0Fc4c26F468D8E1EE26b73'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x73F809c0B3cF18d40463D05Ba4b95067cb51393B']])
def test_hop_unstake(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x4bdf31c7bbe27ccbb9a5d381596b6f4d8cf9583d111af43d5b0b5d76bb8f6751')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, unstake_amount, reward_amount = TimestampMS(1716446062000), '0.00000160545', '0.000958469117996842', '0.000025838435799823'  # noqa: E501
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
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:42161/erc20:0x59745774Ed5EfF903e615F5A2282Cae03484985a'),
            amount=FVal(unstake_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Unstake {unstake_amount} HOP-LP-ETH from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x755569159598f3702bdD7DFF6233A317C156d3Dd'),
        ), EvmEvent(
            sequence_index=13,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:42161/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC'),
            amount=FVal(reward_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Claim {reward_amount} HOP from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x755569159598f3702bdD7DFF6233A317C156d3Dd'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x5d58727c200E96347235a907d9b856A1B0089D86']])
def test_hop_stake_gnosis(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xf3b00cb365594bf9b2894af0edf852d04411db49b5fe9c07708186f75bce5385')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, gas, stake_amount, approval_amount = TimestampMS(1710600070000), '0.00017891077758659', '1.927208027730675426', '115792089237316195423570985008687907853269984665640564039453.729591857668289083'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas} XDAI for gas',
            tx_hash=tx_hash,
            counterparty='gas',
        ), EvmEvent(
            sequence_index=2001,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:100/erc20:0x5b10222f2Ada260AAf6C6fC274bd5810AF9d33c0'),
            amount=FVal(stake_amount),
            location_label=gnosis_accounts[0],
            notes=f'Stake {stake_amount} HOP-LP-USDT in Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            product=EvmProduct.STAKING,
            address=string_to_evm_address('0x2C2Ab81Cf235e86374468b387e241DF22459A265'),
        ), EvmEvent(
            sequence_index=2002,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:100/erc20:0x5b10222f2Ada260AAf6C6fC274bd5810AF9d33c0'),
            amount=FVal(approval_amount),
            location_label=gnosis_accounts[0],
            notes=f'Set HOP-LP-USDT spending approval of {gnosis_accounts[0]} by 0x2C2Ab81Cf235e86374468b387e241DF22459A265 to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x2C2Ab81Cf235e86374468b387e241DF22459A265'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x5d58727c200E96347235a907d9b856A1B0089D86']])
def test_hop_claim_rewards_gnosis(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x5ad3d5050d43ec08883c76116d9328b6bf61dd8478c082bfe21bd97eb237c4b1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, gas, reward_amount = TimestampMS(1710597650000), '0.000149113056096078', '0.001269493516433091'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=2500,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            amount=FVal(reward_amount),
            location_label=gnosis_accounts[0],
            notes=f'Claim {reward_amount} GNO from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x2C2Ab81Cf235e86374468b387e241DF22459A265'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x95e62E8FF84ed8456fDc9739eE4A9597Bb6E4c1f']])
def test_hop_unstake_gnosis(
        gnosis_inquirer: 'GnosisInquirer',
        gnosis_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x10e32923be7fd7beda4551badb4fb3ca1a708268884e540d92c73b88596f3ac4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp, gas, unstake_amount, reward_amount = TimestampMS(1708463325000), '0.000669895628651568', '30000', '0.91583970339645'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas),
            location_label=gnosis_accounts[0],
            notes=f'Burn {gas} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=3003,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:100/erc20:0x5b10222f2Ada260AAf6C6fC274bd5810AF9d33c0'),
            amount=FVal(unstake_amount),
            location_label=gnosis_accounts[0],
            notes=f'Unstake {unstake_amount} HOP-LP-USDT from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x2C2Ab81Cf235e86374468b387e241DF22459A265'),
        ), EvmEvent(
            sequence_index=3005,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            amount=FVal(reward_amount),
            location_label=gnosis_accounts[0],
            notes=f'Claim {reward_amount} GNO from Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x2C2Ab81Cf235e86374468b387e241DF22459A265'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_vote_cast(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xc6116ef064b0a713eb50cb55a1e76ef947ebdba9cbfba9a71498dacb6b75ba0e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas = TimestampMS(1671494483000), '0.00186503943913884'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ADDY,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=307,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ADDY,
            notes='Vote FOR hop governance proposal https://www.tally.xyz/gov/hop/proposal/114834095316819367752457382978722571068850159829764853513197263236546715801279',
            counterparty=CPT_HOP,
            address=HOP_GOVERNOR,
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_hop_add_liquidity_optimism_usdc(
        optimism_inquirer: 'BaseInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x891d2b68a1ecc36b1c14943ddaece1ee50d0d895ca20b9ad61640aa531b8755e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, gas, lp_amount, lp_token_amount, approval_amount = TimestampMS(1670628821000), '0.00006011384375604', '11208.995146', '10843.63570237678072025', '115792089237316195423570985008687907853269984665640564039457584007901920.644789'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(approval_amount),
            location_label=optimism_accounts[0],
            notes=f'Set USDC.e spending approval of {optimism_accounts[0]} by 0x3c0FFAca566fCcfD9Cc95139FEF6CBA143795963 to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x3c0FFAca566fCcfD9Cc95139FEF6CBA143795963'),
        ), EvmEvent(
            sequence_index=3,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(lp_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {lp_amount} USDC.e to Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3c0FFAca566fCcfD9Cc95139FEF6CBA143795963'),
        ), EvmEvent(
            sequence_index=4,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:10/erc20:0x2e17b8193566345a2Dd467183526dEdc42d2d5A8'),
            amount=FVal(lp_token_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {lp_token_amount} HOP-LP-USDC after providing liquidity in Hop',
            tx_hash=tx_hash,
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events
