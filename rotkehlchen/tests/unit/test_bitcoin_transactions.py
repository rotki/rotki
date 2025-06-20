from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.bitcoin.constants import BTC_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.types import string_to_btc_address
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.bitcoin import get_decoded_events_of_bitcoin_tx
from rotkehlchen.types import BTCAddress, Location, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.manager import BitcoinManager


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [
    ['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'],
    ['1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp'],
    ['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4', '1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp'],
])
def test_1input_1output(bitcoin_manager: 'BitcoinManager', btc_accounts: list[BTCAddress]) -> None:
    tx_id, address1, address2 = (
        'e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6',
        string_to_btc_address('bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'),
        string_to_btc_address('1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp'),
    )
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    fee_event = HistoryEvent(
        event_identifier=(event_identifier := f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1686238076000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00002492')),
        location_label=address1,
        notes=f'Spend {fee_amount} BTC for fees',
    )
    if btc_accounts == [address1]:  # only input tracked - fee event and spend event
        assert events == [fee_event, HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(transfer_amount := '0.00001437'),
            location_label=address1,
            notes=f'Send {transfer_amount} BTC to {address2}',
        )]
    elif btc_accounts == [address2]:  # only output tracked - single receive event
        assert events == [HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(transfer_amount := '0.00001437'),
            location_label=address2,
            notes=f'Receive {transfer_amount} BTC from {address1}',
        )]
    else:  # input and output tracked - fee event and transfer event
        assert events == [fee_event, HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(transfer_amount := '0.00001437'),
            location_label=address1,
            notes=f'Transfer {transfer_amount} BTC to {address2}',
        )]


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [
    ['17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy'],
    ['17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf', '17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy'],
])
def test_1input_2output(bitcoin_manager: 'BitcoinManager', btc_accounts: list[BTCAddress]) -> None:
    tx_id, address1, address2, address3 = (
        '450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144',
        string_to_btc_address('17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf'),
        string_to_btc_address('17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy'),
        string_to_btc_address('3CK4fEwbMP7heJarmU4eqA3sMbVJyEnU3V'),
    )
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    if btc_accounts == [address2]:  # only one receiver tracked - single receive event
        assert events == [HistoryEvent(
            event_identifier=f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}',
            sequence_index=0,
            timestamp=TimestampMS(1339247930000),
            location=Location.BITCOIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(amount1 := '0.56196218'),
            notes=f'Receive {amount1} BTC from {address1}',
            location_label=address2,
        )]
    else:  # Sender and one receiver tracked - fee event, transfer event, and spend event
        assert events == [HistoryEvent(
            event_identifier=(event_identifier := f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}'),
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1339247930000)),
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=(fee_amount := FVal('0.01000000')),
            location_label=address1,
            notes=f'Spend {fee_amount} BTC for fees',
        ), HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(amount1 := '0.56196218'),
            notes=f'Transfer {amount1} BTC to {address2}',
            location_label=address1,
        ), HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(amount2 := '0.10000000'),
            notes=f'Send {amount2} BTC to {address3}',
            location_label=address1,
        )]


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
def test_op_return(bitcoin_manager: 'BitcoinManager', btc_accounts: list[BTCAddress]) -> None:
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := 'eb4d2def800c4993928a6f8cc3dd350933a1fb71e6706902025f29a061e5547f'),
    ) == [HistoryEvent(
        event_identifier=(event_identifier := f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1729677861000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00001000')),
        location_label=btc_accounts[0],
        notes=f'Spend {fee_amount} BTC for fees',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=ZERO,
        notes='Store text on the blockchain: #FreeSamourai',
    )]
