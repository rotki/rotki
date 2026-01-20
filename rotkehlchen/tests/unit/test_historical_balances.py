from typing import TYPE_CHECKING

import gevent

from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.balances.historical import HistoricalBalancesManager
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import CPT_EIGENLAYER
from rotkehlchen.chain.ethereum.modules.liquity.constants import CPT_LIQUITY
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE_V3
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.chain.evm.decoding.hop.constants import CPT_HOP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BTC, A_ETH
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.filtering import HistoricalBalancesFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.tests.utils.ethereum import TEST_ADDR1, TEST_ADDR2
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID, Location, Timestamp, TimestampMS
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


def test_process_historical_balances_clears_stale_marker(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    cache_key = DBCacheStatic.STALE_BALANCES_FROM_TS.value

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                group_identifier='grp1',
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ),
        )

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT value FROM key_value_cache WHERE name = ?',
            (cache_key,),
        ).fetchone() is not None

    gevent.sleep(0.01)
    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT value FROM key_value_cache WHERE name = ?',
            (cache_key,),
        ).fetchone() is None


def test_has_unprocessed_events(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test _has_unprocessed_events correctly uses stale marker to determine processing state.

    Conditions tested:
    - stale_value=None: False (all events evaluated, including negative balance skips)
    - stale_value exists + last_processing=None: query result (never processed)
    - stale_value exists + last_processing exists: filtered query (>= stale_event_ts)
    """
    manager = HistoricalBalancesManager(database)
    stale_cache_key = DBCacheStatic.STALE_BALANCES_FROM_TS.value
    modification_cache_key = DBCacheStatic.STALE_BALANCES_MODIFICATION_TS.value

    def add_event(ts: int, asset: Asset = A_ETH) -> None:
        with database.user_write() as write_cursor:
            DBHistoryEvents(database).add_history_event(
                write_cursor=write_cursor,
                event=EvmEvent(
                    tx_ref=make_evm_tx_hash(),
                    group_identifier=f'grp_{ts}',
                    sequence_index=0,
                    timestamp=TimestampMS(ts),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=asset,
                    amount=FVal('10'),
                    location_label=TEST_ADDR1,
                ),
            )

    def clear_stale_marker() -> None:
        with database.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name IN (?, ?)',
                (stale_cache_key, modification_cache_key),
            )

    def set_stale_marker(event_ts: int, modification_ts: int) -> None:
        with database.user_write() as write_cursor:
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.STALE_BALANCES_FROM_TS,
                value=str(event_ts),
            )
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.STALE_BALANCES_MODIFICATION_TS,
                value=str(modification_ts),
            )

    def set_last_processing(ts: int) -> None:
        with database.user_write() as write_cursor:
            database.set_static_cache(
                write_cursor=write_cursor,
                name=DBCacheStatic.LAST_HISTORICAL_BALANCE_PROCESSING_TS,
                value=Timestamp(ts),
            )

    # 1. No events, no stale marker -> False
    clear_stale_marker()
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(9999)]) is False

    # 2. All processed, no modifications (stale=None) -> False
    add_event(1000)
    gevent.sleep(0.01)
    process_historical_balances(database, messages_aggregator)
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(9999)]) is False

    # 3. All processed including negative balance skip (stale=None) -> False (the fix!)
    clear_stale_marker()
    set_last_processing(ts_now())
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(9999)]) is False

    # 4. Events added, never processed (stale exists, last_processing=None) -> True
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM key_value_cache')
        write_cursor.execute('DELETE FROM event_metrics')
    add_event(2000)
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(9999)]) is True

    # 5. Events added, never processed, no match (wrong asset) -> False
    assert manager._has_unprocessed_events('asset = ?', ['BTC']) is False

    # 6. New events after processing, matches new events -> True
    gevent.sleep(0.01)
    process_historical_balances(database, messages_aggregator)
    add_event(5000)
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(9999)]) is True

    # 7. New events after processing, query only old events -> False
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(3000)]) is False

    # 8. New ETH events, query BTC -> False
    assert manager._has_unprocessed_events('asset = ?', ['BTC']) is False

    # 9. New events at ts=5000, query ts <= 3000 (before stale_event_ts) -> False
    set_stale_marker(5000, ts_now() * 1000)
    set_last_processing(ts_now() - 1)
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(3000)]) is False

    # 10. Events modified during processing -> True
    with database.user_write() as write_cursor:
        write_cursor.execute('DELETE FROM event_metrics WHERE event_identifier IN (SELECT identifier FROM history_events WHERE timestamp >= 5000)')  # noqa: E501
    assert manager._has_unprocessed_events('timestamp <= ?', [TimestampMS(9999)]) is True


def test_get_balances_with_unprocessed_events_and_timestamp_filter(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Regression test ensuring FVal timestamp scaling results are int-converted for SQL binding.

    When querying historical balances with a timestamp filter, the timestamp is multiplied by
    scaling_factor, producing an FVal that must be explicitly converted to int before passing
    to SQL to avoid type binding errors.
    """
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                group_identifier='grp_test',
                sequence_index=0,
                timestamp=TimestampMS(1729787659000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ONE,
                location_label=TEST_ADDR1,
            ),
        )

    filter_query = HistoricalBalancesFilterQuery.make(
        timestamp=Timestamp(1729787659),
        location=Location.ETHEREUM,
    )
    manager = HistoricalBalancesManager(database)
    processing_required, balances = manager.get_balances(filter_query=filter_query)

    assert processing_required is True
    assert balances is None


def test_get_balances_skips_zero_amounts(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test that get_balances excludes assets with zero balance from results."""
    manager = HistoricalBalancesManager(database)

    with database.user_write() as write_cursor:
        # ETH: +10 -10 = 0 (should be excluded), BTC: +5 (should be included)
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                group_identifier='grp1',
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                group_identifier='grp2',
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                group_identifier='grp3',
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_BTC,
                amount=FVal('5'),
                location_label=TEST_ADDR1,
            )],
        )

    process_historical_balances(database, messages_aggregator)
    _, balances = manager.get_balances(HistoricalBalancesFilterQuery.make(timestamp=Timestamp(4)))
    assert balances == {A_BTC: FVal('5')}


def test_transfer_updates_sender_and_receiver_buckets(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test TRANSFER/NONE events create metrics for sender and receiver buckets.

    Regular token transfer uses wallet buckets:
    1. Receive 10 ETH -> wallet1 = 10
    2. Transfer 3 ETH to wallet2 -> wallet1 = 7, wallet2 = 3

    Protocol token transfer uses protocol buckets:
    3. Receive 10 Balancer LP -> wallet1 Balancer = 10
    4. Transfer 3 LP to wallet2 -> wallet1 Balancer = 7, wallet2 Balancer = 3

    Protocol tokens from untracked address use protocol bucket:
    5. Receive 5 LP via RECEIVE/NONE -> wallet1 Balancer = 12
    """
    balancer_lp_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56'),
        chain_id=ChainID.ETHEREUM,
        protocol=CPT_BALANCER_V2,
    )

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('3'),
                location_label=TEST_ADDR1,
                address=TEST_ADDR2,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=balancer_lp_token,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
                counterparty=CPT_BALANCER_V2,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(4000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=balancer_lp_token,
                amount=FVal('3'),
                location_label=TEST_ADDR1,
                address=TEST_ADDR2,
            ), EvmEvent(  # protocol token from untracked address uses protocol bucket
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(5000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=balancer_lp_token,
                amount=FVal('5'),
                location_label=TEST_ADDR1,
            )],
        )

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT he.timestamp, he.asset, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.metric_value',
        ).fetchall() == [
            (1000, A_ETH.identifier, TEST_ADDR1, None, '10'),  # wallet1: 0 + 10 = 10
            (2000, A_ETH.identifier, TEST_ADDR2, None, '3'),  # wallet2: 0 + 3 = 3
            (2000, A_ETH.identifier, TEST_ADDR1, None, '7'),  # wallet1: 10 - 3 = 7
            (3000, balancer_lp_token.identifier, TEST_ADDR1, CPT_BALANCER_V2, '10'),  # 0 + 10 = 10
            (4000, balancer_lp_token.identifier, TEST_ADDR2, CPT_BALANCER_V2, '3'),  # 0 + 3 = 3
            (4000, balancer_lp_token.identifier, TEST_ADDR1, CPT_BALANCER_V2, '7'),  # 10 - 3 = 7
            (5000, balancer_lp_token.identifier, TEST_ADDR1, CPT_BALANCER_V2, '12'),  # 7 + 5 = 12
        ]


def test_deposit_to_protocol_updates_wallet_and_protocol_buckets(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test DEPOSIT/DEPOSIT_TO_PROTOCOL and WITHDRAWAL/WITHDRAW_FROM_PROTOCOL events.

    1. Receive 10 ETH -> wallet = 10
    2. Deposit 5 ETH to Aave -> wallet = 5, Aave = 5
    3. Withdraw 2 ETH from Aave -> wallet = 7, Aave = 3
    """
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                asset=A_ETH,
                amount=FVal('5'),
                location_label=TEST_ADDR1,
                counterparty=CPT_AAVE_V3,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=TEST_ADDR1,
                counterparty=CPT_AAVE_V3,
            )],
        )

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT he.timestamp, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.protocol NULLS FIRST',
        ).fetchall() == [
            (1000, TEST_ADDR1, None, '10'),  # wallet: 0 + 10 = 10
            (2000, TEST_ADDR1, None, '5'),  # wallet: 10 - 5 = 5
            (2000, TEST_ADDR1, CPT_AAVE_V3, '5'),  # protocol: 0 + 5 = 5
            (3000, TEST_ADDR1, None, '7'),  # wallet: 5 + 2 = 7
            (3000, TEST_ADDR1, CPT_AAVE_V3, '3'),  # protocol: 5 - 2 = 3
        ]


def test_staking_deposit_and_withdraw_updates_wallet_and_protocol_buckets(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test STAKING DEPOSIT_ASSET and REMOVE_ASSET events.

    1. Receive 10 ETH -> wallet = 10
    2. Stake 4 ETH to Eigenlayer -> wallet = 6, Eigenlayer = 4
    3. Unstake 2 ETH from Eigenlayer -> wallet = 8, Eigenlayer = 2
    """
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=A_ETH,
                amount=FVal('4'),
                location_label=TEST_ADDR1,
                counterparty=CPT_EIGENLAYER,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.REMOVE_ASSET,
                asset=A_ETH,
                amount=FVal('2'),
                location_label=TEST_ADDR1,
                counterparty=CPT_EIGENLAYER,
            )],
        )

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT he.timestamp, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.protocol NULLS FIRST',
        ).fetchall() == [
            (1000, TEST_ADDR1, None, '10'),  # wallet: 0 + 10 = 10
            (2000, TEST_ADDR1, None, '6'),  # wallet: 10 - 4 = 6
            (2000, TEST_ADDR1, CPT_EIGENLAYER, '4'),  # protocol: 0 + 4 = 4
            (3000, TEST_ADDR1, None, '8'),  # wallet: 6 + 2 = 8
            (3000, TEST_ADDR1, CPT_EIGENLAYER, '2'),  # protocol: 4 - 2 = 2
        ]


def test_wrapped_deposit_and_redeem_moves_between_protocol_buckets(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test DEPOSIT_FOR_WRAPPED and REDEEM_WRAPPED with protocol assets.

    Simulates Balancer LP token flow through Aura Finance gauge:
    1. Receive 10 LP from Balancer -> Balancer bucket = 10
    2. Deposit 6 LP into Aura -> Balancer = 4, Aura = 6
    3. Redeem 3 LP from Aura -> Balancer = 7, Aura = 3
    """
    balancer_lp_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56'),
        chain_id=ChainID.ETHEREUM,
        protocol=CPT_BALANCER_V2,
    )

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
                asset=balancer_lp_token,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
                counterparty=CPT_BALANCER_V2,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
                asset=balancer_lp_token,
                amount=FVal('6'),
                location_label=TEST_ADDR1,
                counterparty=CPT_AURA_FINANCE,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
                asset=balancer_lp_token,
                amount=FVal('3'),
                location_label=TEST_ADDR1,
                counterparty=CPT_AURA_FINANCE,
            )],
        )

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT he.timestamp, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.protocol',
        ).fetchall() == [
            (1000, TEST_ADDR1, CPT_BALANCER_V2, '10'),  # 0 + 10 = 10
            (2000, TEST_ADDR1, CPT_AURA_FINANCE, '6'),  # 0 + 6 = 6
            (2000, TEST_ADDR1, CPT_BALANCER_V2, '4'),  # 10 - 6 = 4
            (3000, TEST_ADDR1, CPT_AURA_FINANCE, '3'),  # 6 - 3 = 3
            (3000, TEST_ADDR1, CPT_BALANCER_V2, '7'),  # 4 + 3 = 7
        ]


def test_synthetic_interest_event_when_protocol_withdrawal_exceeds_deposit(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test synthetic interest event creation when withdrawing more than deposited.

    When WITHDRAWAL/WITHDRAW_FROM_PROTOCOL or STAKING/REMOVE_ASSET events withdraw more
    than the protocol bucket balance (due to yield earned), a synthetic RECEIVE/INTEREST
    event is created for the difference.

    1. Receive 10 ETH -> wallet = 10
    2. Deposit 5 ETH to Liquity -> wallet = 5, Liquity = 5
    3. Withdraw 5.1 ETH from Liquity (earned 0.1 ETH yield):
       - Interest event created: Liquity = 5 + 0.1 = 5.1
       - Withdrawal processed: wallet = 5 + 5.1 = 10.1, Liquity = 5.1 - 5.1 = 0
    """
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.DEPOSIT,
                event_subtype=HistoryEventSubType.DEPOSIT_TO_PROTOCOL,
                asset=A_ETH,
                amount=FVal('5'),
                location_label=TEST_ADDR1,
                counterparty=CPT_LIQUITY,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(3000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                asset=A_ETH,
                amount=FVal('5.1'),
                location_label=TEST_ADDR1,
                counterparty=CPT_LIQUITY,
            )],
        )

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT amount, sequence_index, notes FROM history_events ORDER BY timestamp, sequence_index').fetchall() == [  # noqa: E501
            ('10', 0, None),  # receive 10 ETH
            ('5', 0, None),  # deposit 5 ETH
            ('0.1', 0, 'Profit earned from ETH in liquity'),  # synthetic interest event
            ('5.1', 1, None),  # withdrawal (sequence_index bumped from 0 to 1)
        ]

        # Verify event metrics
        assert cursor.execute(
            'SELECT he.timestamp, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.protocol NULLS FIRST, he.sequence_index',
        ).fetchall() == [
            (1000, TEST_ADDR1, None, '10'),  # wallet: 0 + 10 = 10
            (2000, TEST_ADDR1, None, '5'),  # wallet: 10 - 5 = 5
            (2000, TEST_ADDR1, CPT_LIQUITY, '5'),  # protocol: 0 + 5 = 5
            (3000, TEST_ADDR1, None, '10.1'),  # wallet: 5 + 5.1 = 10.1
            (3000, TEST_ADDR1, CPT_LIQUITY, '5.1'),  # protocol: 5 + 0.1 = 5.1 (interest event)
            (3000, TEST_ADDR1, CPT_LIQUITY, '0'),  # protocol: 5.1 - 5.1 = 0 (withdrawal)
        ]


def test_synthetic_interest_event_when_protocol_withdrawal_without_deposit(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test synthetic interest event when withdrawing from a protocol without a tracked deposit.

    This can happen when the deposit event is missing. In this case, the entire withdrawal
    amount is treated as interest/yield.

    1. Withdraw 5 ETH from Liquity (no prior deposit tracked):
       - Interest event created: Liquity = 0 + 5 = 5
       - Withdrawal processed: wallet = 0 + 5 = 5, Liquity = 5 - 5 = 0
    """
    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_event(
            write_cursor=write_cursor,
            event=EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.WITHDRAWAL,
                event_subtype=HistoryEventSubType.WITHDRAW_FROM_PROTOCOL,
                asset=A_ETH,
                amount=FVal('5'),
                location_label=TEST_ADDR1,
                counterparty=CPT_LIQUITY,
            ),
        )

    process_historical_balances(database, messages_aggregator)
    with database.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT amount, sequence_index, notes FROM history_events ORDER BY timestamp, sequence_index').fetchall() == [  # noqa: E501
            ('5', 0, 'Profit earned from ETH in liquity'),  # synthetic interest event
            ('5', 1, None),  # withdrawal (sequence_index bumped from 0 to 1)
        ]

        assert cursor.execute(  # Verify event metrics
            'SELECT he.timestamp, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.protocol NULLS FIRST, he.sequence_index',
        ).fetchall() == [
            (1000, TEST_ADDR1, None, '5'),  # wallet: 0 + 5 = 5
            (1000, TEST_ADDR1, CPT_LIQUITY, '5'),  # protocol: 0 + 5 = 5 (interest event)
            (1000, TEST_ADDR1, CPT_LIQUITY, '0'),  # protocol: 5 - 5 = 0 (withdrawal)
        ]


def test_staking_protocol_lp_token_received_from_untracked_address(
        database: 'DBHandler',
        messages_aggregator: 'MessagesAggregator',
) -> None:
    """Test staking a protocol LP token that was received via RECEIVE/NONE from untracked address.

    When a protocol LP token (e.g., HOP LP) is received from an untracked address, it goes into
    the protocol bucket. When later staking that token, the withdrawal should come from the
    protocol bucket, not the wallet bucket.

    Since asset_protocol == counterparty (both 'hop'), both buckets are the same, so the net
    balance remains unchanged (10 - 5 + 5 = 10). The key is that no negative balance error occurs.

    1. Receive 10 HOP LP via RECEIVE/NONE -> hop bucket = 10
    2. Stake 5 HOP LP to HOP -> hop bucket = 10 (same bucket: -5 out, +5 in)
    """
    hop_lp_token = get_or_create_evm_token(
        userdb=database,
        evm_address=string_to_evm_address('0x5C2048094bAaDe483D0b1DA85c3Da6200A88a849'),
        chain_id=ChainID.ETHEREUM,
        protocol=CPT_HOP,
    )

    with database.user_write() as write_cursor:
        DBHistoryEvents(database).add_history_events(
            write_cursor=write_cursor,
            history=[EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(1000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=hop_lp_token,
                amount=FVal('10'),
                location_label=TEST_ADDR1,
            ), EvmEvent(
                tx_ref=make_evm_tx_hash(),
                sequence_index=0,
                timestamp=TimestampMS(2000),
                location=Location.ETHEREUM,
                event_type=HistoryEventType.STAKING,
                event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
                asset=hop_lp_token,
                amount=FVal('5'),
                location_label=TEST_ADDR1,
                counterparty=CPT_HOP,
            )],
        )

    process_historical_balances(database, messages_aggregator)

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT he.timestamp, em.location_label, em.protocol, em.metric_value '
            'FROM event_metrics em '
            'JOIN history_events he ON em.event_identifier = he.identifier '
            'ORDER BY he.timestamp, em.protocol',
        ).fetchall() == [
            (1000, TEST_ADDR1, CPT_HOP, '10'),  # hop bucket: 0 + 10 = 10
            (2000, TEST_ADDR1, CPT_HOP, '10'),  # hop bucket: 10 - 5 + 5 = 10 (same bucket)
        ]
