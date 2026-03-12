from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest

from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
    INTERNAL_TXS_TO_REPULL,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tasks.internal_tx_conflicts import (
    _repull_and_redecode_tx,
    repull_internal_tx_conflicts,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import ChainID, EvmTransaction, Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator


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

    with patch('rotkehlchen.tasks.internal_tx_conflicts._repull_and_redecode_tx') as repull_mock:
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),  # not used by the patched call
            limit=INTERNAL_TXS_TO_REPULL,
        )

    assert repull_mock.call_count == INTERNAL_TXS_TO_REPULL
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM evm_internal_tx_conflicts WHERE action=? AND fixed=1',
            (INTERNAL_TX_CONFLICT_ACTION_REPULL,),
        ).fetchone()[0] == INTERNAL_TXS_TO_REPULL
        assert cursor.execute(
            'SELECT COUNT(*) FROM key_value_cache WHERE name=?',
            (DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS.value,),
        ).fetchone()[0] == 1


def test_repull_internal_tx_conflicts_skip_customized(database) -> None:
    tx_hash = make_evm_tx_hash()
    with database.user_write() as write_cursor:
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
                make_evm_address(),
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

    with patch('rotkehlchen.tasks.internal_tx_conflicts._repull_and_redecode_tx') as repull_mock:
        repull_internal_tx_conflicts(
            database=database,
            chains_aggregator=cast('ChainsAggregator', object()),
            limit=INTERNAL_TXS_TO_REPULL,
        )

    assert repull_mock.call_count == 0
    with database.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT fixed FROM evm_internal_tx_conflicts WHERE transaction_hash=? AND chain=?',
            (tx_hash, ChainID.ETHEREUM.serialize_for_db()),
        ).fetchone()[0] == 0


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

    class _DummyInquirer:
        def get_transaction_by_hash(self, tx_hash):
            return tx, {'status': '0x1'}

    class _DummyTransactions:
        def __init__(self) -> None:
            self.evm_inquirer = _DummyInquirer()

        def _query_internal_transactions_for_parent_hash(self, **_kwargs):
            raise RemoteError('fetch failed')

    class _DummyChainManager:
        def __init__(self) -> None:
            self.transactions = _DummyTransactions()

    class _DummyChainsAggregator:
        def get_chain_manager(self, blockchain):
            return _DummyChainManager()

    with pytest.raises(RemoteError):
        _repull_and_redecode_tx(
            database=database,
            chains_aggregator=_DummyChainsAggregator(),  # type: ignore[arg-type]
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
