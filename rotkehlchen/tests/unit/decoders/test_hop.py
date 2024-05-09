from typing import TYPE_CHECKING

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_WETH_POLYGON, A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
    from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_hop_l2_deposit(database, ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee
    """
    tx_hash = deserialize_evm_tx_hash('0xd46640417a686b399b2f2a920b0c58a35095759365cbe7b795bddec34b8c5eee')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal('0.001964214783875487')),
            location_label=ADDY,
            notes='Burned 0.001964214783875487 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.2')),
            location_label=ADDY,
            notes='Bridge 0.2 ETH to Optimism via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f'),
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xD8245043a3f339400dcfFFc7A9E6F22a264b933D']])
def test_hop_l2_deposit_usdc(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xac42ca2d88194c0ee219f6c71c98fe566667151a1dc235d17d993b6985342062')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(gas_fee)),
            location_label=ethereum_accounts[0],
            notes=f'Burned {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=363,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDC,
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=ethereum_accounts[0],
            notes=f'Bridge {bridge_amount} USDC to Arbitrum One via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'),
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_hop_optimism_eth_receive(database, optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0x8394c39e1f030a04aa8359f0322257632282a7dfa419b3c9ffc8ab61205a815d
    """
    tx_hash = deserialize_evm_tx_hash('0x8394c39e1f030a04aa8359f0322257632282a7dfa419b3c9ffc8ab61205a815d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1653220466000),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.200077923923235647')),
            location_label=ADDY,
            notes='Bridge 0.200077923923235647 ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x4bBa290826C253BD854121346c370a9886d1bC26']])
def test_hop_optimism_eth_receive_no_event(database, optimism_inquirer, optimism_accounts):
    """Data taken from
    https://optimistic.etherscan.io/tx/0x3e18e3a0220857ecce91ad79065f10a663128926854b6087161fd0364c7f76f5

    Test that HOP bridge events that have no TRANSFER_FROM_L1_COMPLETED event are decoded.
    """
    tx_hash = deserialize_evm_tx_hash('0x3e18e3a0220857ecce91ad79065f10a663128926854b6087161fd0364c7f76f5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xc009D690942DbAaC8d5b15B20EFb24fCbFF77Ddd']])
def test_hop_usdc_bridge(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xdca89892d6a738c2ea278d93a5e1757b2f946f4e24c4aa02d59a0abf6a8e5f4b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_hop_eth_bridge_optimism(database, optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4f1e95506c10f061ddfe28a7437f3b651959ff17f1e2a7a148c8896147ee357e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc5DE997A4809c15b64560b04E1141416B1a2A71e']])
def test_hop_eth_bridge_gnosis(database, gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8765cf6596ff1794679509fcc0ecd5adf921464859f08992944f6d6a7e905d98')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} WETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x03D7f750777eC48d39D080b020D83Eb2CB4e3547'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x0B8B3648060b97447C023E9EE227BB92E35B30FE']])
def test_hop_usdc_bridge_gnosis(database, gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd00e4cd1223d962ef841c16977142856c1f54d4e87fae417c58520270e3a9420')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x76b22b8C1079A44F1211D867D68b1eda76a635A7'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x3b6a814bFbfdae6649Bc3753018e746B8e605342']])
def test_hop_hop_bridge_gnosis(database, gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x93a644818341e6ac22e499ac1ab73c11b6d8e55ff52ecc529125dc28790d7df1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} HOP via Hop protocol',
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x8f7043fF95c088b5727bF7889b4d868DF92F6a58']])
def test_hop_eth_bridge_polygon_pos(database, polygon_pos_inquirer: 'PolygonPOSInquirer', polygon_pos_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xcb26a59c87d41de4d6dd688a9ff8400b4e981f7e38d25787616ec0f81b4dccca')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} WETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xc315239cFb05F1E130E7E28E603CEa4C014c57f0'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xC0b263b8315FAABC27BC0479a5A547281c049C1c']])
def test_hop_eth_bridge_base(database, base_inquirer: 'BaseInquirer', base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd78eb0f79fa4af1e140641ef260499a6e138b6398d2c4cdcd2e7c488ee8cb20e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        database=database,
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x10541b07d8Ad2647Dc6cD67abd4c03575dade261'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x32C885EcE06EBC8F6bEf6C2052E400226C087e08']])
def test_hop_eth_bridge_l2_to_l1_arbitrum_one(database, arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x4fb91812763e6af24465ee014a306b8322beb612aa51f26b657772447744ae94')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
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
            balance=Balance(amount=FVal(gas_fee)),
            location_label=user_address,
            notes=f'Burned {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal(bridge_amount)),
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
            balance=Balance(amount=FVal(hop_fee)),
            location_label=user_address,
            notes=f'Spend {hop_fee} ETH as a hop fee',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x32C885EcE06EBC8F6bEf6C2052E400226C087e08']])
def test_hop_eth_bridge_l2_to_l1_ethereum(database, ethereum_inquirer: 'EthereumInquirer', ethereum_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x15704d966705b423b1f747d9413a474f35647e676a5f7ec2bed5ae83bf4f5e38')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} ETH via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0a6c69327d517568E6308F1E1CD2fD2B2b3cd4BF']])
def test_hop_magic_bridge_l2_to_l1_arbitrum_one(database, arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x05c2c5f18e9acc193f34c611e176d9e65f34d420ba80c7546e0ba0c124d510e3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
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
            balance=Balance(amount=FVal(gas_fee)),
            location_label=user_address,
            notes=f'Burned {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=16,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x539bdE0d7Dbd336b79148AA742883198BBF60342'),
            balance=Balance(amount=FVal(approval_amount)),
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
            balance=Balance(amount=FVal(bridge_amount)),
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
            balance=Balance(amount=FVal(bridge_fee)),
            location_label=user_address,
            notes=f'Spend {bridge_fee} MAGIC as a hop fee',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xebe61c49901a46c954e37B8945Bfb87D238F8f45']])
def test_hop_usdc_bridge_l2_to_l1_ethereum(database, ethereum_inquirer: 'EthereumInquirer', ethereum_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xc76dbb99825d1e53488426b5cf93f7ff71b5fd1fccd41259537e84824a950cc9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC via Hop protocol',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xebe61c49901a46c954e37B8945Bfb87D238F8f45']])
def test_hop_usdc_bridge_l2_to_l1_gnosis(database, gnosis_inquirer: 'GnosisInquirer', gnosis_accounts):  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x0c6084399c873b06407f073acec89ffd9693ac0c7df4befd9e45e4178b5ae869')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(gas_fees)),
            location_label=user_address,
            notes=f'Burned {gas_fees} XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=462,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0x9ec9551d4A1a1593b0ee8124D98590CC71b3B09D'),
            balance=Balance(amount=FVal(bridge_amount)),
            location_label=user_address,
            notes=f'Burn {bridge_amount} of Hop hUSDC',
            counterparty=CPT_HOP,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D', '0xA63734db2c674122EEd383aea7698C68aAbf749e']])  # noqa: E501
def test_hop_eth_bridge_arbitrum_custom_recipient(
        database, arbitrum_one_inquirer: 'ArbitrumOneInquirer', arbitrum_one_accounts,
):
    tx_hash = deserialize_evm_tx_hash('0x88b6fce15afacab9fa77caaf8d42d30d7a517f9f5ae6b7d6c37795309ac90383')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
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
            balance=Balance(amount=FVal(gas)),
            location_label=user_address,
            notes=f'Burned {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            balance=Balance(amount=FVal(bridge_amount)),
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
            balance=Balance(amount=FVal(hop_fee)),
            location_label=user_address,
            notes=f'Spend {hop_fee} ETH as a hop fee',
            counterparty=CPT_HOP,
            address=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        ),
    ]
    assert events == expected_events
