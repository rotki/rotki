"""Find Flying Tulip deposits made for a beneficiary by someone else."""
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final

from rotkehlchen.db.cache import DBCacheDynamic, DBCacheStatic
from rotkehlchen.errors.misc import InputError, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_tx_hash
from rotkehlchen.utils.misc import ts_now

from .constants import DEPOSIT_FOR_ABI, FLYING_TULIP_LEND_DEPLOYMENTS, LAST_DEPOSIT_FOR_QUERY

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
    The beneficiary is an indexed argument of `DepositFor`, so the positions manager
    logs are the only place it can be found.

    One scan per chain covers every tracked address, filtering the beneficiary locally.
    Filtering on chain would cost a full block range walk per address, and the protocol
    emits few of these events. Progress is still kept per address so that an account
    added later gets its own backfill from the deployment block.
    """
    if (deployment := FLYING_TULIP_LEND_DEPLOYMENTS.get(
            transactions.evm_inquirer.chain_id,
    )) is None or len(addresses) == 0:
        return

    inquirer, database = transactions.evm_inquirer, transactions.database
    with database.conn.read_ctx() as cursor:
        checkpoints = {
            address: database.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.LAST_BLOCK_ID,
                location=inquirer.chain_name,
                location_name=LAST_DEPOSIT_FOR_QUERY,
                account_id=address,
            ) or deployment.deployment_block
            for address in addresses
        }

    try:
        target_block = inquirer.get_latest_block_number()
    except RemoteError as e:
        log.error(f'Could not get the latest {inquirer.chain_name} block for the Flying Tulip deposit scan: {e!s}')  # noqa: E501
        _mark_scanned(transactions=transactions)
        return

    # beneficiaries appear as the second topic, left padded to 32 bytes
    tracked = {f'0x{"0" * 24}{address[2:].lower()}': address for address in addresses}
    from_block, save_up_to = min(checkpoints.values()), target_block - CHECKPOINT_MARGIN_BLOCKS
    while from_block <= target_block:
        chunk_end = min(from_block + SCAN_CHUNK_BLOCKS - 1, target_block)
        try:
            log_events = inquirer.get_logs(
                contract_address=deployment.positions_manager,
                abi=DEPOSIT_FOR_ABI,
                event_name='DepositFor',
                argument_filters={},
                from_block=from_block,
                to_block=chunk_end,
            )
        except RemoteError as e:
            log.error(
                f'Failed to query Flying Tulip DepositFor logs on {inquirer.chain_name} '
                f'in blocks {from_block} to {chunk_end}: {e!s}. Continuing from there next time',
            )
            break

        found: dict[ChecksumEvmAddress, list[EVMTxHash]] = defaultdict(list)
        for log_event in log_events:
            if len(topics := log_event['topics']) < 3:
                continue

            if topics[1].lower() == (beneficiary_topic := topics[2].lower()):
                continue  # the payer owns the position, so their own query finds it

            if (beneficiary := tracked.get(beneficiary_topic)) is not None:
                found[beneficiary].append(deserialize_evm_tx_hash(log_event['transactionHash']))

        for beneficiary, tx_hashes in found.items():
            for tx_hash in tx_hashes:
                log.debug(
                    f'Found a Flying Tulip deposit made for {beneficiary} on '
                    f'{inquirer.chain_name} at {tx_hash!s}',
                )
                try:
                    # this also maps an already imported transaction to the beneficiary
                    # and flags it for re-decoding, which plain importing would skip. One
                    # hash at a time so a single bad one cannot drop the others.
                    transactions._batch_ensure_evm_txns_in_db(  # pylint: disable=protected-access
                        tx_hashes=[tx_hash],
                        relevant_address=beneficiary,
                    )
                except RemoteError as e:
                    log.error(
                        f'Could not fetch Flying Tulip deposit transaction {tx_hash!s} for '
                        f'{beneficiary}: {e!s}. Retrying it in the next scan',
                    )
                    return  # keep the checkpoint where it is so this chunk runs again
                except (InputError, DeserializationError, KeyError) as e:
                    log.error(  # a hash that cannot be resolved at all, e.g. reorged out
                        f'Skipping Flying Tulip deposit transaction {tx_hash!s} for '
                        f'{beneficiary}: {e!s}',
                    )

        # the chunk is saved as done only up to the margin, so the tip stays in
        # range of the next scan while everything below it counts as covered
        if (scanned_to := min(chunk_end, save_up_to)) >= from_block:
            with database.user_write() as write_cursor:
                for address, checkpoint in checkpoints.items():
                    if checkpoint >= scanned_to:
                        continue  # this address was already scanned past here

                    checkpoints[address] = scanned_to
                    database.set_dynamic_cache(
                        write_cursor=write_cursor,
                        name=DBCacheDynamic.LAST_BLOCK_ID,
                        value=scanned_to,
                        location=inquirer.chain_name,
                        location_name=LAST_DEPOSIT_FOR_QUERY,
                        account_id=address,
                    )

        from_block = chunk_end + 1

    _mark_scanned(transactions=transactions)


def _mark_scanned(transactions: EvmTransactions) -> None:
    """Record that a scan ran, so the daily task does not start another one right away."""
    with transactions.database.user_write() as write_cursor:
        transactions.database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_FLYING_TULIP_DEPOSITS_CHECK_TS,
            value=ts_now(),
        )
