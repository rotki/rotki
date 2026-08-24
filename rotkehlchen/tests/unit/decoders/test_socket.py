import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import CPT_SOCKET, GATEWAY_ADDRESS
from rotkehlchen.constants.assets import A_ETH, A_POL
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('optimism_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_optimism_to_arb_bridge(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe8c9cffe2a2bbccf81cf8dd34f9b89c01b00ae3f0ff74eab089de96f4624165c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address = optimism_accounts[0]
    bridged_amount, gas_amount = '360.791433', '0.000035854553456552'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1705844449000)),
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:10/erc20:0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),
            amount=FVal(bridged_amount),
            location_label=user_address,
            notes=f'Bridge {bridged_amount} USDC to {user_address} at Arbitrum One using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 10,
                'to_chain': 42161,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': '35259',
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('scroll_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_scroll_to_arbitrum_across_bridge(scroll_inquirer, scroll_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xee8b1b99f88ab4d9924c4aec444e45ab53589b918a2cf54e9bc133481c7dbbb9',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=scroll_inquirer, tx_hash=tx_hash)
    user_address = scroll_accounts[0]
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1739477339000)),
            location=Location.SCROLL,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00000785918'),
            location_label=user_address,
            notes='Burn 0.00000785918 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.SCROLL,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:534352/erc20:0x06eFdBFf2a14a7c8E15944D1F4A48F9F95F663A4'),
            amount=FVal('365.729555'),
            location_label=user_address,
            notes=f'Bridge 365.729555 USDC to {user_address} at Arbitrum One using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 534352,
                'to_chain': 42161,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': '1295289',
            }},
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_bridge_eth(arbitrum_one_inquirer, arbitrum_one_accounts):
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xb1e29bebca0300ff02ee478dfa6c0c2197169761e1c0dcc87418c53a6530d3a5')),  # noqa: E501
    )
    user_address = arbitrum_one_accounts[0]
    bridged_amount, gas_amount = '0.01', '0.0000464928'
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1696328657000)),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridged_amount),
            location_label=user_address,
            notes=f'Bridge {bridged_amount} ETH to {user_address} at Base using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 8453,
                'from_address': user_address,
                'to_address': user_address,
            }},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_polygon_to_gnosis_bridge(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0xafaf61e1f897f394780d069627d1ac1e5f68ad31a00ed72533ce4c709d381a44',
    )
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    user_address = polygon_pos_accounts[0]
    source_asset = Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174')
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1708712296000)),
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POL,
            amount=FVal('0.087685584'),
            location_label=user_address,
            notes='Burn 0.087685584 POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=75,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=source_asset,
            amount=FVal('713.947477'),
            location_label=user_address,
            notes=f'Bridge 713.947477 USDC to {user_address} at Gnosis using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 137,
                'to_chain': 100,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': '0x19c1beb9da864f19672879bc093297c19ead364769f28633fd18aaf12e9d95f2',  # noqa: E501
            }},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=76,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=source_asset,
            amount=FVal('0'),
            location_label=user_address,
            notes=f'Revoke USDC spending approval of {user_address} by {GATEWAY_ADDRESS}',
            address=GATEWAY_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_base_to_gnosis_hop_bridge(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash(
        '0x3e88cd749ab657299b10a6f079b2b63380edb5f2f700c421c3f1c77f7a3b7949',
    )
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address = base_accounts[0]
    source_asset = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1703766791000)),
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000411690516301503'),
            location_label=user_address,
            notes='Burn 0.000411690516301503 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=47,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=source_asset,
            amount=FVal('399.365908'),
            location_label=user_address,
            notes=f'Bridge 399.365908 USDC to {user_address} at Gnosis using Socket',
            counterparty=CPT_SOCKET,
            address=GATEWAY_ADDRESS,
            extra_data={'bridge': {
                'from_chain': 8453,
                'to_chain': 100,
                'from_address': user_address,
                'to_address': user_address,
                'transfer_id': '0x515a483a21beb5543dc74f6dbcb2bcfbb190cc01e10f2209fd195c47b24a0275',  # noqa: E501
            }},
        ),
    ]
