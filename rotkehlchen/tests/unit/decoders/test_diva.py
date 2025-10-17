import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.airdrops import AIRDROP_IDENTIFIER_KEY
from rotkehlchen.chain.ethereum.modules.diva.constants import CPT_DIVA
from rotkehlchen.chain.ethereum.modules.diva.decoder import DIVA_GOVERNOR
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DIVA, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_diva_delegate(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x806081bcc60a40db22bae2c1729f240f48de4b73e76b673fc4767bcee4f1c704')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1690964039000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001694706319628652'),
            location_label=ethereum_accounts[0],
            notes='Burn 0.001694706319628652 ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=94,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_DIVA,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Change DIVA Delegate from 0xc37b40ABdB939635068d3c5f13E7faF686F03B65 to 0x42E6DD8D517abB3E4f6611Ca53a8D1243C183fB0',  # noqa: E501
            counterparty=CPT_DIVA,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_diva_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc66dd53da9837e5197f95d32065807706a118dc2ff326a5e3bf8844b8ee261c2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1688847971000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002211737193518538'),
            location_label=ethereum_accounts[0],
            notes='Burn 0.002211737193518538 ETH for gas',
            counterparty=CPT_GAS,
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=175,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.AIRDROP,
            asset=A_DIVA,
            amount=FVal(12000),
            location_label=ethereum_accounts[0],
            notes='Claim 12000 DIVA from the DIVA airdrop',
            counterparty=CPT_DIVA,
            address=string_to_evm_address('0x777E2B2Cc7980A6bAC92910B95269895EEf0d2E8'),
            extra_data={AIRDROP_IDENTIFIER_KEY: 'diva'},
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=177,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_DIVA,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes='Change DIVA Delegate from 0xc37b40ABdB939635068d3c5f13E7faF686F03B65 to 0xc37b40ABdB939635068d3c5f13E7faF686F03B65',  # noqa: E501
            counterparty=CPT_DIVA,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_vote_cast(ethereum_inquirer, ethereum_accounts):
    """Test voting for DIVA governance"""
    tx_hash = deserialize_evm_tx_hash('0x640818700732a7345f085d14377adf285098ae33747da21444e594a64c905d41')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1694557811000)
    gas_str = '0.00074796777559248'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=400,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Vote FOR diva governance proposal https://www.tally.xyz/gov/diva/proposal/52481024395238134144299582623582875841236980209822828761178984408970724801644',
            counterparty=CPT_DIVA,
            address=DIVA_GOVERNOR,
        ),
    ]
    assert events == expected_events
