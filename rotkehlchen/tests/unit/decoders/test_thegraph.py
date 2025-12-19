from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.arbitrum_one.modules.thegraph.constants import (
    CONTRACT_STAKING as CONTRACT_STAKING_ARB,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.thegraph.constants import (
    CONTRACT_STAKING,
    GRAPH_L1_LOCK_TRANSFER_TOOL,
)
from rotkehlchen.chain.evm.decoding.thegraph.constants import CPT_THEGRAPH
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_GRT, A_GRT_ARB
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer

ADDY_USER = string_to_evm_address('0xd200aeEC7Cd9dD27CAB5a85083953a734D4e84f0')
ADDY_USER_2 = string_to_evm_address('0x8Fe178db26ebA2eEdb22575265bf10A63c395a3d')
ADDY_ROTKI = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
ADDY_USER_1_ARB = string_to_evm_address('0xA9728D95567410555557a54EcA320e5E8bEa36a5')
ADDY_USER_2_ARB = string_to_evm_address('0xec9342111098f8b4A293cD8033746d6f8E9e9e7F')
ADDY_USER_3_ARB = string_to_evm_address('0xBe79986821637afD1406BF9278DA55cf9085cF8f')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER]])
def test_thegraph_delegate(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x6ed3377db652151fb8e4794dd994a921a2d029ad317bd3f2a2916af239490fec')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1690731467000)
    delegate_amount, delegate_tax, gas_fees = '998.98', '5.02', '0.002150596408306665'
    approval_amount = '115792089237316195423570985008687907853269984665640563952473.318503163402575923'  # noqa: E501
    indexer_address = string_to_evm_address('0x6125eA331851367716beE301ECDe7F38A7E429e7')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ADDY_USER,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=358,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GRT,
            amount=FVal(approval_amount),
            location_label=ADDY_USER,
            notes=f'Set GRT spending approval of {ADDY_USER} by {CONTRACT_STAKING} to {approval_amount}',  # noqa: E501
            counterparty=None,
            address=CONTRACT_STAKING,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=359,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GRT,
            amount=FVal(delegate_amount),
            location_label=ADDY_USER,
            notes=f'Delegate {delegate_amount} GRT to indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
            extra_data={'indexer': indexer_address},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=360,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_GRT,
            amount=FVal(delegate_tax),
            location_label=ADDY_USER,
            notes=f'Burn {delegate_tax} GRT as delegation tax',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_ROTKI]])
def test_thegraph_contract_deposit_gas(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xf254ac1bbfbf07ca21042edd3ff78dad7c3158c8218598b5359b6e415e0977b7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1706311139000)
    gas, deposit_amount = '0.000626151499903872', '0.001135647343563552'
    indexer = string_to_evm_address('0x7D91717579885BfCFec3Cb4B4C4fe71c1EedD4dE')
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ADDY_ROTKI,
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(deposit_amount),
            location_label=ADDY_ROTKI,
            notes=f'Deposit {deposit_amount} ETH to {GRAPH_L1_LOCK_TRANSFER_TOOL} contract to pay for the gas in L2.',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_THEGRAPH,
            address=GRAPH_L1_LOCK_TRANSFER_TOOL,
            extra_data={'indexer': indexer},
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_ROTKI]])
def test_thegraph_contract_transfer_approval(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xbb8280cc9ca9de1d33e573a4381d88525a214fc45f84415129face03125ba22f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1706311067000)
    gas = '0.001243940743655704'
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ADDY_ROTKI,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=415,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GRT,
            amount=ZERO,
            location_label=ADDY_ROTKI,
            notes='Approve contract transfer',
            counterparty=CPT_THEGRAPH,
            address=string_to_evm_address('0x7D91717579885BfCFec3Cb4B4C4fe71c1EedD4dE'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_ROTKI]])
def test_thegraph_contract_delegation_transferred_to_l2_vested(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x48321bb00e5c5b67f080991864606dbc493051d20712735a579d7ae31eca3d78')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1706316575000)
    gas, delegation_amount = '0.0034549683606123', '199846.719749385820105919'
    indexer = string_to_evm_address('0x5A8904be09625965d9AEc4BFfD30D853438a053e')
    indexer_l2 = string_to_evm_address('0x2f09092aacd80196FC984908c5A9a7aB3ee4f1CE')
    delegator_l2 = string_to_evm_address('0x9F219c3D048967990f675F49C1117B0598331408')
    contract = string_to_evm_address('0x7D91717579885BfCFec3Cb4B4C4fe71c1EedD4dE')
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ADDY_ROTKI,
            notes=f'Burn {gas} ETH for gas',
            identifier=None,
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=186,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GRT,
            amount=FVal(delegation_amount),
            location_label=ADDY_ROTKI,
            notes=f'Delegation of {delegation_amount} GRT transferred from indexer {indexer} to L2 indexer {indexer_l2}.',  # noqa: E501
            identifier=None,
            tx_ref=tx_hash,
            counterparty=CPT_THEGRAPH,
            address=contract,
            extra_data={'delegator_l2': delegator_l2, 'indexer_l2': indexer_l2, 'beneficiary': ADDY_ROTKI},  # noqa: E501
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER_2, ADDY_ROTKI]])
def test_thegraph_contract_delegation_transferred_to_l2(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xed80711e4cb9c428790f0d9b51f79473bf5253d5d03c04d958d411e7fa34a92e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1706317031000)
    eth_amount, gas, delegation_amount = '0.000255709530674816', '0.002540860890653745', '39243.651715794449516669'  # noqa: E501
    indexer = string_to_evm_address('0xb06071394531B63b0bac78f27e12dc2BEaA913E4')
    indexer_l2 = string_to_evm_address('0x0fd8FD1dC8162148cb9413062FE6C6B144335Dbf')
    delegator_l2 = string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306')
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ADDY_USER_2,
            notes=f'Burn {gas} ETH for gas',
            tx_ref=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal(eth_amount),
            location_label=ADDY_USER_2,
            notes=f'Send {eth_amount} ETH to {CONTRACT_STAKING}',
            tx_ref=tx_hash,
            address=CONTRACT_STAKING,
        ), EvmEvent(
            sequence_index=364,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GRT,
            amount=FVal(delegation_amount),
            location_label=ADDY_USER_2,
            notes=f'Delegation of {delegation_amount} GRT transferred from indexer {indexer} to L2 indexer {indexer_l2}.',  # noqa: E501
            tx_ref=tx_hash,
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
            extra_data={'delegator_l2': delegator_l2, 'indexer_l2': indexer_l2, 'beneficiary': ADDY_ROTKI},  # noqa: E501
        ),
    ]

    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER]])
def test_thegraph_undelegate(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x5ca5244868d9c0d8c30a1cad0feaf137bd28acd9c3f669a09a3a199fd75ad25a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1691771855000)
    gas_fee, undelegate_amount, lock_time = '0.00307607001551556', '1003.70342593701668535', '983'
    indexer_address = string_to_evm_address('0x6125eA331851367716beE301ECDe7F38A7E429e7')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fee),
            location_label=ADDY_USER,
            notes=f'Burn {gas_fee} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=297,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GRT,
            amount=ZERO,
            location_label=ADDY_USER,
            notes=f'Undelegate {undelegate_amount} GRT from indexer {indexer_address}. Lock expires at epoch {lock_time}',  # noqa: E501
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY_USER]])
def test_thegraph_delegated_withdrawn(ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x49307751de5ba4cf98fccbdd1ab8387fd60a7ce120800212c216bf0a6a04acfa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1694577371000)
    gas_fees, withdrawn_amount = '0.000651667321615926', '1003.70342593701668535'
    indexer_address = string_to_evm_address('0x6125eA331851367716beE301ECDe7F38A7E429e7')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ADDY_USER,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=208,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GRT,
            amount=FVal(withdrawn_amount),
            location_label=ADDY_USER,
            notes=f'Withdraw {withdrawn_amount} GRT from indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [[ADDY_USER_1_ARB]])
def test_thegraph_delegate_arbitrum_one(arbitrum_one_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x3c846f305330969fb0ddb87c5ae411b4e9692f451a7ff3237b6f71020030c7d1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1713366299000)
    gas_fees, approve_amount, delegate_amount, delegate_tax = '0.000003483187128', '1.009574848602990389', '24.9745', '0.1255'  # noqa: E501
    indexer_address = string_to_evm_address('0xE13840A2E92e0Cb17A246609b432D0fA2e418774')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ADDY_USER_1_ARB,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=58,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_GRT_ARB,
            amount=FVal(approve_amount),
            location_label=ADDY_USER_1_ARB,
            notes=f'Set GRT spending approval of {ADDY_USER_1_ARB} by {CONTRACT_STAKING_ARB} to {approve_amount}',  # noqa: E501
            counterparty=None,
            address=CONTRACT_STAKING_ARB,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=59,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=A_GRT_ARB,
            amount=FVal(delegate_amount),
            location_label=ADDY_USER_1_ARB,
            notes=f'Delegate {delegate_amount} GRT to indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
            extra_data={'indexer': indexer_address},
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=60,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_GRT_ARB,
            amount=FVal(delegate_tax),
            location_label=ADDY_USER_1_ARB,
            notes=f'Burn {delegate_tax} GRT as delegation tax',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [[ADDY_USER_2_ARB]])
def test_thegraph_undelegate_arbitrum_one(arbitrum_one_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xc66ea685db10809b1765e8381175ada7b021b5a40f57572e220a8b94235c1f72')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1700727276000)
    gas_fees, withdraw_amount, undelegate_amount = '0.0000568994', '49.766469576778571786', '50.576247644221196145'  # noqa: E501
    indexer_address = string_to_evm_address('0xf92f430Dd8567B0d466358c79594ab58d919A6D4')
    lock_time = '390'

    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ADDY_USER_2_ARB,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=11,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GRT_ARB,
            amount=FVal(withdraw_amount),
            location_label=ADDY_USER_2_ARB,
            notes=f'Withdraw {withdraw_amount} GRT from indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=12,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_GRT_ARB,
            amount=ZERO,
            location_label=ADDY_USER_2_ARB,
            notes=f'Undelegate {undelegate_amount} GRT from indexer {indexer_address}. Lock expires at epoch {lock_time}',  # noqa: E501
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [[ADDY_USER_3_ARB]])
def test_thegraph_delegated_withdrawn_arbitrum_one(arbitrum_one_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xd6847bc02b65891118caaa8a2882cf5db6e0938c909db112e4fa6930929d8c39')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1713445792000)
    gas_fees, withdrawn_amount = '0.00000134642', '9.949999999999999998'
    indexer_address = string_to_evm_address('0xf92f430Dd8567B0d466358c79594ab58d919A6D4')
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_fees),
            location_label=ADDY_USER_3_ARB,
            notes=f'Burn {gas_fees} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=67,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=A_GRT_ARB,
            amount=FVal(withdrawn_amount),
            location_label=ADDY_USER_3_ARB,
            notes=f'Withdraw {withdrawn_amount} GRT from indexer {indexer_address}',
            counterparty=CPT_THEGRAPH,
            address=CONTRACT_STAKING_ARB,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x01A0370bc11CA10D1D7AbFB892E85127C4eE921C']])
def test_delegate_horizon(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """This checks that delegation post-horizon works correctly"""
    tx_hash = deserialize_evm_tx_hash('0x7beba0df2eee3a7425ec1dae22b33209c40d37bba73bddd8749a29143ce57f14')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1765816117000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000001695601856'),
        location_label=(delegator_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=7,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=A_GRT_ARB,
        amount=FVal(delegate_amount := '19356.3701652321'),
        location_label=delegator_address,
        notes=f'Delegate {delegate_amount} GRT to indexer 0x0058223C6617CCa7ce76fC929Ec9724cd43d4542',  # noqa: E501
        counterparty=CPT_THEGRAPH,
        address=CONTRACT_STAKING_ARB,
        extra_data={
            'indexer': '0x0058223C6617CCa7ce76fC929Ec9724cd43d4542',
            'verifier': '0xb2Bb92d0DE618878E438b55D5846cfecD9301105',
        },
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=8,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_GRT_ARB,
        amount=FVal(approval_amount := '115792089237316195423570985008687907853269984665640563400795.889548978764957742'),  # noqa: E501
        location_label=delegator_address,
        notes=f'Set GRT spending approval of {delegator_address} by {CONTRACT_STAKING_ARB} to {approval_amount}',  # noqa: E501
        address=CONTRACT_STAKING_ARB,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x40792210D62f471612E2891877d8612E02cB7Db6']])
def test_undelegate_horizon(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """This checks that un-delegation post-horizon works correctly"""
    tx_hash, lock_expiration = deserialize_evm_tx_hash('0x57f89011a6a489c1d901bb0e30a54c8089d4e5faf60ac26881ef4fd02ec89988'), Timestamp(1765815857)  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1765815857000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000006997289591'),
        location_label=(delegator_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=9,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_GRT_ARB,
        amount=ZERO,
        location_label=delegator_address,
        notes=f'Undelegate 163.464055706537930283 GRT from indexer 0xECcDF8231326A9c5aaD32df76a633aaa4c49b104. Lock expires at {decoder.decoders["Thegraph"].timestamp_to_date(lock_expiration)}',  # type: ignore  # noqa: E501
        counterparty=CPT_THEGRAPH,
        address=CONTRACT_STAKING_ARB,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x1C15b0374FC43d594A3Dc4147E45741FBA6c70f3']])
def test_thegraph_delegated_withdrawn_horizon(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
) -> None:
    """This checks that delegation withdrawal post-horizon works correctly"""
    tx_hash = deserialize_evm_tx_hash('0xcaba90e80b65df1d6fc542940d0f8362a16f93c03cfb6f0603dad1eb45b07b0e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1765823914000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000890050078'),
        location_label=(delegator_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=11,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=A_GRT_ARB,
        amount=FVal(withdraw_amount := '613.662387915752934545'),
        location_label=delegator_address,
        notes=f'Withdraw {withdraw_amount} GRT from indexer 0x920FDEB00EE04dd72f62d8A8f80F13c82ef76C1e',  # noqa: E501
        counterparty=CPT_THEGRAPH,
        address=CONTRACT_STAKING_ARB,
    )]
