import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, NamedTuple

import gevent

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.evm.constants import GENESIS_HASH
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
    clean_internal_tx_conflict,
    get_internal_tx_conflicts,
    is_tx_customized,
    set_internal_tx_conflict_fixed,
    set_internal_tx_conflict_repull_error,
)
from rotkehlchen.errors.misc import DataIntegrityError, InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import get_chunks, ts_now

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

REPULL_BATCH_SIZE: Final = 5
REPULL_LAUNCH_STAGGER_SECONDS: Final = 0.35
REPULL_BETWEEN_BATCH_DELAY_SECONDS: Final = 0.25


class _RepullResult(NamedTuple):
    """Outcome for one repull worker run."""

    chain_id: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE'
    tx_hash: 'EVMTxHash'
    needs_decode: bool
    error: str | None


def _error_to_message(error: Exception) -> str:
    """Normalize repull/decode exceptions to a user-facing retry message."""
    if isinstance(error, DataIntegrityError):
        return f'Indexer did not provide valid data: {error!s}'

    return str(error)


def _mark_internal_tx_conflict_fixed(
        database: 'DBHandler',
        chain_id: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
        tx_hash: 'EVMTxHash',
) -> None:
    """Mark a conflict as fixed and emit the INTERNAL_TX_FIXED websocket message."""
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


def _mark_internal_tx_conflict_error(
        database: 'DBHandler',
        chain_id: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
        tx_hash: 'EVMTxHash',
        error_msg: str,
) -> None:
    """Persist retry metadata for a failed repull/decode attempt."""
    with database.user_write() as write_cursor:
        set_internal_tx_conflict_repull_error(
            write_cursor=write_cursor,
            tx_hash=tx_hash,
            chain_id=chain_id,
            retry_ts=ts_now(),
            error=error_msg,
        )


def _repull_internal_tx_data(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        chain_id: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
        tx_hash: 'EVMTxHash',
) -> bool:
    """Repull tx and internals before replacing local rows.

    For customized transactions only the tx data and internals are refreshed
    and this function returns True so that callers can skip redecoding.
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
                    tx_timestamp=transaction.timestamp,
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
        return is_tx_customized(cursor=cursor, tx_hash=tx_hash, chain_id=chain_id)


def _repull_single_conflict(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        chain_id: 'EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE',
        tx_hash: 'EVMTxHash',
) -> _RepullResult:
    """Repull one conflict and return a structured result for batch orchestration."""
    try:
        is_customized = _repull_internal_tx_data(
            database=database,
            chains_aggregator=chains_aggregator,
            chain_id=chain_id,
            tx_hash=tx_hash,
        )
    except (InputError, DataIntegrityError) as e:
        error_msg = _error_to_message(e)
        log.error(
            f'Failed to repull internal tx conflict {tx_hash!s} on '
            f'{chain_id.to_name()} due to {error_msg}',
        )
        return _RepullResult(
            chain_id=chain_id,
            tx_hash=tx_hash,
            needs_decode=False,
            error=error_msg,
        )

    return _RepullResult(
        chain_id=chain_id,
        tx_hash=tx_hash,
        needs_decode=is_customized is False,
        error=None,
    )


def _process_repull_conflicts(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        repull_entries: list[tuple['EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', 'EVMTxHash']],
        ) -> dict['EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', list['EVMTxHash']]:
    """Run staggered repull workers and return tx hashes that need decode per chain."""
    to_decode_by_chain: dict[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, list[EVMTxHash]] = defaultdict(list)  # noqa: E501
    repull_chunks = list(get_chunks(repull_entries, REPULL_BATCH_SIZE))
    for chunk_idx, chunk in enumerate(repull_chunks):
        greenlets: list[tuple[gevent.Greenlet, EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash]] = []  # noqa: E501
        for launch_idx, (chain_id, tx_hash) in enumerate(chunk):
            greenlets.append((
                gevent.spawn_later(
                    launch_idx * REPULL_LAUNCH_STAGGER_SECONDS,
                    _repull_single_conflict,
                    database=database,
                    chains_aggregator=chains_aggregator,
                    chain_id=chain_id,
                    tx_hash=tx_hash,
                ),
                chain_id,
                tx_hash,
            ))

        gevent.joinall([greenlet for greenlet, _, _ in greenlets], raise_error=False)
        for greenlet, chain_id, tx_hash in greenlets:
            if (exception := greenlet.exception) is not None:
                error_msg = _error_to_message(exception)
                log.error(
                    f'Unexpected failure in repull worker for internal tx conflict '
                    f'{tx_hash!s} on {chain_id.to_name()} due to {error_msg}',
                )
                _mark_internal_tx_conflict_error(
                    database=database,
                    chain_id=chain_id,
                    tx_hash=tx_hash,
                    error_msg=error_msg,
                )
                continue

            if (result := greenlet.value) is None:
                _mark_internal_tx_conflict_error(
                    database=database,
                    chain_id=chain_id,
                    tx_hash=tx_hash,
                    error_msg='Repull worker finished without a result',
                )
                continue

            if result.error is not None:
                _mark_internal_tx_conflict_error(
                    database=database,
                    chain_id=result.chain_id,
                    tx_hash=result.tx_hash,
                    error_msg=result.error,
                )
                continue

            if result.needs_decode:
                to_decode_by_chain[result.chain_id].append(result.tx_hash)
                continue

            _mark_internal_tx_conflict_fixed(
                database=database,
                chain_id=result.chain_id,
                tx_hash=result.tx_hash,
            )

        if chunk_idx < len(repull_chunks) - 1:
            gevent.sleep(REPULL_BETWEEN_BATCH_DELAY_SECONDS)

    return to_decode_by_chain


def _decode_conflicts_in_batches(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        to_decode_by_chain: dict['EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE', list['EVMTxHash']],
) -> None:
    """Decode queued conflict tx hashes per-chain in a single batch call per chain."""
    for chain_id, tx_hashes in to_decode_by_chain.items():
        chain = chain_id.to_blockchain()
        chain_manager = chains_aggregator.get_chain_manager(blockchain=chain)  # type: ignore[call-overload]
        try:
            chain_manager.transactions_decoder.decode_and_get_transaction_hashes(
                tx_hashes=tx_hashes,
                send_ws_notifications=True,
                ignore_cache=True,
                delete_customized=False,
            )
        except (InputError, RemoteError, DeserializationError, DataIntegrityError) as e:
            log.error(
                f'Failed batch decode of internal tx conflicts on {chain_id.to_name()} due '
                f'to {_error_to_message(e)}. Purging cached decoded events for queued txs',
            )
            for tx_hash in tx_hashes:
                try:
                    with database.conn.read_ctx() as cursor:
                        context = chain_manager.transactions_decoder._load_transaction_context(
                            cursor=cursor,
                            tx_hash=tx_hash,
                        )
                    chain_manager.transactions_decoder._maybe_load_or_purge_events_from_db(
                        transaction=context.transaction,
                        tx_ref=tx_hash,
                        location=Location.from_chain_id(chain_id),
                        ignore_cache=True,
                        delete_customized=False,
                    )
                except (InputError, RemoteError, DeserializationError, DataIntegrityError) as purge_error:  # noqa: E501
                    _mark_internal_tx_conflict_error(
                        database=database,
                        chain_id=chain_id,
                        tx_hash=tx_hash,
                        error_msg=_error_to_message(purge_error),
                    )
                else:
                    _mark_internal_tx_conflict_fixed(
                        database=database,
                        chain_id=chain_id,
                        tx_hash=tx_hash,
                    )
            continue

        for tx_hash in tx_hashes:
            _mark_internal_tx_conflict_fixed(
                database=database,
                chain_id=chain_id,
                tx_hash=tx_hash,
            )


def repull_internal_tx_conflicts(
        database: 'DBHandler',
        chains_aggregator: 'ChainsAggregator',
        limit: int,
) -> None:
    """Process a batch of internal tx conflicts (both repull and fix_redecode)."""
    with database.conn.read_ctx() as read_cursor:
        entries = get_internal_tx_conflicts(
            cursor=read_cursor,
            fixed=False,
            limit=limit,
        )

    repull_entries: list[tuple[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, EVMTxHash]] = []
    to_decode_by_chain: dict[EVM_CHAIN_IDS_WITH_TRANSACTIONS_TYPE, list[EVMTxHash]] = defaultdict(list)  # noqa: E501
    for chain_id, tx_hash, action in entries:
        if action == INTERNAL_TX_CONFLICT_ACTION_REPULL:
            repull_entries.append((chain_id, tx_hash))
        else:  # fix_redecode
            with database.user_write() as write_cursor:
                clean_internal_tx_conflict(
                    write_cursor=write_cursor,
                    tx_hash=tx_hash,
                    chain_id=chain_id,
                )
            to_decode_by_chain[chain_id].append(tx_hash)

    for chain_id, tx_hashes in _process_repull_conflicts(
        database=database,
        chains_aggregator=chains_aggregator,
        repull_entries=repull_entries,
    ).items():
        to_decode_by_chain[chain_id].extend(tx_hashes)
    _decode_conflicts_in_batches(
        database=database,
        chains_aggregator=chains_aggregator,
        to_decode_by_chain=to_decode_by_chain,
    )

    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_INTERNAL_TX_CONFLICTS_REPULL_TS,
            value=ts_now(),
        )
