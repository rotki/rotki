import pytest

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.pickle_finance.constants import (
    CORN_TOKEN_ID,
    CORNICHON_CLAIM,
    CPT_PICKLE,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

PICKLE_JAR = string_to_evm_address('0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0f1a748cDF53Bbad378CE2C4429463d01CcE0C3f']])
def test_pickle_deposit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xba9a52a144d4e79580a557160e9f8269d3e5373ce44bce00ebd609754034b7bd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_str, deposit_str, withdraw_str, approve_str = TimestampMS(1646619202000), '0.00355751579933013', '907.258590539447889901', '560.885632516582380401', '115792089237316195423570985008687907853269984665640564027654.491316674464992473'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=260,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
            amount=FVal(deposit_str),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_str} LOOKS in pickle contract',
            counterparty=CPT_PICKLE,
            address=PICKLE_JAR,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=261,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken('eip155:1/erc20:0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
            amount=FVal(approve_str),
            location_label=ethereum_accounts[0],
            notes=f'Set LOOKS spending approval of {ethereum_accounts[0]} by {PICKLE_JAR} to {approve_str}',  # noqa: E501
            address=PICKLE_JAR,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=262,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
            amount=FVal(withdraw_str),
            location_label=ethereum_accounts[0],
            notes=f'Receive {withdraw_str} pLOOKS after depositing in pickle contract',
            counterparty=CPT_PICKLE,
            address=PICKLE_JAR,
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC7Dc4Cd171812a441A30472219d390f4F15f6070']])
def test_pickle_withdraw(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x91bc102e1cbb0e4542a10a7a13370b5e591d8d284989bdb0ca4ece4e54e61bab')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_str, deposit_str, withdraw_str = TimestampMS(1646873135000), '0.00389232626065528', '245.522202162316534411', '403.097099656688209687'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=106,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xb4EBc2C371182DeEa04B2264B9ff5AC4F0159C69'),
            amount=FVal(deposit_str),
            location_label=ethereum_accounts[0],
            notes=f'Return {deposit_str} pLOOKS to the pickle contract',
            counterparty=CPT_PICKLE,
            address=PICKLE_JAR,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=107,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=EvmToken('eip155:1/erc20:0xf4d2888d29D722226FafA5d9B24F9164c092421E'),
            amount=FVal(withdraw_str),
            location_label=ethereum_accounts[0],
            notes=f'Unstake {withdraw_str} LOOKS from the pickle contract',
            counterparty=CPT_PICKLE,
            address=PICKLE_JAR,
        )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd7aC4581eF4E2BB6cC3734Da183B981bfd0Ee2A2']])
def test_claim_cornichon(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x23a52632e47eeaf9588972cc3f65a2101745952880be17828d810da3735f333f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_str, amount_str = TimestampMS(1606695800000), '0.002380306', '125.214613076726835921'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=196,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=EvmToken(CORN_TOKEN_ID),
            amount=FVal(amount_str),
            location_label=ethereum_accounts[0],
            notes=f'Claim {amount_str} CORN from the pickle finance hack compensation airdrop',
            counterparty=CPT_PICKLE,
            address=CORNICHON_CLAIM,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'cornichon'},
        )]
    assert events == expected_events
