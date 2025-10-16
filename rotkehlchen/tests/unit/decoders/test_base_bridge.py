import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.constants import CPT_BASE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xc91FC9Dd7f1Bb6Ec429edDB577b9Ace6236B2147']])
def test_deposit_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xbd58a2802a40659da35ff838017a00ba0e251dd0c96ae0c802bd41b5a999f366')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1693477115000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0008732662'),
            location_label=user_address,
            notes='Burn 0.0008732662 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1693477115000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('200'),
            location_label=user_address,
            notes='Bridge 200 ETH from Ethereum to Base via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x49048044D57e1C92A77f79988d21Fa8fAF74E97e'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xC8f9850e4862b62cCA7f87A81633c2Add9488743']])
def test_withdraw_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6f62277e5fe0c7d8c613b66b6850dd4b6cf193f830b52486d7d9b79917441e46')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1693477571000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0011436799352069'),
            location_label=user_address,
            notes='Burn 0.0011436799352069 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=TimestampMS(1693477571000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.003'),
            location_label=user_address,
            notes='Bridge 0.003 ETH from Base to Ethereum via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x49048044D57e1C92A77f79988d21Fa8fAF74E97e'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xbAbE777e1a43053C273bd8A4e45D0cB6c20f8Fc6']])
def test_deposit_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9593200706ea6941eac1c8189b9648e9ebab5bd14504c4a493f5309f85e6cba6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1693480187000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00227258431919723'),
            location_label=user_address,
            notes='Burn 0.00227258431919723 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=476,
            timestamp=TimestampMS(1693480187000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),
            amount=FVal('104.9426'),
            location_label=user_address,
            notes='Bridge 104.9426 cbETH from Ethereum to Base via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x3154Cf16ccdb4C6d922629664174b904d80F2C35'),
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x0050F3427E5388E9cc458e977bC3444faf015618']])
def test_withdraw_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2d047f0b7a0f2052791359ef82eab317b6d6a685a3c24614f51e8775f4b60ef4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=TimestampMS(1693479923000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002955477492625515'),
            location_label=user_address,
            notes='Burn 0.002955477492625515 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=196,
            timestamp=TimestampMS(1693479923000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:1/erc20:0xBe9895146f7AF43049ca1c1AE358B0541Ea49704'),
            amount=FVal('189.09'),
            location_label=user_address,
            notes='Bridge 189.09 cbETH from Base to Ethereum via Base bridge',
            counterparty=CPT_BASE,
            address=string_to_evm_address('0x3154Cf16ccdb4C6d922629664174b904d80F2C35'),
        ),
    ]
