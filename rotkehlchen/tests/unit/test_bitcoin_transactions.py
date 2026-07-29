from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.bitcoin.btc.constants import BTC_GROUP_IDENTIFIER_PREFIX
from rotkehlchen.chain.bitcoin.manager import BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcTxIO, BtcTxIODirection
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import BlockchainAccountData
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.bitcoin import get_decoded_events_of_bitcoin_tx, string_to_btc_address
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    BTCAddress,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.bitcoin.btc.manager import BitcoinManager


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [
    ['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'],
    ['1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp'],
    ['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4', '1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp'],
])
def test_1input_1output(bitcoin_manager: BitcoinManager, btc_accounts: list[BTCAddress]) -> None:
    tx_id, address1, address2 = (
        'e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6',
        string_to_btc_address('bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'),
        string_to_btc_address('1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp'),
    )
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    fee_event = HistoryEvent(
        group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
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
            group_identifier=group_identifier,
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
        assert getattr(events[1], BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY) == [address2]
    elif btc_accounts == [address2]:  # only output tracked - single receive event
        assert events == [HistoryEvent(
            group_identifier=group_identifier,
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
        assert getattr(events[0], BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY) == [address1]
    else:  # input and output tracked - fee event and transfer event
        assert events == [fee_event, HistoryEvent(
            group_identifier=group_identifier,
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
        assert getattr(events[1], BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY) == [address2]


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [
    ['17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy'],
    ['17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf', '17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy'],
])
def test_1input_2output(bitcoin_manager: BitcoinManager, btc_accounts: list[BTCAddress]) -> None:
    tx_id, address1, address2, address3 = (
        '450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144',
        string_to_btc_address('17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf'),
        string_to_btc_address('17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy'),
        string_to_btc_address('3CK4fEwbMP7heJarmU4eqA3sMbVJyEnU3V'),
    )
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    if btc_accounts == [address2]:  # only one receiver tracked - single receive event
        assert events == [HistoryEvent(
            group_identifier=f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}',
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
            group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1339247930000)),
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_BTC,
            amount=(fee_amount := FVal('0.01')),
            location_label=address1,
            notes=f'Spend {fee_amount} BTC for fees',
        ), HistoryEvent(
            group_identifier=group_identifier,
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
            group_identifier=group_identifier,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal(amount2 := '0.1'),
            notes=f'Send {amount2} BTC to {address3}',
            location_label=address1,
        )]


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
@pytest.mark.parametrize('use_blockcypher', [True, False])
def test_op_return(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
        use_blockcypher: bool,
) -> None:
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := 'eb4d2def800c4993928a6f8cc3dd350933a1fb71e6706902025f29a061e5547f'),
        use_blockcypher=use_blockcypher,
    ) == [HistoryEvent(
        group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1729677861000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00001')),
        location_label=btc_accounts[0],
        notes=f'Spend {fee_amount} BTC for fees',
    ), HistoryEvent(
        group_identifier=group_identifier,
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
@pytest.mark.parametrize('btc_accounts', [['17rQ1edty4CxuLHCgtvQ9kxwwpwhGrg4d9']])
def test_op_return_multiple_pushbytes(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Test OP_RETURN with multiple OP_PUSHBYTES_1 operations."""
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := '42c4fabe072e70eae555cb41e34291ee5c9ff205c3e5704e230339abc912b339'),
    ) == [HistoryEvent(
        group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749216296000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00002')),
        location_label=(user_address := btc_accounts[0]),
        notes=f'Spend {fee_amount} BTC for fees',
    ), HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=ZERO,
        notes='Store data on the blockchain: a0a1a2a3a4a5a6a7a8a9b0b1b2b3b4b5b6b7b8b9c0c1c2c3c4c5c6c7c8c9d0d1d2d3d4d5d6d7d8d9e0',  # noqa: E501
    ), HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal('0.00006'),
        location_label=user_address,
        notes='Send 0.00006 BTC to bc1qjl5yclpqvqclq4elhl5g2f0fhwytesmk9nqzd0',
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [['17rQ1edty4CxuLHCgtvQ9kxwwpwhGrg4d9']])
def test_op_return_pushdata1(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Test OP_RETURN with OP_PUSHDATA1 (0x4c)."""
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := '2033435de7ce307341231e818ed937cd3a5e8597381fd83a7e5b0234f61b38d3'),
    ) == [HistoryEvent(
        group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1749216962000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00002')),
        location_label=(user_address := btc_accounts[0]),
        notes=f'Spend {fee_amount} BTC for fees',
    ), HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=ZERO,
        notes='Store text on the blockchain: learnmeabitcoin',
    ), HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=FVal('0.00006'),
        location_label=user_address,
        notes='Send 0.00006 BTC to bc1qjl5yclpqvqclq4elhl5g2f0fhwytesmk9nqzd0',
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
        bitcoin_manager: BitcoinManager,
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
        group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
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
        group_identifier=group_identifier,
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
            group_identifier=group_identifier,
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
            group_identifier=group_identifier,
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
            group_identifier=group_identifier,
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
            group_identifier=group_identifier,
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
            group_identifier=group_identifier,
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
            group_identifier=group_identifier,
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
def test_3input_2output(bitcoin_manager: BitcoinManager, btc_accounts: list[BTCAddress]) -> None:
    """This tx actually has 4 inputs, but 1 input is also an output, with its output value being
    more than its input value, canceling it out as an input, and resulting in only 3 actual inputs.

    Every output is tracked as well, so nothing actually leaves the wallet. The tx must cost
    only the fee and decode into transfers. Decoding it as a spend of each input plus a receive
    of each output would report a disposal and an acquisition that never happened, corrupting
    cost basis while leaving the net balance looking correct.
    """
    events = get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := 'cccd3a9ce6c59fd0b5ae4244cb9b239387efa31c96e0d45c0c0b82c0d7ee3bd8'),
    )
    address1, address2, address3, address4, address5 = btc_accounts
    assert events[:3] == [HistoryEvent(
        group_identifier=(group_identifier := f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1711929790000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount1 := FVal('0.0000349900109618287314696311430719520663908035422202581481970374366538300400020661')),  # noqa: E501
        location_label=address1,
        notes=f'Spend {fee_amount1} BTC for fees',
    ), HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount2 := FVal('0.0000000549945190856342651844284640239668045982288898709259014812816730849799989669482')),  # noqa: E501
        location_label=address2,
        notes=f'Spend {fee_amount2} BTC for fees',
    ), HistoryEvent(
        group_identifier=group_identifier,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount3 := FVal('0.0000000549945190856342651844284640239668045982288898709259014812816730849799989669518')),  # noqa: E501
        location_label=address3,
        notes=f'Spend {fee_amount3} BTC for fees',
    )]
    assert fee_amount1 + fee_amount2 + fee_amount3 == FVal('0.0000351')

    # The remaining events are one transfer per input/output pair. A single counterparty each
    # so historical balance tracking knows exactly which address to credit.
    assert len(transfers := events[3:]) == 6
    assert all(
        x.event_type == HistoryEventType.TRANSFER and
        x.event_subtype == HistoryEventSubType.NONE and
        x.group_identifier == group_identifier and
        x.timestamp == timestamp and
        len(getattr(x, BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY)) == 1
        for x in transfers
    )
    for output_address, output_amount in (
        (address4, FVal('0.00031546')),
        (address5, FVal('0.00313426')),
    ):  # each output is credited exactly what it received in the tx
        assert sum(
            (x.amount for x in transfers
             if getattr(x, BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY) == [output_address]),
            ZERO,
        ).is_close(output_amount, max_diff='1e-20')

    for input_address, input_amount in (
        (address1, FVal('0.00343890998903817126853036885692804793')),
        (address2, FVal('0.00000540500548091436573481557153597603')),
        (address3, FVal('0.00000540500548091436573481557153597603')),
    ):  # and each input sends out everything it put in, minus its fee share
        assert sum(
            (x.amount for x in transfers if x.location_label == input_address),
            ZERO,
        ).is_close(input_amount, max_diff='1e-20')


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [['1PJJygLB42VsaTgo2twFPgRT8CNz1bpGNE']])
@pytest.mark.parametrize('use_blockcypher', [True, False])
def test_p2pk(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
        use_blockcypher: bool,
) -> None:
    """This is an old tx that used P2PK instead of P2PKH and has no fee."""
    assert get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=(tx_id := '1db6251a9afce7025a2061a19e63c700dffc3bec368bd1883decfac353357a9d'),
        use_blockcypher=use_blockcypher,
        ) == [expected_event := HistoryEvent(
            group_identifier=f'{BTC_GROUP_IDENTIFIER_PREFIX}{tx_id}',
            sequence_index=0,
            timestamp=TimestampMS(1313042188000),
            location=Location.BITCOIN,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_BTC,
            amount=FVal('50'),
            location_label=btc_accounts[0],
            notes='Send 50 BTC to 15WvMGm9qG1wDb54TMcvgzZsfvz9KdxzoN',
        )]

    assert expected_event.serialize()['tx_ref'] == tx_id


@pytest.mark.parametrize('btc_accounts', [['bc1pdju7vpgsk7rz5s8kc9hukqr3z5nfe6457q2ysdx9jgpgjhhcmx8qjte9tm']])  # noqa: E501
def test_skip_unconfirmed_blockchain_info_txs(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that unconfirmed txs are skipped without affecting the processing of confirmed txs.
    Unlike the other apis we use, blockchain.info doesn't allow limiting to only confirmed txs.
    Mocks the api result to return one unconfirmed tx and one confirmed tx.
    """
    blockchain_info_response = """{"addresses":[{"address":"bc1pdju7vpgsk7rz5s8kc9hukqr3z5nfe6457q2ysdx9jgpgjhhcmx8qjte9tm","final_balance":29488,"n_tx":14,"total_received":366022,"total_sent":336534}],"wallet":{"final_balance":29488,"n_tx":14,"n_tx_filtered":14,"total_received":366022,"total_sent":336534},
    "txs":[
        {"hash":"f6bcea42da69ec935e13c29241f15a72e055219549403ffe1aef251a306581e6","ver":2,"vin_sz":2,"vout_sz":2,"size":312,"weight":846,"fee":423,"relayed_by":"0.0.0.0","lock_time":0,"tx_index":8110189530268861,"double_spend":false,"time":1754493540,"block_index":null,"block_height":null,"inputs":[{"sequence":4294967295,"witness":"01400ecb3c368d33b70b680f051462d9a682a3f293cfe7d6592961094263611ff90ce24778927f861b9b59e381ecce9560c8d51b8e9f524662c85c124715ff5b146b","script":"","index":0,"prev_out":{"type":0,"spent":true,"value":26084,"spending_outpoints":[{"tx_index":8110189530268861,"n":0}],"n":0,"tx_index":228530240517491,"script":"51206cb9e60510b7862a40f6c16fcb007115269ceab4f0144834c59202895ef8d98e","addr":"bc1pdju7vpgsk7rz5s8kc9hukqr3z5nfe6457q2ysdx9jgpgjhhcmx8qjte9tm"}},{"sequence":4294967295,"witness":"0140b40a01cc81b8ac749f4afa18d3bd7854039f498aa24e4584c3ac59ad4b714a36b6ea06b31c8b7df80d764907895336f984c49d3e6460b397a4e95aef50a32da4","script":"","index":1,"prev_out":{"type":0,"spent":true,"value":20000,"spending_outpoints":[{"tx_index":8110189530268861,"n":1}],"n":0,"tx_index":1648502504821630,"script":"51206cb9e60510b7862a40f6c16fcb007115269ceab4f0144834c59202895ef8d98e","addr":"bc1pdju7vpgsk7rz5s8kc9hukqr3z5nfe6457q2ysdx9jgpgjhhcmx8qjte9tm"}}],"out":[{"type":0,"spent":true,"value":44000,"spending_outpoints":[{"tx_index":6739226631653152,"n":0}],"n":0,"tx_index":8110189530268861,"script":"5120dc699bbaa6a0d1cd8a14aec20a27d9c3ade02fa63bff6b709d8db84c59f50c8b","addr":"bc1pm35ehw4x5rgumzs54mpq5f7ecwk7qtax80lkkuya3kuyck04pj9sy3clgm"},{"type":0,"spent":false,"value":1661,"spending_outpoints":[],"n":1,"tx_index":8110189530268861,"script":"51206cb9e60510b7862a40f6c16fcb007115269ceab4f0144834c59202895ef8d98e","addr":"bc1pdju7vpgsk7rz5s8kc9hukqr3z5nfe6457q2ysdx9jgpgjhhcmx8qjte9tm"}],"result":-44423,"balance":27850},
        {"hash":"821a49c9e315a03c7c7f2ab9f82d38caa622df7d331a11102af09bb0316fda2e","ver":2,"vin_sz":1,"vout_sz":2,"size":234,"weight":609,"fee":612,"relayed_by":"0.0.0.0","lock_time":0,"tx_index":1648502504821630,"double_spend":false,"time":1754493473,"block_index":908880,"block_height":908880,"inputs":[{"sequence":4294967295,"witness":"02473044022071bbf6d314c51c53b24148db9d6f0022a37db519b0a2558455f0564c62741a8e02203e6c0c55076f181f732e4233c354af431953db40867b6c5126e172c38446a4ea012103d785c33d1624ea6113949c58ce4c1d459f16c4d25aeeacf040bd86ed1164d1ab","script":"","index":0,"prev_out":{"type":0,"spent":true,"value":49593,"spending_outpoints":[{"tx_index":1648502504821630,"n":0}],"n":3,"tx_index":920394186050089,"script":"00149f16a0e067f24307f39b373f6c498e71043d0b02","addr":"bc1qnut2pcr87fps0uumxulkcjvwwyzr6zczenmd4r"}}],"out":[{"type":0,"spent":true,"value":20000,"spending_outpoints":[{"tx_index":8110189530268861,"n":1}],"n":0,"tx_index":1648502504821630,"script":"51206cb9e60510b7862a40f6c16fcb007115269ceab4f0144834c59202895ef8d98e","addr":"bc1pdju7vpgsk7rz5s8kc9hukqr3z5nfe6457q2ysdx9jgpgjhhcmx8qjte9tm"}],"result":20000,"balance":72273}
    ],"info":{"nconnected":4,"conversion":100000000,"symbol_local":{"code":"USD","symbol":"XXX","name":"U.S.dollar","conversion":"+inf","symbolAppearsAfter":false,"local":true},"symbol_btc":{"code":"BTC","symbol":"BTC","name":"Bitcoin","conversion":100000000,"symbolAppearsAfter":true,"local":false},"latest_block":{"hash":"00000000000000000000e97a137c2a12a9f098fb840c2212d1c70ea394ab979b","height":908880,"time":1754493565,"block_index":908880}},"recommend_include_fee":true}
    """  # noqa: E501
    with patch('rotkehlchen.chain.bitcoin.manager.requests.get', return_value=MockResponse(200, blockchain_info_response)):  # noqa: E501
        bitcoin_manager.query_transactions(
            from_timestamp=Timestamp(0),
            to_timestamp=ts_now(),
            addresses=btc_accounts,
        )

    with bitcoin_manager.database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(bitcoin_manager.database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    # Check that there is only one event present and that it's from the confirmed tx.
    assert len(events) == 1
    assert '821a49c9e315a03c7c7f2ab9f82d38caa622df7d331a11102af09bb0316fda2e' in events[0].group_identifier  # noqa: E501


# Real mainnet transaction from block 700000. Two inputs pay 0.01 BTC to an external address
# and send the remainder back to a change address, which is the shape an xpub wallet produces
# when spending to an exchange.
CHANGE_TX_ID = '3281f96f3c458a4bee6248d6667c45e8481f51f4f79b878faedbf2e385dfdb95'
CHANGE_TX_INPUT1 = string_to_btc_address('bc1qdlt2jrplkf0v7ucvhhjhs0qf7cqr0j27k7j7p0')
CHANGE_TX_INPUT2 = string_to_btc_address('bc1q5242kk7ut5nkyv74g765amvwqnglrya6xgj6mz')
CHANGE_TX_EXTERNAL_OUTPUT = string_to_btc_address('3CXosf9wCHdSkGieziJ4BVg8g9HpwbX45t')
CHANGE_TX_CHANGE_OUTPUT = string_to_btc_address('bc1qm4lpczdpkcs6j4twpzd2lgguy0sd8zzsm6puhl')
CHANGE_TX_GROUP_IDENTIFIER = f'{BTC_GROUP_IDENTIFIER_PREFIX}{CHANGE_TX_ID}'
CHANGE_TX_FEE = FVal('0.0003135')
CHANGE_TX_EXTERNAL_AMOUNT = FVal('0.01')
CHANGE_TX_CHANGE_AMOUNT = FVal('0.02543836')


def _sum_amounts(
        events: Sequence[HistoryBaseEntry],
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType = HistoryEventSubType.NONE,
) -> FVal:
    return sum(
        (x.amount for x in events
         if x.event_type == event_type and x.event_subtype == event_subtype),
        ZERO,
    )


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [[
    'bc1qdlt2jrplkf0v7ucvhhjhs0qf7cqr0j27k7j7p0',
    'bc1q5242kk7ut5nkyv74g765amvwqnglrya6xgj6mz',
    'bc1qm4lpczdpkcs6j4twpzd2lgguy0sd8zzsm6puhl',
]])
def test_change_output_is_not_double_counted(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Both inputs and the change output belong to the wallet, as happens with an xpub.

    The change must never surface as a receive. Doing so reports a disposal of the whole
    input and an acquisition of the change that never happened, which corrupts cost basis
    even though the net balance stays correct.
    """
    events = get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=CHANGE_TX_ID,
    )
    # Only the amount actually leaving the wallet is a spend, and it goes to the external
    # address alone. The change stays inside the wallet, so it is a balance-only transfer.
    assert _sum_amounts(events, HistoryEventType.SPEND) == CHANGE_TX_EXTERNAL_AMOUNT
    assert _sum_amounts(events, HistoryEventType.TRANSFER) == CHANGE_TX_CHANGE_AMOUNT
    assert _sum_amounts(events, HistoryEventType.SPEND, HistoryEventSubType.FEE) == CHANGE_TX_FEE
    assert _sum_amounts(events, HistoryEventType.RECEIVE) == ZERO

    for event in events:
        if event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE:  # noqa: E501
            assert getattr(event, BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY) == [CHANGE_TX_EXTERNAL_OUTPUT]  # noqa: E501
        elif event.event_type == HistoryEventType.TRANSFER:
            # a single counterparty per transfer so balance tracking knows which
            # address to credit
            assert getattr(event, BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY) == [CHANGE_TX_CHANGE_OUTPUT]  # noqa: E501

    # The wallet's net position must equal what it actually lost on chain.
    assert (
        _sum_amounts(events, HistoryEventType.RECEIVE) -
        _sum_amounts(events, HistoryEventType.SPEND) -
        _sum_amounts(events, HistoryEventType.SPEND, HistoryEventSubType.FEE)
    ) == -(CHANGE_TX_EXTERNAL_AMOUNT + CHANGE_TX_FEE)


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [[
    'bc1qdlt2jrplkf0v7ucvhhjhs0qf7cqr0j27k7j7p0',
    'bc1q5242kk7ut5nkyv74g765amvwqnglrya6xgj6mz',
    '3CXosf9wCHdSkGieziJ4BVg8g9HpwbX45t',
    'bc1qm4lpczdpkcs6j4twpzd2lgguy0sd8zzsm6puhl',
]])
def test_fully_internal_tx_only_costs_the_fee(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """When every output is owned the tx is a consolidation/self transfer.
    It must cost the wallet the fee and nothing else - no spend and no receive.
    """
    events = get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=CHANGE_TX_ID,
    )
    assert _sum_amounts(events, HistoryEventType.SPEND) == ZERO
    assert _sum_amounts(events, HistoryEventType.RECEIVE) == ZERO
    assert _sum_amounts(events, HistoryEventType.SPEND, HistoryEventSubType.FEE) == CHANGE_TX_FEE
    assert _sum_amounts(events, HistoryEventType.TRANSFER) == (
        CHANGE_TX_EXTERNAL_AMOUNT + CHANGE_TX_CHANGE_AMOUNT
    )


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [['bc1qm4lpczdpkcs6j4twpzd2lgguy0sd8zzsm6puhl']])
def test_receive_only_tx_is_not_charged_a_fee(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """The wallet owns none of the inputs, so the sender paid the fee.
    Only the received amount should be recorded.
    """
    events = get_decoded_events_of_bitcoin_tx(
        bitcoin_manager=bitcoin_manager,
        tx_id=CHANGE_TX_ID,
    )
    assert _sum_amounts(events, HistoryEventType.RECEIVE) == CHANGE_TX_CHANGE_AMOUNT
    assert _sum_amounts(events, HistoryEventType.SPEND) == ZERO
    assert _sum_amounts(events, HistoryEventType.SPEND, HistoryEventSubType.FEE) == ZERO
    assert _sum_amounts(events, HistoryEventType.TRANSFER) == ZERO


@pytest.mark.vcr
@pytest.mark.parametrize('btc_accounts', [['bc1qdlt2jrplkf0v7ucvhhjhs0qf7cqr0j27k7j7p0']])
def test_redecoding_after_tracking_more_accounts(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Query the tx with only one address tracked, then again after the rest of the wallet
    is added, as happens when an xpub is added after a standalone address.

    Sequence indexes are positional, so the second decode used to collide with the stale
    events under UNIQUE(group_identifier, sequence_index). That silently kept outdated rows
    and dropped the corrected ones, leaving duplicated spends and missing fee events.
    """
    def query_and_get_tx_events(accounts: list[BTCAddress]) -> list[HistoryBaseEntry]:
        """Query the given accounts and return only the events of the change tx."""
        bitcoin_manager.query_transactions(
            from_timestamp=Timestamp(0),
            to_timestamp=ts_now(),
            addresses=accounts,
        )
        with bitcoin_manager.database.conn.read_ctx() as cursor:
            return [
                x for x in DBHistoryEvents(bitcoin_manager.database).get_history_events_internal(
                    cursor=cursor,
                    filter_query=HistoryEventFilterQuery.make(),
                ) if x.group_identifier == CHANGE_TX_GROUP_IDENTIFIER
            ]

    assert len(query_and_get_tx_events(btc_accounts)) == 2  # one fee event and one spend event

    with bitcoin_manager.database.user_write() as write_cursor:
        bitcoin_manager.database.add_blockchain_accounts(
            write_cursor=write_cursor,
            account_data=[
                BlockchainAccountData(chain=SupportedBlockchain.BITCOIN, address=x)
                for x in (CHANGE_TX_INPUT2, CHANGE_TX_CHANGE_OUTPUT)
            ],
        )

    events = query_and_get_tx_events(
        accounts=[*btc_accounts, CHANGE_TX_INPUT2, CHANGE_TX_CHANGE_OUTPUT],
    )

    # No leftovers from the first decode: two fees, two spends and two transfers.
    assert len(events) == 6
    assert len({x.sequence_index for x in events}) == len(events)  # no duplicate indexes
    assert _sum_amounts(events, HistoryEventType.SPEND, HistoryEventSubType.FEE) == CHANGE_TX_FEE
    assert _sum_amounts(events, HistoryEventType.SPEND) == CHANGE_TX_EXTERNAL_AMOUNT
    assert _sum_amounts(events, HistoryEventType.TRANSFER) == CHANGE_TX_CHANGE_AMOUNT
    assert _sum_amounts(events, HistoryEventType.RECEIVE) == ZERO


@pytest.mark.parametrize('btc_accounts', [[CHANGE_TX_INPUT1]])
def test_transactions_are_saved_and_redecoded_offline(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that queried transactions are saved and can be decoded again without querying
    the explorers, which is what makes correcting a decoding mistake possible at all.
    """
    bitcoin_manager.query_transactions(
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        addresses=btc_accounts,
    )
    dbevents, dbtx = DBHistoryEvents(bitcoin_manager.database), bitcoin_manager.dbtx
    with bitcoin_manager.database.conn.read_ctx() as cursor:
        saved_txs = dbtx.get_transactions(cursor=cursor, location=Location.BITCOIN)
        original_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )
        # everything queried is saved, decoded and associated with the address it came from
        assert len(saved_txs) > 0
        assert dbtx.count_undecoded_transactions(cursor=cursor, location=Location.BITCOIN) == 0
        assert dbtx.get_transaction_ids_for_address(
            cursor=cursor,
            location=Location.BITCOIN,
            address=btc_accounts[0],
        ) != []
        assert (change_tx := next(
            x for x in saved_txs if x.tx_id == CHANGE_TX_ID
        )).is_complete is True
        assert {x.address for x in change_tx.outputs} == {
            CHANGE_TX_EXTERNAL_OUTPUT,
            CHANGE_TX_CHANGE_OUTPUT,
        }

    with patch.object(  # any explorer query during the redecode must fail the test
        bitcoin_manager,
        '_query',
        side_effect=AssertionError('Redecoding should not query the explorers'),
    ):
        assert bitcoin_manager.redecode_transactions() == len(saved_txs)

    with bitcoin_manager.database.conn.read_ctx() as cursor:
        redecoded_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    assert len(redecoded_events) == len(original_events)
    for redecoded, original in zip(redecoded_events, original_events, strict=True):
        assert redecoded.group_identifier == original.group_identifier
        assert redecoded.sequence_index == original.sequence_index
        assert redecoded.amount == original.amount
        assert redecoded.notes == original.notes


@pytest.mark.parametrize('btc_accounts', [[CHANGE_TX_INPUT1]])
def test_saved_transaction_completed_by_a_second_partial_view(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that two partial views of the same transaction complete each other instead of
    duplicating rows. blockchain.info returns only the TxIOs touching the queried addresses,
    so a transaction saved for one address may be missing the TxIOs of another.
    """
    def make_tx(outputs: list[BtcTxIO]) -> BitcoinTx:
        return BitcoinTx(
            tx_id=CHANGE_TX_ID,
            timestamp=Timestamp(1700000000),
            block_height=1,
            fee=CHANGE_TX_FEE,
            inputs=[BtcTxIO(
                value=FVal('0.03'),
                script=b'\x01',
                address=CHANGE_TX_INPUT1,
                direction=BtcTxIODirection.INPUT,
                io_index=0,
            )],
            outputs=outputs,
            vin_count=1,
            vout_count=2,
        )

    external_output = BtcTxIO(
        value=CHANGE_TX_EXTERNAL_AMOUNT,
        script=b'\x02',
        address=CHANGE_TX_EXTERNAL_OUTPUT,
        direction=BtcTxIODirection.OUTPUT,
        io_index=0,
    )
    change_output = BtcTxIO(
        value=CHANGE_TX_CHANGE_AMOUNT,
        script=b'\x03',
        address=CHANGE_TX_CHANGE_OUTPUT,
        direction=BtcTxIODirection.OUTPUT,
        io_index=1,
    )
    dbtx = bitcoin_manager.dbtx
    with bitcoin_manager.database.conn.write_ctx() as write_cursor:
        assert dbtx.add_transactions(  # only the change output is known at first
            write_cursor=write_cursor,
            transactions=[make_tx(outputs=[change_output])],
            location=Location.BITCOIN,
            relevant_addresses=[CHANGE_TX_INPUT1],
        ) == {CHANGE_TX_ID}

    with bitcoin_manager.database.conn.read_ctx() as cursor:
        assert (saved := dbtx.get_transactions(
            cursor=cursor,
            location=Location.BITCOIN,
        )[0]).is_complete is False
        assert saved.multi_io is False  # only one input, so it is still a single-to-many
        assert saved.outputs == [change_output]

    with bitcoin_manager.database.conn.write_ctx() as write_cursor:
        assert dbtx.add_transactions(  # the other output arrives with another address' query
            write_cursor=write_cursor,
            transactions=[make_tx(outputs=[external_output, change_output])],
            location=Location.BITCOIN,
            relevant_addresses=[CHANGE_TX_CHANGE_OUTPUT],
        ) == {CHANGE_TX_ID}

    with bitcoin_manager.database.conn.read_ctx() as cursor:
        assert (saved := dbtx.get_transactions(
            cursor=cursor,
            location=Location.BITCOIN,
        )[0]).is_complete is True
        assert saved.outputs == [external_output, change_output]
        assert saved.fee == CHANGE_TX_FEE  # amounts survive the satoshi roundtrip
        # gaining a TxIO makes the events decoded from the incomplete copy outdated
        assert dbtx.count_undecoded_transactions(cursor=cursor, location=Location.BITCOIN) == 1


@pytest.mark.parametrize('btc_accounts', [[CHANGE_TX_INPUT1, CHANGE_TX_CHANGE_OUTPUT]])
def test_removing_an_address_keeps_shared_transactions(
        bitcoin_manager: BitcoinManager,
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that removing an address only deletes the transactions no other tracked address
    was queried for.
    """
    bitcoin_manager.query_transactions(
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        addresses=btc_accounts,
    )
    database, dbtx = bitcoin_manager.database, bitcoin_manager.dbtx
    with database.conn.read_ctx() as cursor:
        assert CHANGE_TX_ID in {  # the change tx was queried for both addresses
            x.tx_id for x in dbtx.get_transactions(cursor=cursor, location=Location.BITCOIN)
        }

    with database.user_write() as write_cursor:
        database.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            accounts=[CHANGE_TX_CHANGE_OUTPUT],
        )

    with database.conn.read_ctx() as cursor:
        saved_tx_ids = {
            x.tx_id for x in dbtx.get_transactions(cursor=cursor, location=Location.BITCOIN)
        }
        assert CHANGE_TX_ID in saved_tx_ids  # still needed by the address left tracking it

    with database.user_write() as write_cursor:
        database.remove_single_blockchain_accounts(
            write_cursor=write_cursor,
            blockchain=SupportedBlockchain.BITCOIN,
            accounts=[CHANGE_TX_INPUT1],
        )

    with database.conn.read_ctx() as cursor:
        assert dbtx.get_transactions(cursor=cursor, location=Location.BITCOIN) == []
        assert DBHistoryEvents(database).get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(location=Location.BITCOIN),
        ) == []
