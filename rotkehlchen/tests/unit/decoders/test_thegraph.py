import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.arbitrum_one.modules.thegraph.constants import (
    CONTRACT_STAKING as CONTRACT_STAKING_ARB,
)
from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_GRT, A_GRT_ARB
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY_USER = string_to_evm_address('0xd200aeEC7Cd9dD27CAB5a85083953a734D4e84f0')
ADDY_USER_1_ARB = string_to_evm_address('0xA9728D95567410555557a54EcA320e5E8bEa36a5')
ADDY_USER_2_ARB = string_to_evm_address('0xec9342111098f8b4A293cD8033746d6f8E9e9e7F')
ADDY_USER_3_ARB = string_to_evm_address('0xBe79986821637afD1406BF9278DA55cf9085cF8f')


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
    delegate_amount, delegate_tax, gas_fees = '998.98', '5.02', '0.002150596408306665'
    approval_amount = '115792089237316195423570985008687907853269984665640563952473.318503163402575923'  # noqa: E501
    indexer_address = string_to_evm_address('0x6125eA331851367716beE301ECDe7F38A7E429e7')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ADDY_USER,
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=358,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GRT,
            balance=Balance(amount=FVal(approval_amount)),
            location_label=ADDY_USER,
            notes=f'Set GRT spending approval of {ADDY_USER} by {CONTRACT_STAKING} to {approval_amount}',  # noqa: E501
            counterparty=None,
            address=CONTRACT_STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=359,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GRT,
            balance=Balance(amount=FVal(delegate_amount)),
            location_label=ADDY_USER,
            notes=f'Delegate {delegate_amount} GRT to indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
            extra_data={'indexer': indexer_address},
            product=EvmProduct.STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=360,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_GRT,
            balance=Balance(amount=FVal(delegate_tax)),
            location_label=ADDY_USER,
            notes=f'Burn {delegate_tax} GRT as delegation tax',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
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
    gas_fee, undelegate_amount, lock_time = '0.00307607001551556', '1003.70342593701668535', '983'
    indexer_address = string_to_evm_address('0x6125eA331851367716beE301ECDe7F38A7E429e7')
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
            location_label=ADDY_USER,
            notes=f'Burned {gas_fee} ETH for gas',
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
            notes=f'Undelegate {undelegate_amount} GRT from indexer {indexer_address}. Lock expires in {lock_time} seconds',  # noqa: E501
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
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
    gas_fees, withdrawn_amount = '0.000651667321615926', '1003.70342593701668535'
    indexer_address = string_to_evm_address('0x6125eA331851367716beE301ECDe7F38A7E429e7')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ADDY_USER,
            notes=f'Burned {gas_fees} ETH for gas',
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
            balance=Balance(amount=FVal(withdrawn_amount)),
            location_label=ADDY_USER,
            notes=f'Withdraw {withdrawn_amount} GRT from indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [[ADDY_USER_1_ARB]])
def test_thegraph_delegate_arbitrum_one(database, arbitrum_one_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x3c846f305330969fb0ddb87c5ae411b4e9692f451a7ff3237b6f71020030c7d1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1713366299000)
    gas_fees, approve_amount, delegate_amount, delegate_tax = '0.000003483187128', '1.009574848602990389', '24.9745', '0.1255'  # noqa: E501
    indexer_address = string_to_evm_address('0xE13840A2E92e0Cb17A246609b432D0fA2e418774')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ADDY_USER_1_ARB,
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=58,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GRT_ARB,
            balance=Balance(amount=FVal(approve_amount)),
            location_label=ADDY_USER_1_ARB,
            notes=f'Set GRT spending approval of {ADDY_USER_1_ARB} by {CONTRACT_STAKING_ARB} to {approve_amount}',  # noqa: E501
            counterparty=None,
            address=CONTRACT_STAKING_ARB,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=59,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GRT_ARB,
            balance=Balance(amount=FVal(delegate_amount)),
            location_label=ADDY_USER_1_ARB,
            notes=f'Delegate {delegate_amount} GRT to indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
            extra_data={'indexer': indexer_address},
            product=EvmProduct.STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=60,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_GRT_ARB,
            balance=Balance(amount=FVal(delegate_tax)),
            location_label=ADDY_USER_1_ARB,
            notes=f'Burn {delegate_tax} GRT as delegation tax',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [[ADDY_USER_2_ARB]])
def test_thegraph_undelegate_arbitrum_one(database, arbitrum_one_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xc66ea685db10809b1765e8381175ada7b021b5a40f57572e220a8b94235c1f72')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1700727276000)
    gas_fees, withdraw_amount, undelegate_amount = '0.0000568994', '49.766469576778571786', '50.576247644221196145'  # noqa: E501
    indexer_address = string_to_evm_address('0xf92f430Dd8567B0d466358c79594ab58d919A6D4')
    lock_time = '390'

    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ADDY_USER_2_ARB,
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GRT_ARB,
            balance=Balance(amount=FVal(withdraw_amount)),
            location_label=ADDY_USER_2_ARB,
            notes=f'Withdraw {withdraw_amount} GRT from indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GRT_ARB,
            balance=Balance(),
            location_label=ADDY_USER_2_ARB,
            notes=f'Undelegate {undelegate_amount} GRT from indexer {indexer_address}. Lock expires in {lock_time} seconds',  # noqa: E501
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('arbitrum_one_accounts', [[ADDY_USER_3_ARB]])
def test_thegraph_delegated_withdrawn_arbitrum_one(database, arbitrum_one_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xd6847bc02b65891118caaa8a2882cf5db6e0938c909db112e4fa6930929d8c39')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1713445792000)
    gas_fees, withdrawn_amount = '0.00000134642', '9.949999999999999998'
    indexer_address = string_to_evm_address('0xf92f430Dd8567B0d466358c79594ab58d919A6D4')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_fees)),
            location_label=ADDY_USER_3_ARB,
            notes=f'Burned {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=67,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GRT_ARB,
            balance=Balance(amount=FVal(withdrawn_amount)),
            location_label=ADDY_USER_3_ARB,
            notes=f'Withdraw {withdrawn_amount} GRT from indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
    ]
    assert expected_events == events
