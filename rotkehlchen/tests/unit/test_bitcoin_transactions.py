import pytest

from rotkehlchen.chain.bitcoin.manager import BitcoinManager
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventType, HistoryEventSubType
from rotkehlchen.tests.utils.bitcoin import get_decoded_events_of_bitcoin_tx
from rotkehlchen.types import BTCAddress, Timestamp, TimestampMS, Location
from rotkehlchen.utils.misc import ts_now


@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
def test_query_txs(bitcoin_manager: 'BitcoinManager', btc_accounts: list[BTCAddress]) -> None:

    bitcoin_manager.query_transactions(
        from_timestamp=Timestamp(0),
        to_timestamp=ts_now(),
        addresses=btc_accounts,
    )

    with bitcoin_manager.database.conn.read_ctx() as cursor:
        events = DBHistoryEvents(bitcoin_manager.database).get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
            ),
            has_premium=True,
        )

    return
    last_id = events[0].event_identifier
    for event in events:
        if event.event_identifier != last_id:
            print('------')
        print([event])
        last_id = event.event_identifier


@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4', '1G3MiaKdccQmiTr4gYSKmrCVDaLQ5nvBRp']])
def test_decode_p2pkh_p2wpkh_tx(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = 'e47f43692083b6b4bb3d4d6150acd3c016b09fb841e4055e1f5bb8ad44858bc6'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    assert events == [HistoryEvent(
        event_identifier=(event_identifier := f'btc_{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1686238076000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00002492')),
        location_label=(user_address := btc_accounts[0]),
        notes=f'Burn {fee_amount} BTC for gas',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.TRANSFER,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=(transfer_amount := FVal('0.00001437')),
        location_label=user_address,
        notes=f'Transfer {transfer_amount} BTC from {user_address} to {btc_accounts[1]}',
    )]


@pytest.mark.parametrize('btc_accounts', [['bc1qyy30guv6m5ez7ntj0ayr08u23w3k5s8vg3elmxdzlh8a3xskupyqn2lp5w']])  # noqa: E501
def test_decode_p2wsh_tx(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = '4a367acdeeaaf4bca2d9ae81d4cf4c42ac0f8131f52dc53222ff17189e2099b1'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)

    for event in events:
        print('------')
        print([event])


@pytest.mark.parametrize('btc_accounts', [['bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4']])
def test_op_return(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = 'eb4d2def800c4993928a6f8cc3dd350933a1fb71e6706902025f29a061e5547f'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)
    assert events == [HistoryEvent(
        event_identifier=(event_identifier := f'btc_{tx_id}'),
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1729677861000)),
        location=Location.BITCOIN,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BTC,
        amount=(fee_amount := FVal('0.00001000')),
        location_label=btc_accounts[0],
        notes=f'Burn {fee_amount} BTC for gas',
    ), HistoryEvent(
        event_identifier=event_identifier,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BITCOIN,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_BTC,
        amount=ZERO,
        notes='Store text on the blockchain: #FreeSamourai'
    )]


@pytest.mark.parametrize('btc_accounts', [['bc1qyy30guv6m5ez7ntj0ayr08u23w3k5s8vg3elmxdzlh8a3xskupyqn2lp5w']])  # noqa: E501
def test_p2tr(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = '67c97abe049b671a02e537eb901cd600430ddaa5b09b50434969e360ada748bf'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)

    for event in events:
        print('------')
        print([event])


@pytest.mark.parametrize('btc_accounts', [['17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf']])  # noqa: E501
def test_1in2out_sender_tracked(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = '450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)

    '''
    [HistoryEvent(self.event_identifier='btc_450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144', self.sequence_index=0, self.timestamp=1339247930000, self.location=<Location.BITCOIN: 49>, self.event_type=<HistoryEventType.SPEND: 5>, self.event_subtype=<HistoryEventSubType.FEE: 3>, self.asset=<Asset identifier:BTC>, self.amount=FVal(0.01000000), self.location_label='17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf', self.notes='Burn 0.01000000 BTC for gas', self.identifier=None, self.extra_data=None)]
    ------
    [HistoryEvent(self.event_identifier='btc_450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144', self.sequence_index=0, self.timestamp=1339247930000, self.location=<Location.BITCOIN: 49>, self.event_type=<HistoryEventType.SPEND: 5>, self.event_subtype=<HistoryEventSubType.NONE: 10>, self.asset=<Asset identifier:BTC>, self.amount=FVal(0.56196218), self.location_label=None, self.notes='Send 0.56196218 BTC from 17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf to 17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy', self.identifier=None, self.extra_data=None)]
    ------
    [HistoryEvent(self.event_identifier='btc_450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144', self.sequence_index=0, self.timestamp=1339247930000, self.location=<Location.BITCOIN: 49>, self.event_type=<HistoryEventType.SPEND: 5>, self.event_subtype=<HistoryEventSubType.NONE: 10>, self.asset=<Asset identifier:BTC>, self.amount=FVal(0.10000000), self.location_label=None, self.notes='Send 0.10000000 BTC from 17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf to 3CK4fEwbMP7heJarmU4eqA3sMbVJyEnU3V', self.identifier=None, self.extra_data=None)]
    '''
    for event in events:
        print('------')
        print([event])


@pytest.mark.parametrize('btc_accounts', [['17GZv9cYySVCW1TgvQ77CZUnMrfUFEukDf', '17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy']])
def test_1in2out_sender_and_a_receiver_tracked(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = '450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)

    for event in events:
        print('------')
        print([event])


@pytest.mark.parametrize('btc_accounts', [['17AkKFFZmMJgvvuwT2tJbSv149us1ya1cy']])
def test_1in2out_single_receiver_tracked(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = '450c309b70fb3f71b63b10ce60af17499bd21b1db39aa47b19bf22166ee67144'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)

    for event in events:
        print('------')
        print([event])


@pytest.mark.parametrize('btc_accounts', [['bc1qyy30guv6m5ez7ntj0ayr08u23w3k5s8vg3elmxdzlh8a3xskupyqn2lp5w']])
def test_x(
        bitcoin_manager: 'BitcoinManager',
        btc_accounts: list[BTCAddress],
) -> None:
    tx_id = '4a367acdeeaaf4bca2d9ae81d4cf4c42ac0f8131f52dc53222ff17189e2099b1'
    events = get_decoded_events_of_bitcoin_tx(bitcoin_manager=bitcoin_manager, tx_id=tx_id)

    for event in events:
        print('------')
        print([event])