from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock, patch

import gevent
import pytest

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
    INTERNAL_TX_CONFLICT_REPULL_REASON_OTHER,
    POPULATE_INTERNAL_TX_CONFLICTS_QUERY,
    clean_internal_tx_conflict,
    get_internal_tx_conflicts,
    is_tx_customized,
)
from rotkehlchen.db.settings import DEFAULT_INTERNAL_TXS_TO_REPULL
from rotkehlchen.errors.misc import DataIntegrityError, InputError, RemoteError
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.internal_tx_conflicts import (
    _repull_internal_tx_data,
    _RepullResult,
    repull_internal_tx_conflicts,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator


def make_dummy_chains_aggregator(
        get_transaction_by_hash_result: tuple[Any, dict[str, str]],
        query_internal_side_effect: Exception | None = None,
        query_internal_return_value: tuple[Any, Any, str] | None = None,
        replace_internal_hook: Callable[..., None] | None = None,
        query_internal_hook: Callable[..., None] | None = None,
) -> Any:
    class _DummyInquirer:
        def get_transaction_by_hash(self, tx_hash):
            return get_transaction_by_hash_result

    class _DummyTransactions:
        def __init__(self) -> None:
            self.evm_inquirer = _DummyInquirer()

        def _query_internal_transactions_for_parent_hash(self, **kwargs):
            if query_internal_hook is not None:
                query_internal_hook(**kwargs)
            if query_internal_side_effect is not None:
                raise query_internal_side_effect
            if query_internal_return_value is not None:
                return query_internal_return_value
            return [], None, ''

        def _replace_internal_transactions_for_parent_hash(self, **kwargs):
            if replace_internal_hook is not None:
                replace_internal_hook(**kwargs)

    class _DummyDecoder:
        def decode_and_get_transaction_hashes(self, **_kwargs):
            return []

    class _DummyChainManager:
        def __init__(self) -> None:
            self.transactions = _DummyTransactions()
            self.transactions_decoder = _DummyDecoder()

    class _DummyChainsAggregator:
        def get_chain_manager(self, blockchain):
            return _DummyChainManager()

    return _DummyChainsAggregator()


def test_repull_internal_tx_conflicts_batch_limit(database) -> None:
    entries = [
        (
            make_evm_tx_hash(),
            ChainID.ETHEREUM.serialize_for_db(),
            INTERNAL_TX_CONFLICT_ACTION_REPULL,
            0,
        )
        for _ in range(25)
    ]
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, ?)',  # noqa: E501
            entries,
        )

    with patch(
            'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
            side_effect=lambda **kwargs: _RepullResult(
                chain_id=kwargs['chain_id'],
                tx_hash=kwargs['tx_hash'],
                needs_decode=False,
                error=None,
            ),
    ) as repull_mock:
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),  # not used by the patched call
            limit=DEFAULT_INTERNAL_TXS_TO_REPULL,
        )

    assert repull_mock.call_count == DEFAULT_INTERNAL_TXS_TO_REPULL
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_internal_tx_conflicts WHERE action=? AND fixed=1',
            (INTERNAL_TX_CONFLICT_ACTION_REPULL,),
        ).fetchone()[0] == DEFAULT_INTERNAL_TXS_TO_REPULL
        assert cursor.execute(
            'SELECT COUNT(*) FROM key_value_cache WHERE name=?',
            (DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS.value,),
        ).fetchone()[0] == 1


def test_repull_internal_tx_conflicts_sends_ws_message_after_fix(database) -> None:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, ?)',  # noqa: E501
            (tx_hash, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, 0),
        )

    with (
            patch.object(database.msg_aggregator, 'add_message') as add_message_mock,
            patch(
                'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
                side_effect=lambda **kwargs: _RepullResult(
                    chain_id=kwargs['chain_id'],
                    tx_hash=kwargs['tx_hash'],
                    needs_decode=False,
                    error=None,
                ),
            ),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),
            limit=DEFAULT_INTERNAL_TXS_TO_REPULL,
        )

    add_message_mock.assert_called_once_with(
        message_type=WSMessageType.INTERNAL_TX_FIXED,
        data={'chain': ChainID.ETHEREUM.to_name(), 'tx_hash': str(tx_hash)},
    )


def test_repull_internal_tx_conflicts_skip_customized(database) -> None:
    """Customized txs should be repulled (fixing bad internal data) but not
    redecoded, so the customized events are preserved.  The conflict entry
    must be marked as fixed afterwards."""
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1700000000),
        block_number=1,
        from_address=(sender := make_evm_address()),
        to_address=make_evm_address(),
        value=0,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[tx],
            relevant_address=sender,
        )
        write_cursor.execute(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, ?)',  # noqa: E501
            (tx_hash, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, 0),
        )
        write_cursor.execute(
            'INSERT INTO history_events('
            'identifier, entry_type, group_identifier, sequence_index, timestamp, '
            'location, location_label, asset, amount, notes, type, subtype, extra_data, ignored) '
            'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                777_001,
                HistoryBaseEntryType.EVM_EVENT.serialize_for_db(),
                f'10{tx_hash!s}',
                0,
                1700000000,
                Location.ETHEREUM.serialize_for_db(),
                sender,
                A_ETH.identifier,
                '1',
                'customized',
                HistoryEventType.TRADE.serialize(),
                HistoryEventSubType.SPEND.serialize(),
                None,
                0,
            ),
        )
        write_cursor.execute(
            'INSERT INTO chain_events_info(identifier, tx_ref, counterparty, address) '
            'VALUES(?, ?, ?, ?)',
            (777_001, tx_hash, None, None),
        )
        write_cursor.execute(
            'INSERT INTO history_events_mappings(parent_identifier, name, value) VALUES(?, ?, ?)',
            (
                777_001,
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
            ),
        )

    with (
        patch(
            'rotkehlchen.tasks.internal_tx_conflicts.is_tx_customized',
            wraps=is_tx_customized,
        ) as customized_check,
        patch.object(DBEvmTx, 'add_or_ignore_receipt_data'),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=make_dummy_chains_aggregator(
                get_transaction_by_hash_result=(tx, {'status': '0x1'}),
                query_internal_return_value=([], None, ''),
            ),
            limit=DEFAULT_INTERNAL_TXS_TO_REPULL,
        )

    # is_tx_customized is still consulted by the repull flow
    assert customized_check.call_count == 1
    with database.conn.read_ctx() as cursor:
        # conflict is marked as fixed (repull succeeded, decode was skipped)
        assert cursor.execute(
            'SELECT fixed FROM evm_internal_tx_conflicts WHERE transaction_hash=? AND chain=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0] == 1
        # customized event is still present and untouched
        assert cursor.execute(
            'SELECT notes FROM history_events WHERE identifier=?',
            (777_001,),
        ).fetchone()[0] == 'customized'


def test_repull_internal_tx_conflicts_records_retry_error(database) -> None:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, repull_reason, fixed) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
            (
                tx_hash,
                ChainID.ETHEREUM.serialize_for_db(),
                INTERNAL_TX_CONFLICT_ACTION_REPULL,
                INTERNAL_TX_CONFLICT_REPULL_REASON_OTHER,
                0,
            ),
        )

    with patch(
            'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
            side_effect=lambda **kwargs: _RepullResult(
                chain_id=kwargs['chain_id'],
                tx_hash=kwargs['tx_hash'],
                needs_decode=False,
                error='query failed',
            ),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),
            limit=DEFAULT_INTERNAL_TXS_TO_REPULL,
        )

    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT fixed, last_retry_ts, last_error FROM evm_internal_tx_conflicts '
            'WHERE transaction_hash=? AND chain=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()

    assert row[0] == 0
    assert row[1] is not None
    assert row[2] == 'query failed'


def test_repull_internal_tx_conflicts_prioritizes_untried_rows(database) -> None:
    tx_hash_never_tried = make_evm_tx_hash()
    tx_hash_retried = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, repull_reason, fixed, last_retry_ts) VALUES(?, ?, ?, ?, ?, ?)',  # noqa: E501
            [
                (tx_hash_retried, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_OTHER, 0, 1700000000),  # noqa: E501
                (tx_hash_never_tried, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, INTERNAL_TX_CONFLICT_REPULL_REASON_OTHER, 0, None),  # noqa: E501
            ],
        )

    with patch(
            'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
            side_effect=lambda **kwargs: _RepullResult(
                chain_id=kwargs['chain_id'],
                tx_hash=kwargs['tx_hash'],
                needs_decode=False,
                error=None,
            ),
    ) as repull_mock:
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),
            limit=1,
        )

    called_tx_hash = repull_mock.call_args.kwargs['tx_hash']
    assert called_tx_hash == tx_hash_never_tried


def test_repull_internal_tx_conflicts_limits_concurrency_to_batch_size(database) -> None:
    entries = [
        (
            make_evm_tx_hash(),
            ChainID.ETHEREUM.serialize_for_db(),
            INTERNAL_TX_CONFLICT_ACTION_REPULL,
            0,
        )
        for _ in range(12)
    ]
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, ?)',  # noqa: E501
            entries,
        )

    active_workers, max_workers = 0, 0

    def worker(**kwargs) -> _RepullResult:
        nonlocal active_workers, max_workers
        active_workers += 1
        max_workers = max(max_workers, active_workers)
        gevent.sleep(0.01)
        active_workers -= 1
        return _RepullResult(
            chain_id=kwargs['chain_id'],
            tx_hash=kwargs['tx_hash'],
            needs_decode=False,
            error=None,
        )

    with (
            patch('rotkehlchen.tasks.internal_tx_conflicts.REPULL_LAUNCH_STAGGER_SECONDS', 0),
            patch('rotkehlchen.tasks.internal_tx_conflicts.REPULL_BETWEEN_BATCH_DELAY_SECONDS', 0),
            patch(
                'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
                side_effect=worker,
            ),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),
            limit=len(entries),
        )

    assert max_workers == 5


def test_repull_internal_tx_conflicts_uses_staggered_launch(database) -> None:
    entries = [
        (
            make_evm_tx_hash(),
            ChainID.ETHEREUM.serialize_for_db(),
            INTERNAL_TX_CONFLICT_ACTION_REPULL,
            0,
        )
        for _ in range(7)
    ]
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, ?)',  # noqa: E501
            entries,
        )

    delays: list[float] = []

    def spawn_later(delay, func, **kwargs):
        delays.append(delay)
        return gevent.spawn(func, **kwargs)

    with (
            patch('rotkehlchen.tasks.internal_tx_conflicts.REPULL_LAUNCH_STAGGER_SECONDS', 0.2),
            patch('rotkehlchen.tasks.internal_tx_conflicts.REPULL_BETWEEN_BATCH_DELAY_SECONDS', 0),
            patch(
                'rotkehlchen.tasks.internal_tx_conflicts.gevent.spawn_later',
                side_effect=spawn_later,
            ),
            patch(
                'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
                side_effect=lambda **kwargs: _RepullResult(
                    chain_id=kwargs['chain_id'],
                    tx_hash=kwargs['tx_hash'],
                    needs_decode=False,
                    error=None,
                ),
            ),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),
            limit=len(entries),
        )

    assert delays == pytest.approx([0.0, 0.2, 0.4, 0.6, 0.8, 0.0, 0.2])


def test_repull_internal_tx_conflicts_decodes_in_chain_batches(database) -> None:
    tx_hash_eth_repull = make_evm_tx_hash()
    tx_hash_eth_fix = make_evm_tx_hash()
    tx_hash_optimism = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, 0)',  # noqa: E501
            [
                (tx_hash_eth_repull, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL),  # noqa: E501
                (tx_hash_eth_fix, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE),  # noqa: E501
                (tx_hash_optimism, ChainID.OPTIMISM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL),  # noqa: E501
            ],
        )

    ethereum_decoder = MagicMock()
    optimism_decoder = MagicMock()
    chain_managers = {
        ChainID.ETHEREUM.to_blockchain(): MagicMock(transactions_decoder=ethereum_decoder),
        ChainID.OPTIMISM.to_blockchain(): MagicMock(transactions_decoder=optimism_decoder),
    }

    chains_aggregator = MagicMock()
    chains_aggregator.get_chain_manager.side_effect = lambda blockchain: chain_managers[blockchain]

    with patch(
            'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
            side_effect=lambda **kwargs: _RepullResult(
                chain_id=kwargs['chain_id'],
                tx_hash=kwargs['tx_hash'],
                needs_decode=True,
                error=None,
            ),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=chains_aggregator,
            limit=10,
        )

    eth_tx_hashes = ethereum_decoder.decode_and_get_transaction_hashes.call_args.kwargs[
        'tx_hashes'
    ]
    assert set(eth_tx_hashes) == {tx_hash_eth_repull, tx_hash_eth_fix}
    optimism_decoder.decode_and_get_transaction_hashes.assert_called_once_with(
        tx_hashes=[tx_hash_optimism],
        send_ws_notifications=True,
        ignore_cache=True,
        delete_customized=False,
    )

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_internal_tx_conflicts WHERE fixed=1',
        ).fetchone()[0] == 3


def test_repull_internal_tx_conflicts_batch_decode_fallback_isolates_failures(database) -> None:
    tx_hash_ok1 = make_evm_tx_hash()
    tx_hash_fail = make_evm_tx_hash()
    tx_hash_ok2 = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES(?, ?, ?, 0)',  # noqa: E501
            [
                (
                    tx_hash_ok1,
                    ChainID.ETHEREUM.serialize_for_db(),
                    INTERNAL_TX_CONFLICT_ACTION_REPULL,
                ),
                (
                    tx_hash_fail,
                    ChainID.ETHEREUM.serialize_for_db(),
                    INTERNAL_TX_CONFLICT_ACTION_REPULL,
                ),
                (
                    tx_hash_ok2,
                    ChainID.ETHEREUM.serialize_for_db(),
                    INTERNAL_TX_CONFLICT_ACTION_REPULL,
                ),
            ],
        )

    ethereum_decoder = MagicMock()

    def decode_side_effect(**kwargs):
        tx_hashes = kwargs['tx_hashes']
        if len(tx_hashes) > 1:
            raise RemoteError('batch decode failed')
        if tx_hashes[0] == tx_hash_fail:
            raise RemoteError('single decode failed')
        return []

    ethereum_decoder.decode_and_get_transaction_hashes.side_effect = decode_side_effect
    chain_manager = MagicMock(transactions_decoder=ethereum_decoder)
    chains_aggregator = MagicMock()
    chains_aggregator.get_chain_manager.return_value = chain_manager

    with patch(
            'rotkehlchen.tasks.internal_tx_conflicts._repull_single_conflict',
            side_effect=lambda **kwargs: _RepullResult(
                chain_id=kwargs['chain_id'],
                tx_hash=kwargs['tx_hash'],
                needs_decode=True,
                error=None,
            ),
    ):
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=chains_aggregator,
            limit=10,
        )

    with database.conn.read_ctx() as cursor:
        ok1_row = cursor.execute(
            'SELECT fixed, last_error FROM evm_internal_tx_conflicts '
            'WHERE transaction_hash=? AND chain=?',
            (tx_hash_ok1, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()
        fail_row = cursor.execute(
            'SELECT fixed, last_retry_ts, last_error FROM evm_internal_tx_conflicts WHERE transaction_hash=? AND chain=?',  # noqa: E501
            (tx_hash_fail, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()
        ok2_row = cursor.execute(
            'SELECT fixed, last_error FROM evm_internal_tx_conflicts '
            'WHERE transaction_hash=? AND chain=?',
            (tx_hash_ok2, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()

    assert ok1_row == (1, None)
    assert fail_row[0] == 0
    assert fail_row[1] is not None
    assert fail_row[2] == 'single decode failed'
    assert ok2_row == (1, None)


def test_repull_internal_pull_dataintegrity_updates_retry_fields(database) -> None:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, repull_reason, fixed) VALUES(?, ?, ?, ?, ?)',  # noqa: E501
            (
                tx_hash,
                ChainID.ETHEREUM.serialize_for_db(),
                INTERNAL_TX_CONFLICT_ACTION_REPULL,
                INTERNAL_TX_CONFLICT_REPULL_REASON_OTHER,
                0,
            ),
        )

    class _DummyTx:
        def __init__(self) -> None:
            self.to_address = make_evm_address()
            self.timestamp = Timestamp(1700000000)

    repull_internal_tx_conflicts(
        database=database,
        chains_aggregator=make_dummy_chains_aggregator(
            get_transaction_by_hash_result=(_DummyTx(), {'status': '0x1'}),
            query_internal_side_effect=DataIntegrityError('empty internals payload'),
        ),
        limit=DEFAULT_INTERNAL_TXS_TO_REPULL,
    )

    with database.conn.read_ctx() as cursor:
        row = cursor.execute(
            'SELECT fixed, last_retry_ts, last_error FROM evm_internal_tx_conflicts '
            'WHERE transaction_hash=? AND chain=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()

    assert row[0] == 0
    assert row[1] is not None
    assert row[2] == 'Indexer did not provide valid data: empty internals payload'


def test_repull_fetch_failure_keeps_db_unchanged(database) -> None:
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1700000000),
        block_number=1,
        from_address=(sender := make_evm_address()),
        to_address=make_evm_address(),
        value=0,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    )
    with database.user_write() as write_cursor:
        DBEvmTx(database).add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[tx],
            relevant_address=sender,
        )
        parent_tx = write_cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0]
        write_cursor.execute(
            'INSERT INTO evm_internal_transactions(parent_tx, trace_id, from_address, to_address, value, gas, gas_used) '  # noqa: E501
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (parent_tx, 0, sender, tx.to_address, '5', '21000', '55'),
        )

    with database.conn.read_ctx() as cursor:
        internal_before = cursor.execute(
            'SELECT trace_id, from_address, to_address, value, gas, gas_used '
            'FROM evm_internal_transactions '
            'WHERE parent_tx=?',
            (parent_tx,),
        ).fetchall()
        tx_before = cursor.execute(
            'SELECT tx_hash, chain_id FROM evm_transactions WHERE identifier=?',
            (parent_tx,),
        ).fetchall()

    with pytest.raises(InputError, match='Failed to repull ethereum internals for tx'):
        _repull_internal_tx_data(
            database=database,
            chains_aggregator=make_dummy_chains_aggregator(
                get_transaction_by_hash_result=(tx, {'status': '0x1'}),
                query_internal_side_effect=RemoteError('fetch failed'),
            ),
            chain_id=ChainID.ETHEREUM,
            tx_hash=tx_hash,
        )

    with database.conn.read_ctx() as cursor:
        internal_after = cursor.execute(
            'SELECT trace_id, from_address, to_address, value, gas, gas_used '
            'FROM evm_internal_transactions '
            'WHERE parent_tx=?',
            (parent_tx,),
        ).fetchall()
        tx_after = cursor.execute(
            'SELECT tx_hash, chain_id FROM evm_transactions WHERE identifier=?',
            (parent_tx,),
        ).fetchall()

    assert tx_after == tx_before
    assert internal_after == internal_before


def test_repull_internal_conflict_uses_indexer_source_from_internal_query(database) -> None:
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=Timestamp(1700000000),
        block_number=1,
        from_address=make_evm_address(),
        to_address=make_evm_address(),
        value=0,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    )
    captured_indexer_source = {}

    with patch.object(DBEvmTx, 'add_or_ignore_receipt_data'):
        _repull_internal_tx_data(
            database=database,
            chains_aggregator=make_dummy_chains_aggregator(
                get_transaction_by_hash_result=(tx, {'status': '0x1'}),
                query_internal_return_value=([], None, 'etherscan'),
                replace_internal_hook=lambda **kwargs: captured_indexer_source.update(
                    {'value': kwargs['indexer_source']},
                ),
            ),
            chain_id=ChainID.ETHEREUM,
            tx_hash=tx_hash,
        )

    assert captured_indexer_source['value'] == 'etherscan'


def test_fix_conflict_with_specific_internal_tx_dataset(database) -> None:
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ARBITRUM_ONE,
        timestamp=Timestamp(1700000000),
        block_number=1,
        from_address=(sender := make_evm_address()),
        to_address=make_evm_address(),
        value=0,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    )
    with database.user_write() as write_cursor:
        dbevmtx = DBEvmTx(database)
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[tx],
            relevant_address=sender,
        )
        parent_tx = write_cursor.execute(
            'SELECT identifier FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx_hash, ChainID.ARBITRUM_ONE.serialize_for_db()),
        ).fetchone()[0]
        write_cursor.executemany(
            'INSERT INTO evm_internal_transactions('
            'parent_tx, trace_id, from_address, to_address, gas, gas_used, value'
            ') VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                (parent_tx, 0, '0x227DFD9fA88bfe186682f3A45597Bac051742e5F', '0xa669e7A0d4b3e4Fa48af2dE86BD4CD7126Be4e13', '0', '0', '967761034721284'),  # noqa: E501
                (parent_tx, 0, '0x227DFD9fA88bfe186682f3A45597Bac051742e5F', '0xa669e7A0d4b3e4Fa48af2dE86BD4CD7126Be4e13', '2300', '55', '967761034721284'),  # noqa: E501
                (parent_tx, 0, '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', '0x227DFD9fA88bfe186682f3A45597Bac051742e5F', '0', '0', '967761034721284'),  # noqa: E501
                (parent_tx, 0, '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', '0x227DFD9fA88bfe186682f3A45597Bac051742e5F', '122291', '55', '967761034721284'),  # noqa: E501
                (parent_tx, 0, '0xa669e7A0d4b3e4Fa48af2dE86BD4CD7126Be4e13', '0xDeEB02ADA5B089F851f2A1C0301d46631514D312', '113798', '0', '967761034721263'),  # noqa: E501
                (parent_tx, 1, '0xa669e7A0d4b3e4Fa48af2dE86BD4CD7126Be4e13', '0xDeEB02ADA5B089F851f2A1C0301d46631514D312', '113798', '0', '967761034721263'),  # noqa: E501
            ],
        )
        write_cursor.execute(
            'INSERT INTO evm_tx_mappings(tx_id, value) VALUES (?, ?)',
            (parent_tx, 0),
        )
        write_cursor.execute(POPULATE_INTERNAL_TX_CONFLICTS_QUERY)
        assert get_internal_tx_conflicts(
            cursor=write_cursor,
            action=INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
            fixed=False,
        ) == [(ChainID.ARBITRUM_ONE, tx_hash, INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE)]

        clean_internal_tx_conflict(
            write_cursor=write_cursor,
            tx_hash=tx_hash,
            chain_id=ChainID.ARBITRUM_ONE,
        )

    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT from_address, to_address, gas, gas_used, value FROM evm_internal_transactions '
            'WHERE parent_tx=? ORDER BY rowid',
            (parent_tx,),
        ).fetchall() == [
            ('0x227DFD9fA88bfe186682f3A45597Bac051742e5F', '0xa669e7A0d4b3e4Fa48af2dE86BD4CD7126Be4e13', '2300', '55', '967761034721284'),  # noqa: E501
            ('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1', '0x227DFD9fA88bfe186682f3A45597Bac051742e5F', '122291', '55', '967761034721284'),  # noqa: E501
            ('0xa669e7A0d4b3e4Fa48af2dE86BD4CD7126Be4e13', '0xDeEB02ADA5B089F851f2A1C0301d46631514D312', '113798', '0', '967761034721263'),  # noqa: E501
        ]
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_tx_mappings WHERE tx_id=? AND value=?',
            (parent_tx, 0),
        ).fetchone()[0] == 0


def test_repull_passes_tx_timestamp_to_internal_query(database) -> None:
    """Ensure _repull_internal_tx_data forwards the transaction timestamp as
    tx_timestamp so that indexer guards (e.g. Blockscout pre-Bedrock check)
    can gate queries correctly."""
    tx_hash = make_evm_tx_hash()
    tx = EvmTransaction(
        tx_hash=tx_hash,
        chain_id=ChainID.ETHEREUM,
        timestamp=(tx_ts := Timestamp(1600000000)),
        block_number=1,
        from_address=make_evm_address(),
        to_address=make_evm_address(),
        value=0,
        gas=1,
        gas_price=1,
        gas_used=1,
        input_data=b'',
        nonce=1,
    )
    captured_kwargs: dict[str, Any] = {}

    with patch.object(DBEvmTx, 'add_or_ignore_receipt_data'):
        _repull_internal_tx_data(
            database=database,
            chains_aggregator=make_dummy_chains_aggregator(
                get_transaction_by_hash_result=(tx, {'status': '0x1'}),
                query_internal_return_value=([], None, ''),
                query_internal_hook=lambda **kwargs: captured_kwargs.update(kwargs),
            ),
            chain_id=ChainID.ETHEREUM,
            tx_hash=tx_hash,
        )

    assert captured_kwargs.get('tx_timestamp') == tx_ts
