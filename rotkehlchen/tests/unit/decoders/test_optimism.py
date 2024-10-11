
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
from rotkehlchen.chain.optimism.modules.airdrops.decoder import (
    OPTIMISM_AIRDROP_1,
    OPTIMISM_AIRDROP_4,
)
from rotkehlchen.constants.assets import A_ETH, A_OP
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_optimism_airdrop_1_claim(optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0xda810d7e1757c6ce7387b437c26472f802eec47404e60d4f1eaa9f23bf8d8b73
    """
    tx_hash = deserialize_evm_tx_hash('0xda810d7e1757c6ce7387b437c26472f802eec47404e60d4f1eaa9f23bf8d8b73')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1673337921000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.0002038856162166')),
            location_label=ADDY,
            notes='Burned 0.0002038856162166 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_OP,
            balance=Balance(amount=FVal('827.759804739626467328')),
            location_label=ADDY,
            notes='Claim 827.759804739626467328 OP from the optimism airdrop 1',
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_AIRDROP_1,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'optimism_1'},
        )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x168FEB2E7de2aC0c37a239261D3F9e1b396F22a2']])
def test_optimism_airdrop_4_claim(optimism_accounts, optimism_inquirer):
    tx_hash = deserialize_evm_tx_hash('0xb5b478b321a81ae03565dd72bd625fcb203a97f017670b28e306a893414ae83b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp, gas_amount, claim_amount = TimestampMS(1712777987000), '0.000007620095114963', '6000'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas_amount)),
            location_label=optimism_accounts[0],
            notes=f'Burned {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=80,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_OP,
            balance=Balance(amount=FVal(claim_amount)),
            location_label=optimism_accounts[0],
            notes=f'Claim {claim_amount} OP from the optimism airdrop 4',
            counterparty=CPT_OPTIMISM,
            address=OPTIMISM_AIRDROP_4,
            extra_data={AIRDROP_IDENTIFIER_KEY: 'optimism_4'},
        )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [[ADDY]])
def test_optimism_delegate_change(optimism_inquirer):
    """Data taken from
    https://optimistic.etherscan.io/tx/0xe0b31814f787385ab9f680c2ecf7e20e6dd2f880d979a44487768add26faa594
    """
    tx_hash = deserialize_evm_tx_hash('0xe0b31814f787385ab9f680c2ecf7e20e6dd2f880d979a44487768add26faa594')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1673338011000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal('0.00005701303160652')),
            location_label=ADDY,
            notes='Burned 0.00005701303160652 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=ADDY,
            notes=f'Change OP Delegate from {ADDY} to {ADDY}',
            counterparty=CPT_OPTIMISM,
            address=string_to_evm_address('0x4200000000000000000000000000000000000042'),
        )]
    assert expected_events == events
