import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
    get_internal_tx_conflicts,
    is_tx_customized,
    set_internal_tx_conflict_fixed,
)
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChainID, EvmInternalTransaction, EVMTxHash

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _repull_and_redecode_tx(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        chain_id: 'ChainID',
        tx_hash: 'EVMTxHash',
) -> None:
    """Repull tx and internals before replacing local rows, then redecode."""
    chain = chain_id.to_blockchain()
    chain_manager = chains_aggregator.get_chain_manager(blockchain=chain)  # type: ignore[call-overload]
    try:
        if tx_hash == GENESIS_HASH:
            transaction, _ = chain_manager.transactions.ensure_genesis_tx_data_exists()
            raw_receipt_data = chain_manager.transactions.evm_inquirer.get_transaction_receipt(
                tx_hash=tx_hash,
            )
        else:
            transaction, raw_receipt_data = chain_manager.transactions.evm_inquirer.get_transaction_by_hash(  # noqa: E501
                tx_hash=tx_hash,
            )
    except (RemoteError, DeserializationError) as e:
        raise InputError(f'Failed to repull {chain.name.lower()} tx {tx_hash!s}. {e!s}') from e

    parent_hash_internal_txs: list[EvmInternalTransaction] = []
    if transaction.to_address is not None:  # internals exist only for contract interactions
        parent_hash_internal_txs, _ = chain_manager.transactions._query_internal_transactions_for_parent_hash(  # noqa: E501
            parent_tx_hash=tx_hash,
            address=None,
            return_queried_hashes=False,
            known_parent_timestamps={tx_hash: transaction.timestamp},
        )

    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'DELETE FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx_hash, chain_id.serialize_for_db()),
        )
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[transaction],
            relevant_address=None,
        )
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=chain_id,
            data=raw_receipt_data,
        )
        chain_manager.transactions._replace_internal_transactions_for_parent_hash(
            write_cursor=write_cursor,
            parent_tx_hash=tx_hash,
            transactions=parent_hash_internal_txs,
        )

    chain_manager.transactions_decoder.decode_and_get_transaction_hashes(
        tx_hashes=[tx_hash],
        send_ws_notifications=True,
        ignore_cache=True,
        delete_customized=False,
    )


def repull_internal_tx_conflicts(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        limit: int,
) -> None:
    """Process a batch of repull internal tx conflicts."""
    with database.user_write() as write_cursor:
        entries = get_internal_tx_conflicts(
            cursor=write_cursor,
            action=INTERNAL_TX_CONFLICT_ACTION_REPULL,
            fixed=False,
            limit=limit,
        )

    for chain_id, tx_hash in entries:
        with database.conn.read_ctx() as cursor:
            if is_tx_customized(cursor=cursor, tx_hash=tx_hash, chain_id=chain_id):
                continue

        try:
            _repull_and_redecode_tx(
                database=database,
                chains_aggregator=chains_aggregator,
                chain_id=chain_id,
                tx_hash=tx_hash,
            )
        except (InputError, RemoteError, DeserializationError) as e:
            log.error(
                f'Failed to repull internal tx conflict {tx_hash!s} on {chain_id.to_name()} '
                f'due to {e!s}',
            )
            continue

        with database.user_write() as write_cursor:
            set_internal_tx_conflict_fixed(
                write_cursor=write_cursor,
                tx_hash=tx_hash,
                chain_id=chain_id,
            )

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS,
            value=ts_now(),
        )
