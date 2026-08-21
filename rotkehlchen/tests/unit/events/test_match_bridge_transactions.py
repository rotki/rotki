from typing import TYPE_CHECKING

import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.zksync.constants import (
    CPT_ZKSYNC,
    ZKSYNC_LITE_SUNSET_CLAIM,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.across.constants import CPT_ACROSS
from rotkehlchen.chain.evm.decoding.cctp.constants import CPT_CCTP
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.decoding.lifi.constants import CPT_LIFI
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.chain.evm.decoding.relay.constants import CPT_RELAY
from rotkehlchen.chain.evm.decoding.socket_bridge.constants import CPT_SOCKET
from rotkehlchen.chain.evm.decoding.stakedao.v2.constants import CPT_STAKEDAO_V2
from rotkehlchen.chain.zksync_lite.constants import ZKL_IDENTIFIER
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC, A_USDT, A_WBTC, A_XDAI
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HistoryEventLinkType,
    HistoryMappingState,
)
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import DEFAULT_BRIDGE_MATCH_TIME_RANGE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.bridges import (
    SYNTHETIC_BRIDGE_GROUP_PREFIX,
    get_unmatched_bridge_events,
    match_bridge_transactions,
)
from rotkehlchen.tests.fixtures import MockedWsMessage
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import Location, SupportedBlockchain, Timestamp, TimestampMS
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
def test_match_lifi_relay_bridge_by_order_id(database: DBHandler) -> None:
    """A LI.FI Relay route matches its Relay receive by the underlying order id,
    despite different counterparties, assets and amounts."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1783071502000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=Asset('eip155:42161/erc20:0x0c06cCF38114ddfc35e07427B9424adcca9F44F8'),
                amount=FVal('52.085941055797375509'),
                location_label=(user_address := make_evm_address()),
                counterparty=CPT_LIFI,
                extra_data={'bridge': {
                    'from_chain': 42161,
                    'to_chain': 1,
                    'to_address': user_address,
                    'transfer_id': (
                        order_id := (
                            '4865275a0ce3b45d06b859019d78246f'
                            '27ab851a689ba92ad9225999aa2d0753'
                        )
                    ),
                }},
            )), (withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1783071503000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('0.034555752880651201'),
                location_label=user_address,
                counterparty=CPT_RELAY,
                extra_data={'bridge': {
                    'to_chain': 1,
                    'to_address': user_address,
                    'transfer_id': order_id,
                }},
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposit), _event_id(database, withdrawal)),
    }
    with database.conn.read_ctx() as cursor:
        assert all(
            '"fee_amount"' not in row[0]
            for row in cursor.execute(
                'SELECT extra_data FROM history_events WHERE identifier IN (?, ?)',
                (_event_id(database, deposit), _event_id(database, withdrawal)),
            )
        )


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize(('underlying_counterparty', 'transfer_id'), [
    (CPT_ACROSS, '1295289'),
    (CPT_CCTP, '108927'),
    (CPT_HOP, '0x515a483a21beb5543dc74f6dbcb2bcfbb190cc01e10f2209fd195c47b24a0275'),
])
def test_match_socket_underlying_bridge_by_transfer_id(
        database: DBHandler,
        underlying_counterparty: str,
        transfer_id: str,
) -> None:
    """Socket uses normal filters with a liberal counterparty and transfer-id tie-breaker."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    source_asset = Asset(
        'eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    )
    destination_asset = Asset(
        'eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83',
    )
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.BASE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=source_asset,
                amount=FVal('399.365908'),
                location_label=user_address,
                counterparty=CPT_SOCKET,
                extra_data={'bridge': {
                    'from_chain': 8453,
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': transfer_id,
                }},
            )), (withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000100000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=destination_asset,
                amount=FVal('399.128031'),
                location_label=user_address,
                counterparty=underlying_counterparty,
                extra_data={'bridge': {
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': transfer_id,
                }},
            )), EvmEvent(  # closer exact-amount candidate, but without the transfer id
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000090000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=destination_asset,
                amount=FVal('399.365908'),
                location_label=user_address,
                counterparty=underlying_counterparty,
                extra_data={'bridge': {
                    'to_chain': 100,
                    'to_address': user_address,
                }},
            )],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposit), _event_id(database, withdrawal)),
    }


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_do_not_auto_match_socket_transfer_id_across_asset_collections(
        database: DBHandler,
) -> None:
    """A shared transfer id is not sufficient for an automatic cross-asset match."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    source_asset = Asset(
        'eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    )
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.BASE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=source_asset,
                amount=FVal('399.365908'),
                location_label=user_address,
                counterparty=CPT_SOCKET,
                extra_data={'bridge': {
                    'from_chain': 8453,
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': '1295289',
                }},
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000100000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_DAI,
                amount=FVal('399.365908'),
                location_label=user_address,
                counterparty=CPT_ACROSS,
                extra_data={'bridge': {
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': '1295289',
                }},
            )],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == set()


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
@pytest.mark.parametrize(('timestamp', 'amount'), [
    (TimestampMS(1800000000000), FVal('399.365908')),
    (TimestampMS(1700000100000), FVal('300')),
])
def test_socket_transfer_id_keeps_time_and_amount_filters(
        database: DBHandler,
        timestamp: TimestampMS,
        amount: FVal,
) -> None:
    """A Socket transfer id does not bypass the normal time or amount filters."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    source_asset = Asset(
        'eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    )
    destination_asset = Asset(
        'eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83',
    )
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.BASE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=source_asset,
                amount=FVal('399.365908'),
                location_label=user_address,
                counterparty=CPT_SOCKET,
                extra_data={'bridge': {
                    'from_chain': 8453,
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': '1295289',
                }},
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=timestamp,
                location=Location.GNOSIS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=destination_asset,
                amount=amount,
                location_label=user_address,
                counterparty=CPT_ACROSS,
                extra_data={'bridge': {
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': '1295289',
                }},
            )],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == set()


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_socket_underlying_bridge_without_transfer_id(database: DBHandler) -> None:
    """Socket routes accept a differently-labelled bridge leg when the ordinary
    chain, address, asset, amount and time heuristics identify it."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.OPTIMISM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_USDC,
                amount=FVal('22.189898'),
                location_label=user_address,
                counterparty=CPT_SOCKET,
                extra_data={'bridge': {
                    'from_chain': 10,
                    'to_chain': 137,
                    'to_address': user_address,
                }},
            )), (withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000100000),
                location=Location.POLYGON_POS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_USDC,
                amount=FVal('22.1'),
                location_label=user_address,
                counterparty=CPT_CCTP,
                extra_data={'bridge': {
                    'from_chain': 10,
                    'to_chain': 137,
                    'to_address': user_address,
                }},
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposit), _event_id(database, withdrawal)),
    }


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_cross_asset_bridge_by_target_asset(
        database: DBHandler,
) -> None:
    """An explicit target asset narrows candidates and permits a cross-asset route."""
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1783071502000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_USDC,
                amount=FVal('52.085941'),
                location_label=(user_address := make_evm_address()),
                counterparty=CPT_LIFI,
                extra_data={'bridge': {
                    'from_chain': 42161,
                    'to_chain': 1,
                    'to_address': user_address,
                    'to_asset': ZERO_ADDRESS,
                }},
            )), EvmEvent(  # same source asset and amount, but not the declared target asset
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1783071502500),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_USDC,
                amount=FVal('52.085941'),
                location_label=user_address,
            ), (receive := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1783071503000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.034555'),
                location_label=user_address,
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposit), _event_id(database, receive)),
    }


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


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_sunset_claim_synthesizes_zksync_lite_counterpart(database: DBHandler) -> None:
    """A ZKsync Lite sunset claim gets its L2 exit leg synthesized and linked, since
    the zksync lite API shutdown makes pulling the real counterpart impossible. The
    synthesized leg is marked with the synthetic (and matched) mapping states."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(claim := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1700000000000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_ETH,
                amount=FVal('0.05'),
                location_label=user_address,
                counterparty=CPT_ZKSYNC,
                address=ZKSYNC_LITE_SUNSET_CLAIM,
                notes='Claim 0.05 ETH from the ZKsync Lite sunset',
                extra_data={'bridge': {
                    'from_chain': SupportedBlockchain.ZKSYNC_LITE.serialize(),
                    'to_chain': 1,
                    'to_address': user_address,
                }},
            ))],
        )

    match_bridge_transactions(database=database)
    claim_id = _event_id(database, claim)
    with database.conn.read_ctx() as cursor:
        synthetic = next(
            x for x in events_db.get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(),
            ) if x.group_identifier == f'{SYNTHETIC_BRIDGE_GROUP_PREFIX}{claim.group_identifier}'
        )
        assert synthetic.identifier is not None
        assert synthetic.location == Location.ZKSYNC_LITE
        assert synthetic.event_type == HistoryEventType.DEPOSIT
        assert synthetic.event_subtype == HistoryEventSubType.BRIDGE
        assert synthetic.asset == A_ETH
        assert synthetic.amount == FVal('0.05')
        assert synthetic.timestamp == claim.timestamp
        assert synthetic.location_label == user_address
        assert synthetic.notes == 'Send 0.05 ETH from zksync lite bridged to Ethereum'
        assert synthetic.extra_data is not None
        assert synthetic.extra_data['matched_bridge'] == {
            'group_identifier': claim.group_identifier,
            'location': Location.ETHEREUM.serialize(),
        }
        states = {(row[0], row[1]) for row in cursor.execute(
            'SELECT parent_identifier, value FROM history_events_mappings WHERE name=?',
            (HISTORY_MAPPING_KEY_STATE,),
        )}

    assert states == {
        (synthetic.identifier, HistoryMappingState.SYNTHETIC.serialize_for_db()),
        (synthetic.identifier, HistoryMappingState.MATCHED.serialize_for_db()),
        (claim_id, HistoryMappingState.MATCHED.serialize_for_db()),
    }
    assert _get_bridge_links(database) == {(synthetic.identifier, claim_id)}
    deposits, withdrawals = get_unmatched_bridge_events(database=database)
    assert len(deposits) == len(withdrawals) == 0

    # a second run must not synthesize another counterpart or create further links
    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {(synthetic.identifier, claim_id)}
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE group_identifier=?',
            (synthetic.group_identifier,),
        ).fetchone()[0] == 1


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_sunset_claim_resynthesis_reuses_orphaned_counterpart(database: DBHandler) -> None:
    """Redecoding the claim transaction (or the DB upgrade decoded-events reset)
    deletes the anchor — cascading the link away — while the synthetic zksync lite
    counterpart survives as an orphan. Re-running the matcher must reuse that orphan
    instead of failing on the unique (group_identifier, sequence_index) constraint."""
    events_db = DBHistoryEvents(database)
    user_address = make_evm_address()

    def make_claim() -> EvmEvent:
        return EvmEvent(
            tx_ref=claim_tx,
            sequence_index=0,
            timestamp=TimestampMS(1700000000000),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal('0.05'),
            location_label=user_address,
            counterparty=CPT_ZKSYNC,
            address=ZKSYNC_LITE_SUNSET_CLAIM,
            notes='Claim 0.05 ETH from the ZKsync Lite sunset',
            extra_data={'bridge': {
                'from_chain': SupportedBlockchain.ZKSYNC_LITE.serialize(),
                'to_chain': 1,
                'to_address': user_address,
            }},
        )

    claim_tx = make_evm_tx_hash()
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(write_cursor=write_cursor, history=[(claim := make_claim())])

    match_bridge_transactions(database=database)
    old_claim_id = _event_id(database, claim)
    with database.conn.read_ctx() as cursor:
        synthetic_id = cursor.execute(
            'SELECT identifier FROM history_events WHERE group_identifier=?',
            (synthetic_group := f'{SYNTHETIC_BRIDGE_GROUP_PREFIX}{claim.group_identifier}',),
        ).fetchone()[0]
    assert _get_bridge_links(database) == {(synthetic_id, old_claim_id)}

    # simulate a redecode that does not preserve matched events: the anchor is
    # deleted (the link cascades away) and re-decoded from scratch
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute('DELETE FROM history_events WHERE identifier=?', (old_claim_id,))
        events_db.add_history_events(write_cursor=write_cursor, history=[make_claim()])
    assert _get_bridge_links(database) == set()

    match_bridge_transactions(database=database)
    new_claim_id = _event_id(database, claim)
    assert new_claim_id != old_claim_id
    assert _get_bridge_links(database) == {(synthetic_id, new_claim_id)}  # same synthetic reused
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE group_identifier=?',
            (synthetic_group,),
        ).fetchone()[0] == 1

    deposits, withdrawals = get_unmatched_bridge_events(database=database)
    assert len(deposits) == len(withdrawals) == 0


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_monerium_bridge_legs_by_transfer_id(database: DBHandler) -> None:
    """Monerium chain to chain moves match on the tx hash pair its API reports for both
    legs of a move, not on the amount and time heuristic.

    Both moves below are real gnosis <-> arbitrum EURe transfers. Their destination legs
    land seconds after the source ones onchain but are placed a day later here, well past
    the heuristic window, so a match can only come from the shared transfer id.
    """
    events_db = DBHistoryEvents(database)
    gnosis_eure = Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430')
    arbitrum_eure = Asset('eip155:42161/erc20:0x0c06cCF38114ddfc35e07427B9424adcca9F44F8')
    # gnosis -> arbitrum: burn 0xff00dec3..., mint 0x88d55171...
    out_user = '0x8EaeD0c875d0aF5134EEac3dA91BeCf8dE505e2b'
    out_transfer_id = '0x88d55171adb39b33c8b3b1802cf7873d6c04120d38de414800b8905a720a5e21-0xff00dec38e08377a18075e35c6b755da9f24882ec9aa5aa0de4ea6ebdedcb381'  # noqa: E501
    # arbitrum -> gnosis: burn 0x0262c273..., mint 0xcb922e79...
    in_user = '0xE53464166D9DaB175E9c290209d5eab9cF98eec5'
    in_transfer_id = '0x0262c273b8bd935e467e67f32b779aea6b0c3e294de335486180a62cbafed797-0xcb922e794da9d77dc2c3a395f5ba09f9e6e63040c1af90565a027839cdaff36e'  # noqa: E501
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(out_deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1787090645000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=gnosis_eure,
                amount=FVal('2000'),
                location_label=out_user,
                counterparty=CPT_MONERIUM,
                extra_data={'bridge': {
                    'from_chain': 100,
                    'to_chain': 42161,
                    'from_address': out_user,
                    'to_address': out_user,
                    'transfer_id': out_transfer_id,
                }},
            )), (out_withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1787090648000 + DAY_IN_SECONDS * 1000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=arbitrum_eure,
                amount=FVal('2000'),
                location_label=out_user,
                counterparty=CPT_MONERIUM,
                extra_data={'bridge': {
                    'from_chain': 100,
                    'to_chain': 42161,
                    'from_address': out_user,
                    'to_address': out_user,
                    'transfer_id': out_transfer_id,
                }},
            )), (in_deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1787216450000),
                location=Location.ARBITRUM_ONE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=arbitrum_eure,
                amount=FVal('196.34'),
                location_label=in_user,
                counterparty=CPT_MONERIUM,
                extra_data={'bridge': {
                    'from_chain': 42161,
                    'to_chain': 100,
                    'from_address': in_user,
                    'to_address': in_user,
                    'transfer_id': in_transfer_id,
                }},
            )), (in_withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1787216455000 + DAY_IN_SECONDS * 1000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=gnosis_eure,
                amount=FVal('196.34'),
                location_label=in_user,
                counterparty=CPT_MONERIUM,
                extra_data={'bridge': {
                    'from_chain': 42161,
                    'to_chain': 100,
                    'from_address': in_user,
                    'to_address': in_user,
                    'transfer_id': in_transfer_id,
                }},
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {  # source leg is always the left side of the link
        (_event_id(database, out_deposit), _event_id(database, out_withdrawal)),
        (_event_id(database, in_deposit), _event_id(database, in_withdrawal)),
    }
    deposits, withdrawals = get_unmatched_bridge_events(database=database)
    assert len(deposits) == len(withdrawals) == 0


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_xdai_bridge_by_nonce(database: DBHandler) -> None:
    """The two legs of a DAI to xDAI bridging match by the nonce the bridge logs.

    They are the legs decoded from ethereum transaction 0xeb720d57bd48a89a69ba743c98441
    4f711e06a6edacd2ab5ef6d4bfddc019d6b and gnosis transaction 0xa0a2a6996eadbd50db09787
    3c37674cd6c0f130bc283b617c8a88c6db606c0f3. The ethereum leg used to be identified by
    its own transaction hash while the gnosis one repeats the nonce, and ids that
    contradict each other veto the heuristic tiers as well, so the pair never matched.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=834,
                timestamp=TimestampMS(1749508919000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_DAI,
                amount=FVal(amount := '33.85386'),
                location_label=(user_address := make_evm_address()),
                counterparty=CPT_GNOSIS_CHAIN,
                extra_data={'bridge': {
                    'from_chain': 1,
                    'to_chain': 100,
                    'from_address': user_address,
                    'transfer_id': (transfer_id := (
                        '0x000000000000000000000000'
                        '0000000000000000000000000000000000000369'
                    )),
                }},
            )), (withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=10,
                timestamp=TimestampMS(1749509175000),
                location=Location.GNOSIS,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_XDAI,
                amount=FVal(amount),
                location_label=user_address,
                counterparty=CPT_GNOSIS_CHAIN,
                extra_data={'bridge': {
                    'from_chain': 1,
                    'to_chain': 100,
                    'to_address': user_address,
                    'transfer_id': transfer_id,
                }},
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposit), _event_id(database, withdrawal)),
    }


@pytest.mark.parametrize('function_scope_initialize_mock_rotki_notifier', [True])
def test_match_zksync_lite_withdrawal_past_default_window(database: DBHandler) -> None:
    """A zksync lite exit matches the ethereum leg that settles hours later.

    They are the legs of zksync lite transaction 0x4108ec114f61a486a67e072ae5508ee8a5ed
    42126f5bf892a5489364ef75e8f3 and ethereum transaction 0xcfb173fc85c133114c065f77101e
    4f522b45e8948ea34c858864a7d9e769d128, 6.6 hours apart because the funds are only
    released once the zksync block is verified on ethereum. That is past the default
    match window, so the pair is only found through the bridge's own slow window, which
    is reachable only because the zksync lite leg names its counterparty.
    """
    events_db = DBHistoryEvents(database)
    with database.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[(deposit := EvmEvent(
                group_identifier=ZKL_IDENTIFIER.format(tx_hash=str(zksync_tx_hash := make_evm_tx_hash())),  # noqa: E501
                tx_ref=zksync_tx_hash,
                sequence_index=0,
                timestamp=TimestampMS(1774130088000),
                location=Location.ZKSYNC_LITE,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_USDT,
                amount=FVal(amount := '4.0783'),
                location_label=(user_address := make_evm_address()),
                counterparty=CPT_ZKSYNC,
                extra_data={'bridge': {
                    'from_chain': 'zksync_lite',
                    'to_chain': 1,
                    'from_address': user_address,
                    'to_address': user_address,
                }},
            )), (withdrawal := EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=821,
                timestamp=TimestampMS(1774153859000),  # 6.6 hours after the exit
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.BRIDGE,
                asset=A_USDT,
                amount=FVal(amount),
                location_label=user_address,
                counterparty=CPT_ZKSYNC,
                extra_data={'bridge': {
                    'from_chain': 'zksync_lite',
                    'to_chain': 1,
                    'to_address': user_address,
                }},
            ))],
        )

    match_bridge_transactions(database=database)
    assert _get_bridge_links(database) == {
        (_event_id(database, deposit), _event_id(database, withdrawal)),
    }
