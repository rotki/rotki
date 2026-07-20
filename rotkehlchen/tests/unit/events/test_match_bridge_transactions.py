from typing import TYPE_CHECKING

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC, A_USDT, A_WBTC
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.constants import HistoryEventLinkType
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DEFAULT_BRIDGE_MATCH_TIME_RANGE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.bridges import match_bridge_transactions
from rotkehlchen.tests.fixtures import MockedWsMessage
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


def _get_bridge_links(database: DBHandler) -> set[tuple[int, int]]:
    with database.conn.read_ctx() as cursor:
        return set(cursor.execute(
            'SELECT left_event_id, right_event_id FROM history_event_links WHERE link_type=?',
            (HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),),
        ).fetchall())


def _event_id(database: DBHandler, event: EvmEvent) -> int:
    """The identifier assigned at insertion (add_history_events does not backfill it)."""
    with database.conn.read_ctx() as cursor:
        return cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier=? AND sequence_index=?',
            (event.group_identifier, event.sequence_index),
        ).fetchone()[0]


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_bridge_transactions_exact_transfer_id(database: DBHandler) -> None:
    """Two legs sharing counterparty and transfer_id match exactly, even with
    an amount difference beyond tolerance and another plausible candidate present."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
                counterparty=CPT_ACROSS,
                extra_data={'bridge': {
                    'from_chain': 1,
                    'to_chain': 42161,
                    'from_address': user_address,
                    'to_address': user_address,
                    'transfer_id': '4024312',
                }},
            )), (withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000300000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('0.9'),  # >1% difference: only the id can match them
                location_label=user_address,
                counterparty=CPT_ACROSS,
                extra_data={'bridge': {
                    'from_chain': 1,
                    'to_chain': 42161,
                    'to_address': user_address,
                    'transfer_id': '4024312',
                }},
            )), EvmEvent(  # decoy with different transfer id
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000200000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
                counterparty=CPT_ACROSS,
                extra_data={'bridge': {'transfer_id': '999'}},
            )],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {(_event_id(database, deposit), _event_id(database, withdrawal))}  # noqa: E501

    # verify matched_bridge metadata (including implied fee) got written on both sides
    with database.conn.read_ctx() as cursor:
        rows = dict(cursor.execute(
            'SELECT identifier, extra_data FROM history_events WHERE identifier IN (?, ?)',
            (deposit_id := _event_id(database, deposit), withdrawal_id := _event_id(database, withdrawal)),  # noqa: E501
        ))
    assert '"matched_bridge"' in rows[deposit_id]
    assert '"fee_amount": "0.1"' in rows[deposit_id]
    assert '"matched_bridge"' in rows[withdrawal_id]

    # a second run must not create further links or messages about these
    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {(_event_id(database, deposit), _event_id(database, withdrawal))}  # noqa: E501


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_bridge_transactions_wrapped_assets_transfer_id(database: DBHandler) -> None:
    """Legs whose assets are unrelated (e.g. LaPoste-wrapped side-chain tokens vs the
    canonical mainnet tokens) still match exactly on transfer id, including several
    tokens bridged in one message and disambiguated only by the token index."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    deposit_tx, withdrawal_tx = make_evm_tx_hash(), make_evm_tx_hash()
    deposits, withdrawals = [], []
    for index, (deposit_asset, withdrawal_asset, amount) in enumerate([
        (A_DAI, A_USDT, FVal('1000')),  # same nonce, same amounts impossible to
        (A_USDC, A_WBTC, FVal('1000')),  # tell apart without the token index
    ]):
        deposits.append(EvmEvent(
            tx_ref=deposit_tx,
            sequence_index=index,
            timestamp=TimestampMS(1700000000000),
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=deposit_asset,
            amount=amount,
            location_label=user_address,
            counterparty=CPT_STAKEDAO_V2,
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 1,
                'to_address': user_address,
                'transfer_id': f'4242-{index}',
            }},
        ))
        withdrawals.append(EvmEvent(
            tx_ref=withdrawal_tx,
            sequence_index=index,
            timestamp=TimestampMS(1700001000000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=withdrawal_asset,
            amount=amount,
            location_label=user_address,
            counterparty=CPT_STAKEDAO_V2,
            extra_data={'bridge': {
                'from_chain': 42161,
                'to_chain': 1,
                'to_address': user_address,
                'transfer_id': f'4242-{index}',
            }},
        ))

    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=deposits + withdrawals,
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposits[0]), _event_id(database, withdrawals[0])),
        (_event_id(database, deposits[1]), _event_id(database, withdrawals[1])),
    }


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_bridge_transactions_heuristic(database: DBHandler) -> None:
    """A deposit with structured destination data matches the right chain/address
    candidate; a plain receive is rewritten into a bridge withdrawal on match."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    other_address = make_evm_address()
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(  # bridge deposit to other_address on gnosis
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=user_address,
                counterparty='some_bridge',
                extra_data={'bridge': {
                    'from_chain': 1,
                    'to_chain': 100,
                    'from_address': user_address,
                    'to_address': other_address,
                }},
            )), EvmEvent(  # wrong chain (arbitrum, not gnosis)
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000100000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=other_address,
            ), (plain_receive := EvmEvent(  # correct chain and address, undecoded
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000200000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=other_address,
            )), EvmEvent(  # wrong address on the right chain
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000200000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=user_address,
            )],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {(_event_id(database, deposit), _event_id(database, plain_receive))}  # noqa: E501
    with database.conn.read_ctx() as cursor:
        event_type, event_subtype, counterparty = cursor.execute(
            'SELECT he.type, he.subtype, cei.counterparty FROM history_events he '
            'LEFT JOIN chain_events_info cei ON he.identifier=cei.identifier '
            'WHERE he.identifier=?',
            (_event_id(database, plain_receive),),
        ).fetchone()
    assert event_type == HistoryEventType.WITHDRAWAL.serialize()
    assert event_subtype == HistoryEventSubType.BRIDGE.serialize()
    assert counterparty == 'some_bridge'


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_bridge_transactions_ambiguous_and_ws(database: DBHandler) -> None:
    """Ambiguous deposits stay unmatched and are reported via websocket."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
            )] + [EvmEvent(  # two indistinguishable candidates
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000300000),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
            ) for _ in range(2)],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == set()
    assert database.msg_aggregator.rotki_notifier.pop_message() == MockedWsMessage(  # type: ignore  # pop_message exists on MockRotkiNotifier
        message_type=WSMessageType.UNMATCHED_BRIDGE_TRANSACTIONS,
        data={'count': 3},  # 1 deposit + 2 withdrawals unmatched
    )


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_bridge_transactions_slow_bridge_window(database: DBHandler) -> None:
    """Native L2->L1 withdrawals with challenge periods match beyond the default window."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    deposit_ts = TimestampMS(1700000000000)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(  # L2->L1 arbitrum native bridge withdrawal initiation
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=deposit_ts,
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
                counterparty=CPT_ARBITRUM_ONE,
            )), (claim := EvmEvent(  # executed on L1 eight days later
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(deposit_ts + ts_sec_to_ms(Timestamp(8 * DAY_IN_SECONDS))),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=user_address,
                counterparty=CPT_ARBITRUM_ONE,
            ))],
        )

    assert 8 * DAY_IN_SECONDS > DEFAULT_BRIDGE_MATCH_TIME_RANGE  # sanity: beyond default window
    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {(_event_id(database, deposit), _event_id(database, claim))}  # noqa: E501


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_bridge_transactions_unsupported_destination(database: DBHandler) -> None:
    """Deposits to chains rotki cannot query are auto-resolved and not re-reported."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('1'),
                location_label=make_evm_address(),
                counterparty=CPT_ACROSS,
                extra_data={'bridge': {'from_chain': 1, 'to_chain': 59144}},  # linea unsupported
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == set()
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT event_id FROM history_event_link_ignores WHERE link_type=?',
            (HistoryEventLinkType.BRIDGE_MATCH.serialize_for_db(),),
        ).fetchall() == [(_event_id(database, deposit),)]
    assert database.msg_aggregator.rotki_notifier.pop_message() is None  # type: ignore  # pop_message exists on MockRotkiNotifier
