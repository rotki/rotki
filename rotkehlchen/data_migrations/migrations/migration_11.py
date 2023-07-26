import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import UpdateType
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ChainID,
    EVMTxHash,
    ExternalService,
    ExternalServiceApiCredentials,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _get_optimism_transaction_fees(
        rotki: 'Rotkehlchen',
        progress_handler: 'MigrationProgressHandler',
        txhash_to_id: dict[EVMTxHash, int],
) -> None:
    """Since we now need 1 extra column per optimism transaction we need to repull all
    optimism transactions to store the l1 gas fee"""
    db_tuples = []
    optimism_manager = rotki.chains_aggregator.get_evm_manager(ChainID.OPTIMISM)
    assert optimism_manager, 'should exist at this point'
    for txhash, txid in txhash_to_id.items():
        progress_handler.new_step(f'Fetching optimism transaction {txhash.hex()}')
        try:
            transaction, _ = optimism_manager.node_inquirer.get_transaction_by_hash(tx_hash=txhash)
        except RemoteError:
            log.error(f'Could not pull data from optimism for transaction {txhash.hex()}')
            continue

        db_tuples.append((txid, str(transaction.l1_fee)))  # type: ignore  # is optimism tx here

    with rotki.data.db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT OR IGNORE INTO optimism_transactions(tx_id, l1_fee) VALUES(?, ?)',
            db_tuples,
        )


def _detect_arbitrum_one_accounts(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # noqa: E501
    """
    Detect accounts that have activity in other evm chains and are not yet tracked.
    The reason is to start the new release with arbitrum one already detected.

    Initially we check updates for spam assets and rpc nodes. Spam assets are updated before
    accounts detection to avoid detecting accounts that only have spam assets. We also check
    for rpc nodes updates here, to avoid an edge case where a call to rpc nodes happens before the
    rpc node update task has finished.
    """
    progress_handler.new_step('Fetching new spam assets and rpc data info')
    rotki.data_updater.check_for_updates(updates=[UpdateType.SPAM_ASSETS, UpdateType.RPC_NODES])

    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.add_external_service_credentials(
            write_cursor=write_cursor,  # add temporary etherscan arbitrum one key
            credentials=[ExternalServiceApiCredentials(
                service=ExternalService.ARBITRUM_ONE_ETHERSCAN,
                api_key=ApiKey('VQUFYKKJR4RK8HFHYIJ9I93FIUVP44TN99'),  # same one in tests
            )])

    rotki.chains_aggregator.detect_evm_accounts(progress_handler, chains=[SupportedBlockchain.ARBITRUM_ONE])  # noqa: E501
    # remove temporary etherscan arbitrum one key
    rotki.data.db.delete_external_service_credentials([ExternalService.ARBITRUM_ONE_ETHERSCAN])


def data_migration_11(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.30.0
    """
    log.debug('Enter data_migration_11')
    with rotki.data.db.conn.read_ctx() as cursor:
        # We need to get the optimism transactions here in order to calculate the number of
        # steps for the migration.
        cursor.execute('SELECT tx_hash, identifier FROM evm_transactions WHERE chain_id=10')
        txhash_to_id = dict(cursor)

    # steps are: optimism txs + ethereum accounts + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
    progress_handler.set_total_steps(len(txhash_to_id) + len(rotki.chains_aggregator.accounts.eth) + 3)  # noqa: E501
    _get_optimism_transaction_fees(rotki, progress_handler, txhash_to_id)
    _detect_arbitrum_one_accounts(rotki, progress_handler)
    log.debug('Exit data_migration_11')
