from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.constants import HOUR_IN_SECONDS, ONE
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BTC,
    A_DAI,
    A_ETH,
    A_GNO,
    A_SAI,
    A_USD,
    A_USDC,
    A_WETH_OPT,
    A_WSOL,
)
from rotkehlchen.constants.timing import SAI_DAI_MIGRATION_TS
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import (
    DEFAULT_ASSET_MOVEMENT_TIME_RANGE,
    ModifiableDBSettings,
)
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.asset_movement import (
    AssetMovement,
    AssetMovementExtraData,
    AssetMovementSubtype,
)
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks import events as task_events
from rotkehlchen.tasks.events import match_asset_movements
from rotkehlchen.tests.fixtures import MockedWsMessage
from rotkehlchen.tests.unit.test_eth2 import HOUR_IN_MILLISECONDS
from rotkehlchen.tests.utils.factories import (
    make_evm_address,
    make_evm_tx_hash,
    make_solana_address,
    make_solana_signature,
)
from rotkehlchen.types import ChecksumEvmAddress, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


def _match_and_check(database: 'DBHandler', expected_matches: list[tuple[int, int]]) -> None:
    """Helper function for testing that the expected events are properly matched."""
    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall()) == set(expected_matches)


def _get_match_for_movement(cursor: 'DBCursor', movement_id: int | None) -> int | None:
    """Helper function to check the id of the event matched with a movement."""
    return None if (result := cursor.execute(
        'SELECT right_event_id FROM history_event_links WHERE link_type=? AND left_event_id=?',
        (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(), movement_id),
    ).fetchone()) is None else result[0]


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
            history=[AssetMovement(  # deposit1, Fiat, should be auto ignored
                location=Location.GEMINI,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1500000000000),
                asset=A_USD,
                amount=FVal('100'),
                unique_id='1',
                location_label='Gemini 1',
            ), (deposit2 := AssetMovement(  # deposit2, two matches, one with tx ref
                location=Location.GEMINI,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1510000000000),
                asset=A_ETH,
                amount=FVal('0.1'),
                unique_id='2',
                extra_data=AssetMovementExtraData(
                    blockchain='eth',
                    transaction_id=str(tx_ref := make_evm_tx_hash()),
                ),
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
                counterparty=CPT_MONERIUM,
                notes='Important info',
                location_label=make_evm_address(),
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
                event_subtype=HistoryEventSubType.SPEND,
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
            )), (withdrawal1_wrong_ts_event := EvmEvent(  # similar to withdrawal1's matched event, but timestamp is farther away than the time range  # noqa: E501
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(withdrawal1.timestamp + ts_sec_to_ms(Timestamp(DEFAULT_ASSET_MOVEMENT_TIME_RANGE + 1))),  # noqa: E501
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_USDC,
                amount=FVal('0.2'),
            )), (withdrawal2 := AssetMovement(  # withdrawal2, with two similar events
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
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
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1540000000000),
                asset=A_BTC,
                amount=FVal('0.4'),
                unique_id='5',
                location_label='Bybit 1',
            )), (deposit3 := AssetMovement(  # deposit3, with fee
                location=Location.BYBIT,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1550000000000),
                asset=A_USDC,
                amount=FVal('99'),
                unique_id='6',
            )), AssetMovement(  # deposit3 fee
                location=Location.BYBIT,
                event_subtype=HistoryEventSubType.FEE,
                timestamp=TimestampMS(1550000000000),
                asset=A_USDC,
                amount=ONE,
                unique_id='6',
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
            ), AssetMovement(  # deposit5, for blockchain that will have no transactions
                location=Location.GEMINI,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1555000000000),
                asset=A_ETH,
                amount=FVal('0.6'),
                unique_id='9',
                location_label='Gemini 1',
                extra_data=AssetMovementExtraData(blockchain='monero'),
            ), (withdrawal4 := AssetMovement(  # withdrawal4, with another asset movement for the matched event  # noqa: E501
                location=Location.BITSTAMP,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1560000000000),
                asset=A_USDC,
                amount=FVal('5.5'),
                unique_id='7',
                location_label='Bitstamp 1',
            )), (withdrawal4_matched_event := AssetMovement(  # withdrawal4's matched event
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1560000000001),
                asset=A_USDC,
                amount=FVal('5.49'),  # Slightly different amount but within the tolerance so will still auto match and add a fee event to cover the difference. # noqa: E501
                unique_id='8',
                location_label='Kraken 1',
            ))],
        )

    match_asset_movements(database=database)

    with database.conn.read_ctx() as cursor:
        all_events = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(order_by_rules=[
                ('timestamp', True),
                ('sequence_index', True),
                ('history_events_identifier', True),
            ]),
        )

    asset_movements = [
        event for event in all_events
        if isinstance(event, (AssetMovement, HistoryEvent))
    ]  # include plain history events so the adjustments are included.
    events = [event for event in all_events if isinstance(event, OnchainEvent)]

    assert len(events) == 8
    # Corresponding event for deposit2
    assert (deposit2_matched_event := events[0]).event_type == HistoryEventType.EXCHANGE_TRANSFER
    assert deposit2_matched_event.event_subtype == HistoryEventSubType.SPEND
    assert deposit2_matched_event.notes == 'Important info'  # Notes shouldn't be updated on monerium events.  # noqa: E501
    assert deposit2_matched_event.counterparty == Location.GEMINI.name.lower()
    # Second event matching deposit2 but with the wrong ref. Unmodified.
    # (except for identifier since its from the db here)
    deposit_2_wrong_ref_event.identifier = events[1].identifier
    assert events[1] == deposit_2_wrong_ref_event
    # Corresponding event for withdrawal1
    assert (withdrawal1_matched_event := events[2]).event_type == HistoryEventType.EXCHANGE_TRANSFER  # noqa: E501
    assert withdrawal1_matched_event.event_subtype == HistoryEventSubType.RECEIVE
    assert withdrawal1_matched_event.notes == f'Receive 0.2 USDC in {withdrawal1_user_address} from Coinbase 1'  # noqa: E501
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
    assert (deposit3_matched_event := events[7]).event_type == HistoryEventType.EXCHANGE_TRANSFER
    assert deposit3_matched_event.event_subtype == HistoryEventSubType.SPEND
    # Check that the note has been updated but doesn't include the 'to {exchange}' part since
    # deposit3 doesn't have a location_label set.
    assert deposit3_matched_event.notes == f'Send 100 USDC from {deposit3_user_address}'
    assert deposit3_matched_event.counterparty == Location.BYBIT.name.lower()

    # Last two events should be withdrawal4's matched event and a new adjustment event to cover the
    # difference between withdrawal4 and its matched event. Note that since the matched event is
    # also an asset movement in this case, the adjustment is actually added to the group of the
    # matched event since it gets processed first.
    withdrawal4_matched_event.identifier = asset_movements[-2].identifier
    withdrawal4_matched_event.extra_data = AssetMovementExtraData(matched_asset_movement={
        'group_identifier': withdrawal4.group_identifier,
        'exchange': 'bitstamp',
        'exchange_name': 'Bitstamp 1',
    })
    assert asset_movements[-2] == withdrawal4_matched_event
    assert (withdrawal4_adjustment := asset_movements[-1]).event_type == HistoryEventType.EXCHANGE_ADJUSTMENT  # noqa: E501
    assert withdrawal4_adjustment.event_subtype == HistoryEventSubType.RECEIVE
    assert withdrawal4_adjustment.group_identifier == withdrawal4_matched_event.group_identifier
    assert withdrawal4_adjustment.amount == withdrawal4.amount - withdrawal4_matched_event.amount

    # Check that matches have been cached and that the cached identifiers
    # refer to the correct asset movements
    deposit_1_identifier = 1
    deposit_2_identifier = 2
    withdrawal_1_identifier = 5
    deposit_3_identifier = 13
    deposit_4_identifier = 16
    withdrawal4_identifier = 17
    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall()) == {
            (withdrawal4_matched_event.identifier, withdrawal4_identifier),
            (withdrawal4_identifier, withdrawal4_matched_event.identifier),
            (deposit_3_identifier, deposit3_matched_event.identifier),
            (withdrawal_1_identifier, withdrawal1_matched_event.identifier),
            (deposit_2_identifier, deposit2_matched_event.identifier),
        }
        assert set(cursor.execute(
            'SELECT event_id FROM history_event_link_ignores WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall()) == {
            (deposit_4_identifier,),
            (deposit_1_identifier,),
        }
        matched_asset_movements = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[
                deposit_2_identifier,
                withdrawal_1_identifier,
                deposit_3_identifier,
                withdrawal4_identifier,
            ], order_by_rules=[('history_events_identifier', True)]),
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
        'exchange': 'kraken',
        'exchange_name': 'Kraken 1',
    })
    withdrawal4.identifier = withdrawal4_identifier
    assert matched_asset_movements[3] == withdrawal4

    # Check that the unmatched movements ws message was sent
    assert database.msg_aggregator.rotki_notifier.pop_message() == MockedWsMessage(  # type: ignore  # pop_message will be present since it's a MockRotkiNotifier
        message_type=WSMessageType.UNMATCHED_ASSET_MOVEMENTS,
        data={'count': (unmatched_count := 2)},
    )

    # Check that the matching logic is now only run for unmatched asset movements
    with patch('rotkehlchen.tasks.events.find_asset_movement_matches', return_value=[]) as find_match_mock:  # noqa: E501
        match_asset_movements(database=database)

    assert find_match_mock.call_count == unmatched_count
    # Processed in order of descending timestamp: withdrawal3, withdrawal2, deposit1
    withdrawal3.identifier = 12
    assert find_match_mock.call_args_list[0].kwargs['asset_movement'] == withdrawal3
    withdrawal2.identifier = 9
    assert find_match_mock.call_args_list[1].kwargs['asset_movement'] == withdrawal2

    # Check that the modified matched events are not removed when resetting for redecode
    assert deposit2_matched_event.identifier is not None
    with database.conn.write_ctx() as write_cursor:
        events_db.reset_events_for_redecode(write_cursor, Location.ETHEREUM)
        assert len(events_db.get_history_events_internal(
            cursor=write_cursor,
            filter_query=HistoryEventFilterQuery.make(
                identifiers=[deposit2_matched_event.identifier],
            ),
        )) == 1


@pytest.mark.parametrize(('event_type', 'event_subtype'), [
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET),
    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
])
def test_withdrawal_fee(
        database: 'DBHandler',
        event_type: HistoryEventType,
        event_subtype: HistoryEventSubType,
) -> None:
    """Regression test for incorrect matching due to fee tolerance."""
    with database.conn.write_ctx() as write_cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(
            write_cursor=write_cursor,
            history=[(withdrawal_movement := AssetMovement(
                location=Location.POLONIEX,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700001000000),
                asset=A_AAVE,
                amount=FVal('64.57557962'),
                unique_id='polo_withdrawal_1',
                location_label='Poloniex 1',
            )), AssetMovement(
                location=Location.POLONIEX,
                event_subtype=HistoryEventSubType.FEE,
                timestamp=TimestampMS(1700001000000),
                asset=A_AAVE,
                amount=FVal('0.32548608'),
                unique_id='polo_withdrawal_1',
                location_label='Poloniex 1',
            ), (receive_event := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700001010000),
                location=Location.ETHEREUM,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=A_AAVE,
                amount=FVal('64.25009354'),
                location_label=make_evm_address(),
            ))],
        )

    with database.conn.read_ctx() as cursor:
        inserted_events = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                group_identifiers=[
                    withdrawal_movement.group_identifier,
                    receive_event.group_identifier,
                ],
                order_by_rules=[('history_events_identifier', True)],
            ),
        )

    group_id_to_identifier = {
        event.group_identifier: event.identifier
        for event in inserted_events
    }
    assert group_id_to_identifier[withdrawal_movement.group_identifier] is not None
    assert group_id_to_identifier[receive_event.group_identifier] is not None

    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        withdrawal_id = cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier=?',
            (withdrawal_movement.group_identifier,),
        ).fetchone()[0]
        receive_id = cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier=?',
            (receive_event.group_identifier,),
        ).fetchone()[0]
        assert _get_match_for_movement(cursor=cursor, movement_id=withdrawal_id) == receive_id


def test_multiple_close_matches_clustered(database: 'DBHandler') -> None:
    """Ensure clustered movements are matched to the closest amounts."""
    events_db = DBHistoryEvents(database)
    with database.user_write() as write_cursor:
        database.set_settings(
            write_cursor=write_cursor,
            settings=ModifiableDBSettings(
                asset_movement_amount_tolerance=FVal('0.01'),
            ),
        )

    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                identifier=(evm_event_1_id := 1),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal('25.61'),
                location_label=make_evm_address(),
            ), EvmEvent(
                identifier=(evm_event_2_id := 2),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000 + 6 * 60 * 1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal('25.50'),
                location_label=make_evm_address(),
            ), AssetMovement(
                identifier=(movement_1_id := 3),
                location=Location.POLONIEX,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700000000000 + 2 * 60 * 1000),
                asset=A_ETH,
                amount=FVal('25.59'),
                unique_id='polo_deposit_1',
                location_label='Poloniex 1',
            ), AssetMovement(
                identifier=(movement_2_id := 4),
                location=Location.POLONIEX,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700000000000 + 4 * 60 * 1000),
                asset=A_ETH,
                amount=FVal('25.45'),
                unique_id='polo_deposit_2',
                location_label='Poloniex 1',
            )],
        )

    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        matched_1 = _get_match_for_movement(cursor=cursor, movement_id=movement_1_id)
        matched_2 = _get_match_for_movement(cursor=cursor, movement_id=movement_2_id)

    assert matched_1 == evm_event_1_id
    assert matched_2 == evm_event_2_id


def test_customized_deposit(database: 'DBHandler') -> None:
    """Test matching a customized deposit event with a gas event present.

    The issue in this test is the difference being off by 0.3%. We had 0.2% before.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(gas_event := EvmEvent(
                identifier=1,
                tx_ref=(tx_hash := make_evm_tx_hash()),
                sequence_index=0,
                timestamp=TimestampMS(1700002000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001'),
                counterparty=CPT_GAS,
                location_label=(location_label := make_evm_address()),
            )), EvmEvent(
                identifier=(customized_id := 2),
                tx_ref=tx_hash,
                sequence_index=1,
                timestamp=gas_event.timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=ONE,
                location_label=location_label,
            ), AssetMovement(
                identifier=(movement_id := 3),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700002060000),
                asset=A_ETH,
                amount=FVal('0.997109827'),
                unique_id='kraken_deposit_eth_1',
                location_label='Kraken 1',
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700002000000 + 900000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.00182'),
                counterparty=CPT_GAS,
                location_label=location_label,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700002000000 + 1800000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.00182'),
                counterparty=CPT_GAS,
                location_label=location_label,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700002000000 + 2700000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.00182'),
                counterparty=CPT_GAS,
                location_label=location_label,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700002000000 + 3600000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.00182'),
                counterparty=CPT_GAS,
                location_label=location_label,
            )],
        )
        write_cursor.execute(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) '
            'VALUES(?, ?, ?)',
            (
                customized_id,
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
            ),
        )

    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        assert _get_match_for_movement(cursor=cursor, movement_id=movement_id) == customized_id


def test_deposit_withdrawal_direction(database: 'DBHandler') -> None:
    """Onchain deposit to exchange should not match an exchange withdrawal."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                identifier=1,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700003000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=ONE,
                counterparty=CPT_KRAKEN,
                location_label=make_evm_address(),
            ), AssetMovement(
                identifier=(movement_id := 2),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700003001000),
                asset=A_ETH,
                amount=ONE,
                unique_id='kraken_withdrawal_1',
                location_label='Kraken 1',
            )],
        )

    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        assert _get_match_for_movement(cursor=cursor, movement_id=movement_id) is None


def test_gno_kraken_flow(database: 'DBHandler') -> None:
    """Test GNO deposit/withdrawal flow with fees and bridge event."""
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(  # deposit to kraken
                identifier=1,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700004000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_GNO,
                amount=FVal('64'),
                counterparty=CPT_KRAKEN,
                location_label=make_evm_address(),
            ), EvmEvent(  # gas fee for deposit
                identifier=2,
                tx_ref=make_evm_tx_hash(),
                sequence_index=1,
                timestamp=TimestampMS(1700004000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001'),
                counterparty=CPT_GAS,
                location_label=make_evm_address(),
            ), AssetMovement(
                identifier=(deposit_id := 3),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700004060000),
                asset=A_GNO,
                amount=FVal('64'),
                unique_id='kraken_gno_deposit_1',
                location_label='Kraken 1',
            ), AssetMovement(
                identifier=(withdrawal_id := 4),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700005000000),
                asset=A_GNO,
                amount=FVal('64'),
                unique_id='kraken_gno_withdrawal_1',
                location_label='Kraken 1',
            ), AssetMovement(  # withdrawal fee
                identifier=5,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.FEE,
                timestamp=TimestampMS(1700005000000),
                asset=A_GNO,
                amount=FVal('0.01'),
                unique_id='kraken_gno_withdrawal_1',
                location_label='Kraken 1',
            ), EvmEvent(  # onchain received after withdrawal
                identifier=(withdraw_event_id := 6),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700005060000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=A_GNO,
                amount=FVal('63.99'),
                location_label=make_evm_address(),
            ), EvmEvent(  # bridge event
                identifier=7,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700006000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_GNO,
                amount=FVal('64'),
                counterparty=CPT_GNOSIS_CHAIN,
                location_label=make_evm_address(),
            )],
        )

    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        assert _get_match_for_movement(cursor=cursor, movement_id=deposit_id) is not None
        assert _get_match_for_movement(cursor=cursor, movement_id=withdrawal_id) == withdraw_event_id  # noqa: E501


def test_match_asset_movements_settings(database: 'DBHandler') -> None:
    """Test that the amount tolerance and time range settings works correctly, with the match
    failing when tolerance or time range is too small but succeeding with higher values.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(movement_event := AssetMovement(
                identifier=(movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1520000000000),
                asset=A_USDC,
                amount=FVal('0.2'),
                unique_id='xyz',
                location_label='Kraken 1',
            )), (matched_event := EvmEvent(
                identifier=(match_id := 2),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(movement_event.timestamp + HOUR_IN_MILLISECONDS * 2),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('0.199'),  # Differs by 0.001 (0.5%)
                location_label=make_evm_address(),
            ))],
        )

    for tolerance, time_range, expected_value in (
        (FVal('0.01'), HOUR_IN_SECONDS, None),  # ok tolerance, but range too small - Fail
        (FVal('0.0001'), HOUR_IN_SECONDS * 3, None),  # ok range, but tolerance too low - Fail
        (FVal('0.01'), HOUR_IN_SECONDS * 3, match_id),  # ok tolerance, and ok range - Success
    ):
        with database.user_write() as write_cursor:
            database.set_settings(
                write_cursor=write_cursor,
                settings=ModifiableDBSettings(
                    asset_movement_amount_tolerance=tolerance,
                    asset_movement_time_range=time_range,
                ),
            )

        match_asset_movements(database=database)
        with database.conn.read_ctx() as cursor:
            result = cursor.execute(
                'SELECT right_event_id FROM history_event_links '
                'WHERE left_event_id=? AND link_type=?',
                (movement_id, HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db()),
            ).fetchone()
            assert (None if result is None else result[0]) == expected_value

    # Verify the adjustment event was created properly
    with database.conn.read_ctx() as cursor:
        all_events = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    assert len(all_events) == 3
    assert all_events[0].group_identifier == movement_event.group_identifier
    assert all_events[1].group_identifier == movement_event.group_identifier
    assert all_events[1].event_type == HistoryEventType.EXCHANGE_ADJUSTMENT
    assert all_events[1].event_subtype == HistoryEventSubType.RECEIVE
    assert all_events[1].amount == movement_event.amount - matched_event.amount
    assert all_events[2].group_identifier == matched_event.group_identifier


def test_auto_ignore_by_asset(database: 'DBHandler') -> None:
    """Test that movements are auto-ignored if their asset is for an unsupported chain."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                identifier=idx + 1,
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1520000000000),
                asset=asset,
                amount=ONE,
                unique_id=f'xyz{idx}',
                location_label='Kraken 1',
            ) for idx, asset in enumerate([
                A_BTC,  # Native token for supported chain
                A_WETH_OPT,  # EVM token from a supported chain
                A_WSOL,  # Solana token
                Asset('ICP'),  # Native token for unsupported chain
                Asset('eip155:250/erc20:0xc60D7067dfBc6f2caf30523a064f416A5Af52963'),  # Unsupported EVM chain.  # noqa: E501
                Asset('STRK'),  # STRK is an unsupported chain but another token in the collection
                # is from a supported chain, so don't ignore since it may be either token.
            ])],
        )

    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        assert set(cursor.execute(
            'SELECT event_id FROM history_event_link_ignores WHERE link_type=?',
            (HistoryEventLinkType.ASSET_MOVEMENT_MATCH.serialize_for_db(),),
        ).fetchall()) == {  # only 4 & 5 (ICP, and unsupported EVM chain token) are ignored
            (4,),
            (5,),
        }


@pytest.mark.parametrize('number_of_arbitrum_one_accounts', [2])
def test_ignore_transfers_between_tracked_accounts(
        database: 'DBHandler',
        arbitrum_one_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that transfers between tracked accounts are not included as possible matches."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(movement_event := AssetMovement(
                identifier=(movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1520000000000),
                asset=A_USDC,
                amount=FVal('25'),
                unique_id='xyz',
                location_label='Kraken 1',
            )), EvmEvent(  # Matched event
                identifier=(match_id := 2),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(movement_event.timestamp + 1),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=movement_event.asset,
                amount=movement_event.amount,
                location_label=arbitrum_one_accounts[0],
            ), EvmEvent(  # Ignored transfer between tracked addresses
                identifier=3,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(movement_event.timestamp + 2),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=movement_event.asset,
                amount=movement_event.amount,
                location_label=arbitrum_one_accounts[0],
                address=arbitrum_one_accounts[1],
            )],
        )

    # Run matching and check that it matched properly with the receive event instead of seeing
    # the transfer event as a second close match.
    _match_and_check(database=database, expected_matches=[(movement_id, match_id)])


def test_timestamp_tolerance(database: 'DBHandler') -> None:
    """Test that events that are not on the expected side of the asset movement can still be
    auto matched as long as they are within the 1 hour tolerance.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(movement_event := AssetMovement(
                identifier=(movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1520000000000),
                asset=A_USDC,
                amount=FVal('25'),
                unique_id='xyz',
                location_label='Kraken 1',
            )), EvmEvent(  # Matched event. Timestamp is before movement but within tolerance
                identifier=(match_id := 2),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(movement_event.timestamp - 10),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=movement_event.asset,
                amount=movement_event.amount,
            ), EvmEvent(  # Ignored event. Timestamp is before movement outside tolerance
                identifier=3,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(movement_event.timestamp - HOUR_IN_MILLISECONDS * 2),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=movement_event.asset,
                amount=movement_event.amount,
            )],
        )

    # Run matching and check that it matched properly with the event inside the tolerance.
    _match_and_check(database=database, expected_matches=[(movement_id, match_id)])


def test_exchange_deposit_delayed_credit(database: 'DBHandler') -> None:
    """Test matching a delayed exchange deposit credit to the onchain spend."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(EvmEvent(
                identifier=(match_id := 1),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1488715200000),  # 2017-03-05 12:00:00 UTC
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=(user_address := make_evm_address()),
            )), (asset_movement := AssetMovement(
                identifier=(movement_id := 2),
                location=Location.POLONIEX,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1488974400000),  # 2017-03-08 12:00:00 UTC
                asset=A_ETH,
                amount=ONE,
                unique_id='polo_deposit_1',
                location_label='Poloniex 1',
            ))],
        )

    _match_and_check(database=database, expected_matches=[(movement_id, match_id)])
    with database.conn.read_ctx() as cursor:
        matched_event = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(identifiers=[match_id]),
        )[0]

    assert matched_event.event_type == HistoryEventType.EXCHANGE_TRANSFER
    assert matched_event.event_subtype == HistoryEventSubType.SPEND
    assert matched_event.counterparty == 'poloniex'  # type: ignore[attr-defined]
    assert matched_event.notes == f'Send 1 ETH from {user_address} to Poloniex 1'
    assert matched_event.extra_data == {'matched_asset_movement': {
        'group_identifier': asset_movement.group_identifier,
        'exchange': 'poloniex',
        'exchange_name': 'Poloniex 1',
    }}


def test_exchange_deposit_sai_to_dai_credit(database: 'DBHandler') -> None:
    """Test matching a SAI onchain deposit with a DAI exchange credit."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(EvmEvent(
                identifier=(match_id := 1),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(ts_sec_to_ms(Timestamp(SAI_DAI_MIGRATION_TS + 1))),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_SAI,
                amount=FVal('25'),
                location_label=make_evm_address(),
            )), AssetMovement(
                identifier=(movement_id := 2),
                location=Location.POLONIEX,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(ts_sec_to_ms(Timestamp(SAI_DAI_MIGRATION_TS + 2))),
                asset=A_DAI,
                amount=FVal('25'),
                unique_id='polo_deposit_sai_dai_1',
                location_label='Poloniex 1',
            )],
        )

    _match_and_check(database=database, expected_matches=[(movement_id, match_id)])


def test_adjustments(database: 'DBHandler') -> None:
    """Test that we properly create adjustment events during matching if amounts differ."""
    events_db = DBHistoryEvents(database)

    events_to_add = []
    movement_data: list[tuple[Asset, AssetMovementSubtype, float, float]] = [
        (A_ETH, HistoryEventSubType.RECEIVE, 5.49, 5.5),
        (A_BTC, HistoryEventSubType.RECEIVE, 5.5, 5.49),
        (A_USDC, HistoryEventSubType.SPEND, 5.49, 5.5),
        (A_WSOL, HistoryEventSubType.SPEND, 5.5, 5.49),
    ]
    for idx, (asset, movement_subtype, movement_amount, match_amount) in enumerate(movement_data):
        events_to_add.extend([(movement_event := AssetMovement(
            location=Location.KRAKEN,
            event_subtype=movement_subtype,
            timestamp=TimestampMS(1600000000000 + idx),
            asset=asset,
            amount=FVal(movement_amount),
            location_label='kraken',
        )), HistoryEvent(  # Existing adjustment event should be replaced
            group_identifier=movement_event.group_identifier,
            sequence_index=1,
            timestamp=movement_event.timestamp,
            location=movement_event.location,
            event_type=HistoryEventType.EXCHANGE_ADJUSTMENT,
            event_subtype=HistoryEventSubType.SPEND,
            asset=movement_event.asset,
            amount=FVal('0.1234'),
        ), EvmEvent(
            tx_ref=make_evm_tx_hash(),
            sequence_index=1,
            timestamp=movement_event.timestamp,
            location=Location.OPTIMISM,
            event_type=(
                HistoryEventType.SPEND if movement_subtype == HistoryEventSubType.RECEIVE
                else HistoryEventType.RECEIVE
            ),
            event_subtype=HistoryEventSubType.NONE,
            asset=asset,
            amount=FVal(match_amount),
        )])

    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=events_to_add,
        )

    # Run matching and check that the adjustment events were created with proper subtypes
    match_asset_movements(database=database)
    with database.conn.read_ctx() as cursor:
        for asset, expected_adjustment_subtype in (
            (A_ETH, HistoryEventSubType.RECEIVE),
            (A_BTC, HistoryEventSubType.SPEND),
            (A_USDC, HistoryEventSubType.SPEND),
            (A_WSOL, HistoryEventSubType.RECEIVE),
        ):
            assert len(events := events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    assets=(asset,),
                    event_types=[HistoryEventType.EXCHANGE_ADJUSTMENT],
                ),
            )) == 1
            assert events[0].event_subtype == expected_adjustment_subtype
            assert events[0].amount == FVal('0.01')


def test_match_by_balance_tracking_event_direction(database: 'DBHandler') -> None:
    """Test that when there are multiple close matches due to the accounting direction being
    neutral that we narrow the match based on is balance tracking direction.
    """
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[(movement_event := AssetMovement(
                identifier=(movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1520000000000),
                asset=A_USDC,
                amount=FVal('25'),
                unique_id='xyz',
                location_label='Kraken 1',
            )), EvmEvent(  # Ignored event. Balance tracking direction is OUT (wrong direction).
                identifier=2,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=movement_event.timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=movement_event.asset,
                amount=movement_event.amount,
            ), EvmEvent(  # Matched event. Balance tracking direction is IN (expected direction).
                identifier=(match_id := 3),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=movement_event.timestamp,
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=movement_event.asset,
                amount=movement_event.amount,
            )],
        )

    _match_and_check(database=database, expected_matches=[(movement_id, match_id)])


def test_match_by_transaction_id_without_0x_prefix(database: 'DBHandler') -> None:
    """Match by tx hash when movement transaction_id is missing the 0x prefix."""
    tx_hash = make_evm_tx_hash()
    tx_hash_str = str(tx_hash)
    amount = FVal('110')
    ts = TimestampMS(1700000000000)
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                identifier=(movement_id := 1),
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=ts,
                asset=A_USDC,
                amount=amount,
                unique_id='coinbasepro_withdrawal_1',
                extra_data=AssetMovementExtraData(
                    transaction_id=tx_hash_str[2:],
                    address=make_evm_address(),
                ),
                location_label='Coinbase Pro 1',
            ), EvmEvent(  # Matched by tx hash
                identifier=(match_id := 2),
                tx_ref=tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(ts + 12000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            ), EvmEvent(  # Same amount, wrong tx hash
                identifier=3,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(ts + 18000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            )],
        )

    _match_and_check(database=database, expected_matches=[(movement_id, match_id)])


def test_reprocess_ambiguous_movement_after_candidate_gets_matched(database: 'DBHandler') -> None:
    """Retry ambiguous movements when one of their candidates gets matched later."""
    tx_ref = make_evm_tx_hash()
    tx_ref_str = str(tx_ref)
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(  # Processed first (newer timestamp): two close matches.
                identifier=(ambiguous_movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700004000000),
                asset=A_USDC,
                amount=(amount := FVal('110')),
                unique_id='kraken_withdrawal_ambiguous',
                location_label='Kraken 1',
            ), AssetMovement(  # Processed later, but uniquely matched by tx hash.
                identifier=(tx_ref_movement_id := 2),
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700003000000),
                asset=A_USDC,
                amount=amount,
                unique_id='coinbasepro_withdrawal_txref',
                extra_data=AssetMovementExtraData(
                    transaction_id=tx_ref_str[2:],
                    address=make_evm_address(),
                ),
                location_label='Coinbase Pro 1',
            ), EvmEvent(  # Candidate 1: tx-ref movement should pick this one.
                identifier=(tx_ref_match_id := 3),
                tx_ref=tx_ref,
                sequence_index=0,
                timestamp=TimestampMS(1700003005000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            ), EvmEvent(  # Candidate 2: remaining match for the previously ambiguous movement.
                identifier=(remaining_match_id := 4),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700003006000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            )],
        )

    _match_and_check(
        database=database,
        expected_matches=[
            (tx_ref_movement_id, tx_ref_match_id),
            (ambiguous_movement_id, remaining_match_id),
        ],
    )


def test_retry_ambiguous_movement_stays_ambiguous(database: 'DBHandler') -> None:
    """Retry path should update candidate mappings when ambiguity remains."""
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(  # Processed first: 3 matching candidates.
                identifier=(ambiguous_movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700005000000),
                asset=A_USDC,
                amount=(amount := FVal('110')),
                unique_id='kraken_withdrawal_ambiguous',
                location_label='Kraken 1',
            ), AssetMovement(  # Processed second: uniquely matches candidate 1 by tx hash.
                identifier=(tx_ref_movement_id := 2),
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700004000000),
                asset=A_USDC,
                amount=amount,
                unique_id='coinbasepro_withdrawal_txref',
                extra_data=AssetMovementExtraData(
                    transaction_id=str(tx_ref := make_evm_tx_hash())[2:],
                    address=make_evm_address(),
                ),
                location_label='Coinbase Pro 1',
            ), EvmEvent(  # Candidate 1: matched by tx-ref movement.
                identifier=(tx_ref_match_id := 3),
                tx_ref=tx_ref,
                sequence_index=0,
                timestamp=TimestampMS(1700004005000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            ), EvmEvent(  # Candidate 2: remains for ambiguous movement after retry.
                identifier=4,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700004006000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            ), EvmEvent(  # Candidate 3: remains for ambiguous movement after retry.
                identifier=5,
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700004007000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            )],
        )

    with patch(
        'rotkehlchen.tasks.events._set_ambiguous_candidate_mappings',
        wraps=task_events._set_ambiguous_candidate_mappings,
    ) as set_mappings_mock:
        match_asset_movements(database=database)

    with database.conn.read_ctx() as cursor:
        assert _get_match_for_movement(cursor=cursor, movement_id=tx_ref_movement_id) == tx_ref_match_id  # noqa: E501
        assert _get_match_for_movement(cursor=cursor, movement_id=ambiguous_movement_id) is None

    ambiguous_calls = [
        call for call in set_mappings_mock.call_args_list
        if call.kwargs['movement_id'] == ambiguous_movement_id
    ]
    assert [len(call.kwargs['matched_events']) for call in ambiguous_calls] == [3, 2]


def test_retry_ambiguous_movement_loses_all_candidates(database: 'DBHandler') -> None:
    """Retry path should clear candidate mappings when no candidates remain."""
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(  # Processed first: 2 matching candidates.
                identifier=(ambiguous_movement_id := 1),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700005000000),
                asset=A_USDC,
                amount=(amount := FVal('110')),
                unique_id='kraken_withdrawal_ambiguous',
                location_label='Kraken 1',
            ), AssetMovement(  # Uniquely matches candidate 1 by tx hash.
                identifier=(tx_ref_movement_id_1 := 2),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700004000000),
                asset=A_USDC,
                amount=amount,
                unique_id='coinbasepro_withdrawal_txref_1',
                extra_data=AssetMovementExtraData(
                    transaction_id=str(tx_ref_1 := make_evm_tx_hash())[2:],
                    address=make_evm_address(),
                ),
                location_label='Kraken 2',
            ), AssetMovement(  # Uniquely matches candidate 2 by tx hash.
                identifier=(tx_ref_movement_id_2 := 3),
                location=Location.KRAKEN,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700003990000),
                asset=A_USDC,
                amount=amount,
                unique_id='coinbasepro_withdrawal_txref_2',
                extra_data=AssetMovementExtraData(
                    transaction_id=str(tx_ref_2 := make_evm_tx_hash())[2:],
                    address=make_evm_address(),
                ),
                location_label='Kraken 3',
            ), EvmEvent(  # Candidate 1
                identifier=(tx_ref_match_id_1 := 4),
                tx_ref=tx_ref_1,
                sequence_index=0,
                timestamp=TimestampMS(1700004005000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            ), EvmEvent(  # Candidate 2
                identifier=(tx_ref_match_id_2 := 5),
                tx_ref=tx_ref_2,
                sequence_index=0,
                timestamp=TimestampMS(1700003995000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=amount,
                location_label=make_evm_address(),
            )],
        )

    with patch(
        'rotkehlchen.tasks.events._set_ambiguous_candidate_mappings',
        wraps=task_events._set_ambiguous_candidate_mappings,
    ) as set_mappings_mock:
        match_asset_movements(database=database)

    with database.conn.read_ctx() as cursor:
        assert _get_match_for_movement(cursor=cursor, movement_id=tx_ref_movement_id_1) == tx_ref_match_id_1  # noqa: E501
        assert _get_match_for_movement(cursor=cursor, movement_id=tx_ref_movement_id_2) == tx_ref_match_id_2  # noqa: E501
        assert _get_match_for_movement(cursor=cursor, movement_id=ambiguous_movement_id) is None

    ambiguous_calls = [
        call for call in set_mappings_mock.call_args_list
        if call.kwargs['movement_id'] == ambiguous_movement_id
    ]
    assert [len(call.kwargs['matched_events']) for call in ambiguous_calls] == [2, 0]


def test_match_coinbasepro_coinbase_transfer(database: 'DBHandler') -> None:
    """Test that we properly match transfers between coinbasepro and coinbase.
    Regression test for matching exchange to exchange movements even if the asset is
    for an unsupported chain (ICP in this case).
    """
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[AssetMovement(
                identifier=1,
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1670000330000),
                asset=A_USDC,
                amount=FVal('2.256789'),
                unique_id='xyz1',
            ), AssetMovement(
                identifier=2,
                location=Location.COINBASE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1670000329000),
                asset=A_USDC,
                amount=FVal('2.256789'),
                unique_id='xyz2',
                notes='Transfer funds from CoinbasePro',
            ), AssetMovement(
                identifier=3,
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1670000315000),
                asset=Asset('ICP'),
                amount=FVal('0.0098765'),
                unique_id='xyz3',
            ), AssetMovement(
                identifier=4,
                location=Location.COINBASE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1670000313000),
                asset=Asset('ICP'),
                amount=FVal('0.0098765'),
                unique_id='xyz4',
                notes='Transfer funds from CoinbasePro',
            )],
        )

    # Since these are exchange to exchange movements, there are two entries for each pair,
    # one entry for every asset movement.
    _match_and_check(database=database, expected_matches=[(1, 2), (2, 1), (3, 4), (4, 3)])


def test_coinbasepro_transfer_with_onchain_event(database: 'DBHandler') -> None:
    """Ensure CoinbasePro transfer notes restrict matches to Coinbase/CoinbasePro."""
    with database.conn.write_ctx() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                identifier=(match_id := 1),
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700012000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=make_evm_address(),
            ), AssetMovement(
                identifier=(movement_id := 2),
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700012005000),
                asset=A_ETH,
                amount=ONE,
                unique_id='cbpro_deposit_1',
                location_label='CoinbasePro 1',
            ), AssetMovement(
                identifier=(movement_id_2 := 3),
                location=Location.COINBASEPRO,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700013000000),
                asset=A_ETH,
                amount=ONE,
                unique_id='cbpro_withdrawal_1',
                location_label='CoinbasePro 1',
                notes='Transfer funds to CoinbasePro',
            ), AssetMovement(
                identifier=(match_id_2 := 4),
                location=Location.COINBASE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700013001000),
                asset=A_ETH,
                amount=ONE,
                unique_id='cb_deposit_1',
                location_label='Coinbase 1',
                notes='Transfer funds from CoinbasePro',
            )],
        )

    _match_and_check(
        database=database,
        expected_matches=[
            (movement_id, match_id),
            (movement_id_2, match_id_2),
            (match_id_2, movement_id_2),
        ],
    )


def test_deposit_to_anon(database: 'DBHandler') -> None:
    """Regression test for wrong pairing when a deposit is followed by a withdrawal.

    Scenario: user deposits onchain to Coinbase, then Coinbase withdraws to a different
    address on the same chain. We expect the deposit movement to match the outgoing
    onchain transfer and the withdrawal movement to match the incoming transfer. In the
    reported bug these get swapped due to the matching heuristics.
    """
    with database.conn.write_ctx() as write_cursor:
        (events_db := DBHistoryEvents(database)).add_history_events(
            write_cursor=write_cursor,
            history=[(spend_event := EvmEvent(  # onchain spend to exchange
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('100'),
                location_label=make_evm_address(),
                address=make_evm_address(),
            )), (deposit_movement := AssetMovement(
                location=Location.COINBASE,
                event_subtype=HistoryEventSubType.RECEIVE,
                timestamp=TimestampMS(1700000050000),
                asset=A_USDC,
                amount=FVal('100'),
                unique_id='cb_deposit_1',
                location_label='Coinbase 1',
            )), (withdrawal_movement := AssetMovement(
                location=Location.COINBASE,
                event_subtype=HistoryEventSubType.SPEND,
                timestamp=TimestampMS(1700000300000),
                asset=A_USDC,
                amount=FVal('100'),
                unique_id='cb_withdrawal_1',
                location_label='Coinbase 1',
            )), (receive_event := EvmEvent(  # onchain receive from exchange
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000350000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('100'),
                location_label=make_evm_address(),
                address=make_evm_address(),
            )),
        ])

    with database.conn.read_ctx() as cursor:
        inserted_events = events_db.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                group_identifiers=[
                    spend_event.group_identifier,
                    deposit_movement.group_identifier,
                    withdrawal_movement.group_identifier,
                    receive_event.group_identifier,
                ],
                order_by_rules=[('history_events_identifier', True)],
            ),
        )

    match_asset_movements(database=database)
    group_id_to_identifier = {
        event.group_identifier: event.identifier
        for event in inserted_events
    }

    with database.conn.read_ctx() as cursor:
        deposit_match = _get_match_for_movement(
            cursor=cursor,
            movement_id=group_id_to_identifier[deposit_movement.group_identifier],  # deposit id
        )
        withdrawal_match = _get_match_for_movement(
            cursor=cursor,
            movement_id=group_id_to_identifier[withdrawal_movement.group_identifier],  # withdrawal_id  # noqa: E501
        )

    assert deposit_match == group_id_to_identifier[spend_event.group_identifier]  # outgoing_event_id  # noqa: E501
    assert withdrawal_match == group_id_to_identifier[receive_event.group_identifier]  # incoming_event_id  # noqa: E501
