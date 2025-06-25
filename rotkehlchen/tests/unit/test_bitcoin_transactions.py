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


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [
    ['bc1qyy30guv6m5ez7ntj0ayr08u23w3k5s8vg3elmxdzlh8a3xskupyqn2lp5w'],
    ['3G2W5fwfsXfgVJrBc9gxTYfHi6C9zUdtVd'],
    ['bc1qwqdg6squsna38e46795at95yu9atm8azzmyvckulcc7kytlcckxswvvzej'],
    [
        'bc1qyy30guv6m5ez7ntj0ayr08u23w3k5s8vg3elmxdzlh8a3xskupyqn2lp5w',
        'bc1qwqdg6squsna38e46795at95yu9atm8azzmyvckulcc7kytlcckxswvvzej',
        '3G2W5fwfsXfgVJrBc9gxTYfHi6C9zUdtVd',
    ],
])
def test_2input_1output(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    """This tx actually has 4 inputs and 2 outputs, but 3 inputs are from the same address,
    so it only has 2 distinct inputs, and 1 output is simply returning extra btc to one of the
    input addresses, which results in only 1 actual output when decoding normal transfers.

    So this is testing both the self-transfer and multi-input single output cases.
    """
    tx_id, address1, address2, address3, transfer_amount1, transfer_amount2 = (
        '4a367acdeeaaf4bca2d9ae81d4cf4c42ac0f8131f52dc53222ff17189e2099b1',
        'bc1qyy30guv6m5ez7ntj0ayr08u23w3k5s8vg3elmxdzlh8a3xskupyqn2lp5w',
        '3G2W5fwfsXfgVJrBc9gxTYfHi6C9zUdtVd',
        'bc1qwqdg6squsna38e46795at95yu9atm8azzmyvckulcc7kytlcckxswvvzej',
        FVal('1.29845349708138288872596018273081044498336247250578083582426259094241723535052'),
        FVal('0.119546502918617111274039817269189555016637527494219164175737409057582764649484'),
    )
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    fee_event1 = HistoryEvent(
        event_identifier=(event_identifier := f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749114440000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount1 := FVal('0.000439532918617111274039817269189555016637527494219164175737409057582764649483955')),  # noqa: E501
        location_label=address1,
        notes=f'Spend {fee_amount1} BTC for fees',
    )
    fee_event2 = HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount2 := FVal('0.000040467081382888725960182730810444983362472505780835824262590942417235350516045')),  # noqa: E501
        location_label=address2,
        notes=f'Spend {fee_amount2} BTC for fees',
    )
    if btc_accounts == [address1]:  # self-transfer input address tracked
        assert events == [fee_event1, HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=transfer_amount1,
            location_label=address1,
            notes=f'Send {transfer_amount1} BTC to {address3}',
        )]
    elif btc_accounts == [address2]:  # other input address tracked
        assert events == [fee_event2, HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=transfer_amount2,
            location_label=address2,
            notes=f'Send {transfer_amount2} BTC to {address3}',
        )]
    elif btc_accounts == [address3]:  # output address tracked
        assert events == [HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=transfer_amount1,
            location_label=address3,
            notes=f'Receive {transfer_amount1} BTC from {address1}',
        ), HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=transfer_amount2,
            location_label=address3,
            notes=f'Receive {transfer_amount2} BTC from {address2}',
        )]
    else:  # all addresses tracked
        fee_event2.sequence_index = 1
        assert events == [fee_event1, fee_event2, HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=transfer_amount1,
            location_label=address1,
            notes=f'Transfer {transfer_amount1} BTC to {address3}',
        ), HistoryEvent(
            event_identifier=event_identifier,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.TRANSFER,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=transfer_amount2,
            location_label=address2,
            notes=f'Transfer {transfer_amount2} BTC to {address3}',
        )]
        # Confirm totals match the original values in the tx.
        assert fee_amount1 + fee_amount2 == FVal('0.000480000000000000000000000000000000000000000000000000000000000000000000000000000')  # noqa: E501
        assert transfer_amount1 + transfer_amount2 == FVal('1.41800000000000000000000000000000000000000000000000000000000000000000000000000')  # noqa: E501


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [[
    'bc1qpeuhg6gcs4gdze7cmp3tmu9yjzkp7edtt6f4k4',
    '1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH',
    'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
    'bc1qxdw4t0uvnztl6jxuxvvpnsmx9fg4w7qxv5tgm4',
    '1HZwkjkeaoZfTSaJxDw6aKkxp45agDiEzN',
]])
def test_3input_2output(bitcoin_manager: 'BitcoinManager', btc_accounts: list[BTCAddress]) -> None:
    """This tx actually has 4 inputs, but 1 input is also an output, with its output value being
    more than its input value, canceling it out as an input, and resulting in only 3 actual inputs.
    """
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := 'cccd3a9ce6c59fd0b5ae4244cb9b239387efa31c96e0d45c0c0b82c0d7ee3bd8'),
    ) == [HistoryEvent(
        event_identifier=(event_identifier := f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1711929790000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount1 := FVal('0.0000349900109618287314696311430719520663908035422202581481970374366538300400020661')),  # noqa: E501
        location_label=(address1 := btc_accounts[0]),
        notes=f'Spend {fee_amount1} BTC for fees',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount2 := FVal('0.0000000549945190856342651844284640239668045982288898709259014812816730849799989669482')),  # noqa: E501
        location_label=(address2 := btc_accounts[1]),
        notes=f'Spend {fee_amount2} BTC for fees',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount3 := FVal('0.0000000549945190856342651844284640239668045982288898709259014812816730849799989669518')),  # noqa: E501
        location_label=(address3 := btc_accounts[2]),
        notes=f'Spend {fee_amount3} BTC for fees',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=(spend_amount1 := FVal('0.00343890998903817126853036885692804793360919645777974185180296256334616995999793')),  # noqa: E501
        location_label=address1,
        notes=f'Send {spend_amount1} BTC to {(address4 := btc_accounts[3])}, {(address5 := btc_accounts[4])}',  # noqa: E501
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=(spend_amount2 := FVal('0.00000540500548091436573481557153597603319540177111012907409851871832691502000103305')),  # noqa: E501
        location_label=address2,
        notes=f'Send {spend_amount2} BTC to {address4}, {address5}',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=5,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=(spend_amount3 := FVal('0.00000540500548091436573481557153597603319540177111012907409851871832691502000103305')),  # noqa: E501
        location_label=address3,
        notes=f'Send {spend_amount3} BTC to {address4}, {address5}',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=6,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal('0.00031546'),
        location_label=address4,
        notes=f'Receive 0.00031546 BTC from {address1}, {address2}, {address3}',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=7,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal('0.00313426'),
        location_label=address5,
        notes=f'Receive 0.00313426 BTC from {address1}, {address2}, {address3}',
    )]


@pytest.mark.parametrize('btc_accounts', [['1PJJygLB42VsaTgo2twFPgRT8CNz1bpGNE']])
def test_p2pk(bitcoin_manager: 'BitcoinManager', btc_accounts: list[BTCAddress]) -> None:
    """This is an old tx that used P2PK instead of P2PKH and has no fee."""
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := '1db6251a9afce7025a2061a19e63c700dffc3bec368bd1883decfac353357a9d'),
    ) == [HistoryEvent(
        event_identifier=f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx_id}',
        sequence_index=0,
        timestamp=TimestampMS(1313042188000),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal('50.00000000'),
        location_label=btc_accounts[0],
        notes='Send 50.00000000 BTC to 15WvMGm9qG1wDb54TMcvgzZsfvz9KdxzoN',
    )]
