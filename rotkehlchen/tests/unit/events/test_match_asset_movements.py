from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.constants import HOUR_IN_SECONDS
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_USD, A_USDC
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
)
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.events import match_asset_movements
from rotkehlchen.tests.fixtures import MockedWsMessage
from rotkehlchen.tests.utils.factories import (
    make_evm_address,
    make_evm_tx_hash,
    make_solana_address,
    make_solana_signature,
)
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_asset_movements(database: 'DBHandler') -> None:
    """Test that the asset movement matching logic works correctly.

    Adds some test events to the DB, runs the matching, and checks that events were properly
    matched and updated. Then runs the matching again to check that already matched events
    are properly excluded from subsequent matching.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(  # deposit1, Fiat, should be ignored.
                location=Location.GEMINI,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1500000000000),
                asset=A_USD,
                amount=FVal('100'),
                unique_id='1',
                location_label='Gemini 1',
            ), (deposit2 := AssetMovement(  # deposit2, two matches, one with tx ref
                location=Location.GEMINI,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='2',
                extra_data={'transaction_id': str(tx_ref := make_evm_tx_hash())},
                location_label='Gemini 2',
            )), EvmEvent(  # deposit2's matched event, same tx ref
                tx_ref=tx_ref,
                sequence_index=0,
                timestamp=TimestampMS(deposit2.timestamp - 60000),  # timestamp differs some but is < 1 hour different.  # noqa: E501
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.1'),
                location_label=(deposit2_user_address := make_evm_address()),
            ), (deposit_2_wrong_ref_event := EvmEvent(  # deposit2 similar event, wrong tx ref
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=deposit2.timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.1'),
            )), (withdrawal1 := AssetMovement(  # withdrawal1, with matched event
                location=Location.COINBASE,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1520000000000),
                asset=A_USDC,
                amount=FVal('0.2'),
                unique_id='3',
                location_label='Coinbase 1',
            )), EvmEvent(  # withdrawal1's matched event, already a deposit/deposit_asset, but notes and counterparty will be updated.  # noqa: E501
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=withdrawal1.timestamp,
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_USDC,
                amount=FVal('0.2'),
                location_label=(withdrawal1_user_address := make_evm_address()),
            ), (withdrawal1_wrong_amount_event := EvmEvent(  # similar to withdrawal1's matched event, but the amount is wrong  # noqa: E501
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=withdrawal1.timestamp,
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_USDC,
                amount=FVal('0.21'),
            )), (withdrawal1_wrong_ts_event := EvmEvent(  # similar to withdrawal1's matched event, but timestamp > 1 hour away  # noqa: E501
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(withdrawal1.timestamp + ts_sec_to_ms(Timestamp(HOUR_IN_SECONDS)) * 2),  # noqa: E501
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_USDC,
                amount=FVal('0.2'),
            )), (withdrawal2 := AssetMovement(  # withdrawal2, with two similar events
                location=Location.KRAKEN,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1530000000000),
                asset=A_USDC,
                amount=FVal('0.3'),
                unique_id='4',
                location_label='Kraken 1',
            )), EvmEvent(  # withdrawal2 possible event 1
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=withdrawal2.timestamp,
                location=Location.BASE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('0.3'),
            ), EvmEvent(  # withdrawal2 possible event 2
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=withdrawal2.timestamp,
                location=Location.BASE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('0.3'),
            ), (withdrawal3 := AssetMovement(  # withdrawal3, no matched events
                location=Location.BYBIT,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1540000000000),
                asset=A_BTC,
                amount=FVal('0.4'),
                unique_id='5',
                location_label='Bybit 1',
            )), (deposit3 := AssetMovement(  # deposit3, with fee
                location=Location.BYBIT,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1550000000000),
                asset=A_USDC,
                amount=FVal('99'),
                unique_id='6',
                location_label='Bybit 1',
            )), AssetMovement(  # deposit3 fee
                location=Location.BYBIT,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1550000000000),
                asset=A_USDC,
                amount=FVal('1'),
                unique_id='6',
                location_label='Bybit 1',
                is_fee=True,
            ), SolanaEvent(  # deposit3 match, amount includes fee
                tx_ref=make_solana_signature(),
                sequence_index=0,
                timestamp=TimestampMS(1550000000000),
                location=Location.SOLANA,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('100'),
                location_label=(deposit3_user_address := make_solana_address()),
            ), (withdrawal4 := AssetMovement(  # withdrawal4, with another asset movement for the matched event  # noqa: E501
                location=Location.BITSTAMP,
                event_type=HistoryEventType.WITHDRAWAL,
                timestamp=TimestampMS(1560000000000),
                asset=A_USDC,
                amount=FVal('0.3'),
                unique_id='7',
                location_label='Bitstamp 1',
            )), (withdrawal4_matched_event := AssetMovement(  # withdrawal4's matched event
                location=Location.KUCOIN,
                event_type=HistoryEventType.DEPOSIT,
                timestamp=TimestampMS(1560000000001),
                asset=A_USDC,
                amount=FVal('0.3'),
                unique_id='8',
                location_label='Kucoin 1',
            ))],
        )

    match_asset_movements(database=database)

    with database.conn.read_ctx() as cursor:
        all_events = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    asset_movements = [event for event in all_events if isinstance(event, AssetMovement)]
    events = [event for event in all_events if isinstance(event, OnchainEvent)]

    assert len(events) == 8
    # Corresponding event for deposit2
    assert (deposit2_matched_event := events[0]).event_type == HistoryEventType.WITHDRAWAL
    assert deposit2_matched_event.event_subtype == HistoryEventSubType.REMOVE_ASSET
    assert deposit2_matched_event.notes == f'Withdraw 0.1 ETH from {deposit2_user_address} to Gemini 2'  # noqa: E501
    assert deposit2_matched_event.counterparty == Location.GEMINI.name.lower()
    # Second event matching deposit2 but with the wrong ref. Unmodified.
    # (except for identifier since its from the db here)
    deposit_2_wrong_ref_event.identifier = events[1].identifier
    assert events[1] == deposit_2_wrong_ref_event
    # Corresponding event for withdrawal1
    assert (withdrawal1_matched_event := events[2]).event_type == HistoryEventType.DEPOSIT
    assert withdrawal1_matched_event.event_subtype == HistoryEventSubType.DEPOSIT_ASSET
    assert withdrawal1_matched_event.notes == f'Deposit 0.2 USDC to {withdrawal1_user_address} from Coinbase 1'  # noqa: E501
    assert withdrawal1_matched_event.counterparty == Location.COINBASE.name.lower()
    # Second event matching withdrawal1 but with the wrong amount. Unmodified.
    withdrawal1_wrong_amount_event.identifier = events[3].identifier
    assert events[3] == withdrawal1_wrong_amount_event
    # Third event matching withdrawal1 but with the wrong timestamp. Unmodified.
    withdrawal1_wrong_ts_event.identifier = events[4].identifier
    assert events[4] == withdrawal1_wrong_ts_event
    # The next two events are related to withdrawal2,
    # but neither are modified since both match.
    assert all(event.notes is None for event in events[5:7])
    # Corresponding event for deposit3
    assert (deposit3_matched_event := events[7]).event_type == HistoryEventType.WITHDRAWAL
    assert deposit3_matched_event.event_subtype == HistoryEventSubType.REMOVE_ASSET
    assert deposit3_matched_event.notes == f'Withdraw 100 USDC from {deposit3_user_address} to Bybit 1'  # noqa: E501
    assert deposit3_matched_event.counterparty == Location.BYBIT.name.lower()

    withdrawal4_matched_event.identifier = asset_movements[-1].identifier
    withdrawal4_matched_event.extra_data = AssetMovementExtraData(matched_asset_movement={
        'group_identifier': withdrawal4.group_identifier,
        'exchange': 'bitstamp',
        'exchange_name': 'Bitstamp 1',
    })
    assert asset_movements[-1] == withdrawal4_matched_event

    # Check that matches have been cached and that the cached identifiers
    # refer to the correct asset movements
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT * FROM key_value_cache WHERE name LIKE ?',
            ('matched_asset_movement_%',),
        ).fetchall() == [
            (f'matched_asset_movement_{deposit2_matched_event.identifier}', str(deposit_2_identifier := 2)),  # noqa: E501
            (f'matched_asset_movement_{withdrawal1_matched_event.identifier}', str(withdrawal_1_identifier := 5)),  # noqa: E501
            (f'matched_asset_movement_{deposit3_matched_event.identifier}', str(deposit_3_identifier := 13)),  # noqa: E501
            (f'matched_asset_movement_{withdrawal4_matched_event.identifier}', str(withdrawal4_identifier := 16)),  # noqa: E501
            (f'matched_asset_movement_{withdrawal4_identifier}', str(withdrawal4_matched_event.identifier)),  # noqa: E501
        ]
        matched_asset_movements = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[
                deposit_2_identifier,
                withdrawal_1_identifier,
                deposit_3_identifier,
                withdrawal4_identifier,
            ]),
        )
    assert len(matched_asset_movements) == 4
    deposit2.identifier = deposit_2_identifier
    assert matched_asset_movements[0] == deposit2
    withdrawal1.identifier = withdrawal_1_identifier
    assert matched_asset_movements[1] == withdrawal1
    deposit3.identifier = deposit_3_identifier
    assert matched_asset_movements[2] == deposit3
    # since withdrawal4 is part of an exchange to exchange movement, it is also the matched event
    # for the other asset movement and has the matched_asset_movement extra data.
    withdrawal4.extra_data = AssetMovementExtraData(matched_asset_movement={
        'group_identifier': withdrawal4_matched_event.group_identifier,
        'exchange': 'kucoin',
        'exchange_name': 'Kucoin 1',
    })
    withdrawal4.identifier = withdrawal4_identifier
    assert matched_asset_movements[3] == withdrawal4

    # Check that the unmatched movements ws message was sent
    assert database.msg_aggregator.rotki_notifier.pop_message() == MockedWsMessage(  # type: ignore  # pop_message will be present since it's a MockRotkiNotifier
        message_type=WSMessageType.UNMATCHED_ASSET_MOVEMENTS,
        data={'count': 2},
    )

    # Check that the matching logic is now only run for unmatched asset movements
    with patch('rotkehlchen.tasks.events._find_asset_movement_match', return_value=None) as find_match_mock:  # noqa: E501
        match_asset_movements(database=database)

    assert find_match_mock.call_count == 2
    withdrawal2.identifier = 9
    assert find_match_mock.call_args_list[0].kwargs['asset_movement'] == withdrawal2
    withdrawal3.identifier = 12
    assert find_match_mock.call_args_list[1].kwargs['asset_movement'] == withdrawal3
