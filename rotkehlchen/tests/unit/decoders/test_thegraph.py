import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING, CPT_THEGRAPH
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_GRT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY_USER = string_to_evm_address('0xd200aeEC7Cd9dD27CAB5a85083953a734D4e84f0')
ADDY_THEGRAPH = string_to_evm_address(CONTRACT_STAKING)


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER]])
def test_thegraph_delegate(database, ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x6ed3377db652151fb8e4794dd994a921a2d029ad317bd3f2a2916af239490fec')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1690731467000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.002150596408306665')),
            location_label=ADDY_USER,
            notes='Burned 0.002150596408306665 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=358,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GRT,
            balance=Balance(amount=FVal('1.157920892373161954235709850E+59')),
            location_label=ADDY_USER,
            notes=(
                f'Set GRT spending approval of {ADDY_USER} by {ADDY_THEGRAPH}'
                f' to 115792089237316195423570985000000000000000000000000000000000'
            ),
            counterparty=None,
            address=ADDY_THEGRAPH,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=359,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GRT,
            balance=Balance(amount=FVal('998.98')),
            location_label=ADDY_USER,
            notes='Delegate 998.98 GRT to indexer 0x6125eA331851367716beE301ECDe7F38A7E429e7',
            counterparty=CPT_THEGRAPH,
            address=ADDY_THEGRAPH,
            extra_data={'indexer': '0x6125eA331851367716beE301ECDe7F38A7E429e7'},
            product=EvmProduct.STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=360,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_GRT,
            balance=Balance(amount=FVal('5.02')),
            location_label=ADDY_USER,
            notes='Burn 5.02 GRT as delegation tax',
            counterparty=CPT_THEGRAPH,
            address=ADDY_THEGRAPH,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER]])
def test_thegraph_undelegate(database, ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x5ca5244868d9c0d8c30a1cad0feaf137bd28acd9c3f669a09a3a199fd75ad25a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1691771855000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00307607001551556')),
            location_label=ADDY_USER,
            notes='Burned 0.00307607001551556 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=297,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GRT,
            balance=Balance(),
            location_label=ADDY_USER,
            notes=(
                'Undelegate 1003.70342593701668535 GRT from'
                ' indexer 0x6125eA331851367716beE301ECDe7F38A7E429e7. Lock expires in 983 seconds'
            ),
            counterparty=CPT_THEGRAPH,
            address=ADDY_THEGRAPH,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER]])
def test_thegraph_delegated_withdrawn(database, ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x49307751de5ba4cf98fccbdd1ab8387fd60a7ce120800212c216bf0a6a04acfa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1694577371000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.000651667321615926')),
            location_label=ADDY_USER,
            notes='Burned 0.000651667321615926 ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=208,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GRT,
            balance=Balance(amount=FVal('1003.70342593701668535')),
            location_label=ADDY_USER,
            notes=(
                'Withdraw 1003.70342593701668535 GRT'
                ' from indexer 0x6125eA331851367716beE301ECDe7F38A7E429e7'
            ),
            counterparty=CPT_THEGRAPH,
            address=ADDY_THEGRAPH,
        ),
    ]
    assert expected_events == events
