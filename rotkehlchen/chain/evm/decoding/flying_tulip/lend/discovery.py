"""Find Flying Tulip deposits made for a beneficiary by someone else."""
import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.flying_tulip.constants import CPT_FLYING_TULIP
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_tx_hash,
    deserialize_int_from_hex_or_int,
)
from rotkehlchen.types import Location
from rotkehlchen.utils.misc import ts_now

from .constants import (
    DEPOSIT_FOR_ABI,
    FLYING_TULIP_LEND_DEPLOYMENTS,
    LAST_DEPOSIT_FOR_QUERY,
    POSITIONS_MANAGER_ABI,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.chain.evm.transactions import EvmTransactions
    from rotkehlchen.types import ChecksumEvmAddress, EVMTxHash

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Progress is saved once per chunk, so an interrupted or rate limited first scan
# still moves forward instead of restarting from the deployment block every day.
SCAN_CHUNK_BLOCKS: Final = 250_000
# The tip is scanned but never saved as done. get_logs prefers indexers, whose
# head can lag the node that reported the latest block, and the last blocks can
# still reorg. Leaving a margin means those blocks are simply looked at again.
CHECKPOINT_MARGIN_BLOCKS: Final = 300


def query_deposit_for_transactions(
        transactions: EvmTransactions,
        addresses: Sequence[ChecksumEvmAddress],
) -> None:
    """Import transactions where a tracked address got a lending deposit paid by someone else.

    `depositFor` credits the beneficiary's position while the tokens leave the payer's
    wallet, so when the payer is not tracked the transaction touches no tracked address
    at all. Transaction discovery queries per address and never returns it, and with no
    transaction there is no event, which also keeps the position out of the balances.
    The beneficiary is an indexed argument of `DepositFor`, which lets us query
    the positions manager logs for their deposits directly.

    Known lending activity or a batched live collateral check gates the historical
    scan. This discovers externally funded open positions and backfills deposits
    for closed positions whose withdrawal was found by normal transaction discovery.
    Only eligible beneficiaries are queried, each from their own checkpoint, so a
    newly discovered position does not rescan another account's old deposits.
    """
    if (deployment := FLYING_TULIP_LEND_DEPLOYMENTS.get(
            transactions.evm_inquirer.chain_id,
    )) is None or len(addresses) == 0:
        return

    inquirer, database = transactions.evm_inquirer, transactions.database
    with database.conn.read_ctx() as cursor:
        known_users = {row[0] for row in cursor.execute(
            'SELECT DISTINCT H.location_label FROM history_events H '
            'JOIN chain_events_info C ON H.identifier=C.identifier '
            'WHERE H.location=? AND C.counterparty=? AND C.address IN (?, ?)',
            (Location.from_chain_id(inquirer.chain_id).serialize_for_db(), CPT_FLYING_TULIP,
             deployment.positions_manager, deployment.leverage_engine),
        )}
    addresses = list(dict.fromkeys(addresses))
    if len(unknown_users := [address for address in addresses if address not in known_users]) != 0:
        positions_manager = EvmContract(
            address=deployment.positions_manager,
            abi=POSITIONS_MANAGER_ABI,
            deployed_block=deployment.deployment_block,
        )
        try:
            results = inquirer.multicall(calls=[
                (positions_manager.address, positions_manager.encode(
                    method_name='userCollateralAssets',
                    arguments=[address],
                )) for address in unknown_users
            ])
            known_users.update(
                address for address, result in zip(unknown_users, results, strict=True)
                if len(positions_manager.decode(
                    result=result,
                    method_name='userCollateralAssets',
                    arguments=[address],
                )[0]) != 0
            )
        except (RemoteError, DeserializationError) as e:
            log.error(
                'Could not check Flying Tulip lending positions on %s: %s',
                inquirer.chain_name, e,
            )
            return

    addresses = [address for address in addresses if address in known_users]

    if len(addresses) == 0:
        _mark_scanned(transactions=transactions)
        return

    cache_keys = {
        DBCacheDynamic.LAST_BLOCK_ID.get_db_key(
            location=inquirer.chain_name,
            location_name=LAST_DEPOSIT_FOR_QUERY,
            account_id=address,
        ): address for address in addresses
    }
    checkpoints = dict.fromkeys(addresses, deployment.deployment_block - 1)
    with database.conn.read_ctx() as cursor:
        for bindings, placeholders in get_query_chunks(list(cache_keys)):
            for key, value in cursor.execute(
                f'SELECT name, value FROM key_value_cache WHERE name IN ({placeholders})',
                bindings,
            ):
                checkpoints[cache_keys[key]] = max(int(value), deployment.deployment_block - 1)

    try:
        target_block = inquirer.get_latest_block_number()
    except RemoteError as e:
        log.error(
            'Could not get the latest %s block for the Flying Tulip deposit scan: %s',
            inquirer.chain_name, e,
        )
        return

    # Etherscan-style indexers accept one value per topic, unlike RPC topic OR-lists.
    # Filter each eligible beneficiary instead of downloading the whole market's logs.
    for beneficiary, checkpoint in checkpoints.items():
        if not _query_deposits_for_address(
                transactions=transactions,
                beneficiary=beneficiary,
                contract_address=deployment.positions_manager,
                from_block=checkpoint + 1,
                target_block=target_block,
        ):
            return

    _mark_scanned(transactions=transactions)


def _query_deposits_for_address(
        transactions: EvmTransactions,
        beneficiary: ChecksumEvmAddress,
        contract_address: ChecksumEvmAddress,
        from_block: int,
        target_block: int,
) -> bool:
    """Import one beneficiary's deposits and checkpoint only fully processed chunks."""
    inquirer, database = transactions.evm_inquirer, transactions.database
    beneficiary_topic = f'0x{"0" * 24}{beneficiary[2:].lower()}'
    save_up_to = target_block - CHECKPOINT_MARGIN_BLOCKS
    while from_block <= target_block:
        chunk_end = min(from_block + SCAN_CHUNK_BLOCKS - 1, target_block)
        try:
            log_events = inquirer.get_logs(
                contract_address=contract_address,
                abi=DEPOSIT_FOR_ABI,
                event_name='DepositFor',
                argument_filters={'beneficiary': beneficiary},
                from_block=from_block,
                to_block=chunk_end,
            )
        except RemoteError as e:
            log.error(
                'Failed to query Flying Tulip DepositFor logs for %s on %s '
                'in blocks %s to %s: %s. Continuing from there next time',
                beneficiary, inquirer.chain_name, from_block, chunk_end, e,
            )
            return False

        tx_hashes: dict[EVMTxHash, None] = {}
        for log_event in log_events:
            if len(topics := log_event['topics']) < 3:
                continue

            if topics[1].lower() == beneficiary_topic:
                continue  # the payer owns the position, so their own query finds it

            if (
                topics[2].lower() == beneficiary_topic and
                from_block <= deserialize_int_from_hex_or_int(
                    log_event['blockNumber'], 'Flying Tulip deposit block',
                ) <= chunk_end
            ):
                tx_hashes[deserialize_evm_tx_hash(log_event['transactionHash'])] = None

        for tx_hash in tx_hashes:
            log.debug(
                'Found a Flying Tulip deposit made for %s on %s at %s',
                beneficiary, inquirer.chain_name, tx_hash,
            )
            try:
                # This also maps an existing transaction to the beneficiary and flags
                # it for re-decoding. One bad hash must not drop the others.
                transactions._batch_ensure_evm_txns_in_db(  # pylint: disable=protected-access
                    tx_hashes=[tx_hash],
                    relevant_address=beneficiary,
                )
            except RemoteError as e:
                log.error(
                    'Could not fetch Flying Tulip deposit transaction %s for %s: %s. '
                    'Retrying it in the next scan',
                    tx_hash, beneficiary, e,
                )
                return False  # keep the checkpoint so this chunk runs again
            except (InputError, DeserializationError, KeyError) as e:
                log.error(  # a hash that cannot be resolved at all, e.g. reorged out
                    'Skipping Flying Tulip deposit transaction %s for %s: %s',
                    tx_hash, beneficiary, e,
                )

        # the chunk is saved as done only up to the margin, so the tip stays in
        # range of the next scan while everything below it counts as covered
        if (scanned_to := min(chunk_end, save_up_to)) >= from_block:
            with database.user_write() as write_cursor:
                database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_BLOCK_ID,
                    value=scanned_to,
                    location=inquirer.chain_name,
                    location_name=LAST_DEPOSIT_FOR_QUERY,
                    account_id=beneficiary,
                )

        from_block = chunk_end + 1

    return True


def _mark_scanned(transactions: EvmTransactions) -> None:
    """Record a successful position check and any required scan for this chain."""
    with transactions.database.user_write() as write_cursor:
        transactions.database.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_QUERY_TS,
            location=transactions.evm_inquirer.chain_name,
            location_name=LAST_DEPOSIT_FOR_QUERY,
            account_id='positions',
            value=ts_now(),
        )
