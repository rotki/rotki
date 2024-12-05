import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.optimism.modules.giveth.constants import (
    CPT_GIVETH,
    GIV_DISTRO,
    GIV_TOKEN_ID,
    GIVPOW_TOKEN_ID,
    GIVPOWER_STAKING,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xB9573982875b83aaDc1296726E2ae77D13D9B98F']])
def test_optimism_stake_deposit(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x875d69d471b2c31c5175848b11f68815e197fd609509cee420075685d21feccb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user, gas, amount = TimestampMS(1733231821000), optimism_accounts[0], '0.00000045219580173', '416.766115409070747461'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=37,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=EvmToken(GIV_TOKEN_ID),
            balance=Balance(amount=FVal(ZERO)),
            location_label=user,
            notes=f'Revoke GIV spending approval of {user} by {GIVPOWER_STAKING}',
            address=GIVPOWER_STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=38,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken(GIV_TOKEN_ID),
            balance=Balance(amount=FVal(amount)),
            location_label=user,
            notes=f'Deposit {amount} GIV for staking',
            counterparty=CPT_GIVETH,
            address=GIVPOWER_STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=39,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(GIVPOW_TOKEN_ID),
            balance=Balance(amount=FVal(amount)),
            location_label=user,
            notes=f'Receive {amount} POW after depositing GIV',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xB9573982875b83aaDc1296726E2ae77D13D9B98F']])
def test_optimism_lock(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x160a78b4ce5001b407db9f5fca3e64fcc0619995d8888c66605f69525eed0270')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user, gas, giv_amount, pow_amount = TimestampMS(1733231841000), optimism_accounts[0], '0.000000453377609571', '416.766115409070747461', '172.630177184494281415'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=EvmToken(GIV_TOKEN_ID),
            balance=Balance(amount=FVal(giv_amount)),
            location_label=user,
            notes=f'Lock {giv_amount} GIV for 1 round/s',
            counterparty=CPT_GIVETH,
            address=GIVPOWER_STAKING,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=EvmToken(GIVPOW_TOKEN_ID),
            balance=Balance(amount=FVal(pow_amount)),
            location_label=user,
            notes=f'Receive {pow_amount} POW after locking GIV',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0xAca2F322d69E07993E073C8730180FB139cA4446']])
def test_optimism_withdraw(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd687dcd65be8a2a9aea83123a9bdae775232af23e5846f01ade70f3f5280d392')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user, gas, amount = TimestampMS(1732744801000), optimism_accounts[0], '0.000000258591448555', '798.24369413782804452'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=EvmToken(GIVPOW_TOKEN_ID),
            balance=Balance(amount=FVal(amount)),
            location_label=user,
            notes=f'Return {amount} POW to Giveth staking',
            counterparty=CPT_GIVETH,
            address=ZERO_ADDRESS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=EvmToken(GIV_TOKEN_ID),
            balance=Balance(amount=FVal(amount)),
            location_label=user,
            notes=f'Withdraw {amount} GIV from staking',
            counterparty=CPT_GIVETH,
            address=GIVPOWER_STAKING,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x8a0F0a09e622bc0677a404343129FB5dDA1E2d33']])
def test_optimism_claim(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2144b2417404977fe2b4b4064b58cdaafc90e416e68a5ad16c04989cc025f3b1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, user, gas, amount = TimestampMS(1732520935000), optimism_accounts[0], '0.000001950934408636', '55.906071953178772758'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=41,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=EvmToken(GIV_TOKEN_ID),
            balance=Balance(amount=FVal(amount)),
            location_label=user,
            notes=f'Claim {amount} GIV as staking reward',
            counterparty=CPT_GIVETH,
            address=GIV_DISTRO,
        ),
    ]
    assert events == expected_events
