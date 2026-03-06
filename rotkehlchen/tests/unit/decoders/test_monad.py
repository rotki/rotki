import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.monad.modules.wmon.constants import CPT_WMON
from rotkehlchen.constants.assets import A_MON, A_WMON
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('monad_accounts', [['0xB5c0e65Fb2A31CB935F5234A9982050AC1693E55']])
def test_wmon_wrap(monad_inquirer, monad_accounts):
    """Test wrapping MON to WMON on Monad"""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=monad_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xbec79c9b2b34a4374435313ca8f09ade4054af7b8111f42dbdc69a50890cc8ee')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1758018567000)),
        location=Location.MONAD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_MON,
        amount=FVal(gas_amount := '0.002255650000045113'),
        location_label=(user := monad_accounts[0]),
        notes=f'Burn {gas_amount} MON for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.MONAD,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_MON,
        amount=FVal(wrapped_amount := '0.01'),
        location_label=user,
        notes=f'Wrap {wrapped_amount} MON in WMON',
        counterparty=CPT_WMON,
        address=(wmon_address := A_WMON.resolve_to_evm_token().evm_address),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.MONAD,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_WMON,
        amount=FVal(wrapped_amount),
        location_label=user,
        notes=f'Receive {wrapped_amount} WMON',
        counterparty=CPT_WMON,
        address=wmon_address,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('monad_accounts', [['0x9D24d495F7380BA80dC114D8C2cF1a54a68e25A4']])
def test_wmon_unwrap(monad_inquirer, monad_accounts):
    """Test unwrapping WMON to MON on Monad"""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=monad_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x2f2eb8f692117ee026b0e0eec7bbd26d90f6bdbba2216deac70b829ce9eff636')),  # noqa: E501
    )
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1759393762000)),
        location=Location.MONAD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_MON,
        amount=FVal(gas_amount := '0.0020595365'),
        location_label=(user := monad_accounts[0]),
        notes=f'Burn {gas_amount} MON for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.MONAD,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_WMON,
        amount=FVal(unwrapped_amount := '0.00995487'),
        location_label=user,
        notes=f'Unwrap {unwrapped_amount} WMON',
        counterparty=CPT_WMON,
        address=(wmon_address := A_WMON.resolve_to_evm_token().evm_address),
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.MONAD,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_MON,
        amount=FVal(unwrapped_amount),
        location_label=user,
        notes=f'Receive {unwrapped_amount} MON',
        counterparty=CPT_WMON,
        address=wmon_address,
    )]
