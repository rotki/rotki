import logging
from typing import TYPE_CHECKING

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
    get_internal_tx_conflicts,
    is_tx_customized,
    set_internal_tx_conflict_fixed,
    set_internal_tx_conflict_repull_error,
)
from rotkehlchen.errors.misc import DataIntegrityError, InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import (
        EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE,
        EvmInternalTransaction,
        EVMTxHash,
    )

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _repull_and_redecode_tx(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        chain_id: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
        tx_hash: 'EVMTxHash',
) -> None:
    """Repull tx and internals before replacing local rows, then redecode.

    For customized transactions only the tx data and internals are refreshed
    without redecoding, to avoid creating duplicate events alongside the
    preserved customized ones.
    """
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
    indexer_source = ''
    if transaction.to_address is not None:  # internals exist only for contract interactions
        try:
            parent_hash_internal_txs, _, indexer_source = (
                chain_manager.transactions._query_internal_transactions_for_parent_hash(
                    parent_tx_hash=tx_hash,
                    address=None,
                    return_queried_hashes=False,
                    known_parent_timestamps={tx_hash: transaction.timestamp},
                )
            )
        except (RemoteError, DeserializationError) as e:
            raise InputError(
                f'Failed to repull {chain.name.lower()} internals for tx {tx_hash!s}. {e!s}',
            ) from e

    dbevmtx = DBEvmTx(database)
    with database.user_write() as write_cursor:
        # Keep parent transaction rows/mappings intact and only refresh internals.
        # We only add missing receipt data before replacing internals.
        dbevmtx.add_or_ignore_receipt_data(
            write_cursor=write_cursor,
            chain_id=chain_id,
            data=raw_receipt_data,
        )
        chain_manager.transactions._replace_internal_transactions_for_parent_hash(
            write_cursor=write_cursor,
            parent_tx_hash=tx_hash,
            transactions=parent_hash_internal_txs,
            indexer_source=indexer_source,
        )

    with database.conn.read_ctx() as cursor:
        if is_tx_customized(cursor=cursor, tx_hash=tx_hash, chain_id=chain_id):
            return  # repulled data but skip redecoding to preserve customized events

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
    with database.conn.read_ctx() as read_cursor:
        entries = get_internal_tx_conflicts(
            cursor=read_cursor,
            action=INTERNAL_TX_CONFLICT_ACTION_REPULL,
            fixed=False,
            limit=limit,
        )

    for chain_id, tx_hash in entries:
        try:
            _repull_and_redecode_tx(
                database=database,
                chains_aggregator=chains_aggregator,
                chain_id=chain_id,
                tx_hash=tx_hash,
            )
        except (InputError, RemoteError, DeserializationError, DataIntegrityError) as e:
            error_msg = str(e)
            if isinstance(e, DataIntegrityError):
                error_msg = f'Indexer did not provide valid data: {e!s}'
            log.error(
                f'Failed to repull internal tx conflict {tx_hash!s} on {chain_id.to_name()} '
                f'due to {error_msg}',
            )
            with database.user_write() as write_cursor:
                set_internal_tx_conflict_repull_error(
                    write_cursor=write_cursor,
                    tx_hash=tx_hash,
                    chain_id=chain_id,
                    retry_ts=ts_now(),
                    error=error_msg,
                )
            continue

        with database.user_write() as write_cursor:
            set_internal_tx_conflict_fixed(
                write_cursor=write_cursor,
                tx_hash=tx_hash,
                chain_id=chain_id,
            )
        database.msg_aggregator.add_message(
            message_type=WSMessageType.INTERNAL_TX_FIXED,
            data={'chain': chain_id.to_name(), 'tx_hash': str(tx_hash)},
        )

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS,
            value=ts_now(),
        )
