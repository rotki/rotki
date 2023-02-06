import logging
from typing import TYPE_CHECKING

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.errors.misc import InputError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_8(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at optimism addition. v1.27.0
    This migration duplicates accounts if active at optimism or avalanche.
    """
    log.debug('Enter data_migration_8')
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)

    # when we sync a remote database the migrations are executed but the chain_manager
    # has not been created yet
    if (chains_aggregator := getattr(rotki, 'chains_aggregator', None)) is not None:
        # steps are: ethereum accounts + potentially write to db + update spam assets
        progress_handler.set_total_steps(len(accounts.eth) + 2)
        filtered_result = chains_aggregator.filter_active_evm_addresses(
            accounts=accounts.eth,
            progress_handler=progress_handler,
        )
        to_add_accounts = []
        for chain, account in filtered_result:  # add them to chain aggregator
            if chain == SupportedBlockchain.ETHEREUM:
                continue

            try:
                chains_aggregator.modify_blockchain_accounts(
                    blockchain=chain,
                    accounts=[account],
                    append_or_remove='append',
                )
            except InputError:
                log.debug(f'Not adding {account} to {chain} since it already exists')
                continue
            to_add_accounts.append((chain, account))

        progress_handler.new_step('Potentially write migrated addresses to the DB')
        with rotki.data.db.user_write() as write_cursor:
            for chain, account in to_add_accounts:  # add them to the DB
                rotki.data.db.add_blockchain_accounts(
                    write_cursor=write_cursor,
                    account_data=[BlockchainAccountData(
                        chain=chain,
                        address=account,
                    )],  # not duplicating label and tags as it's chain specific
                )

        # notify frontend of which accounts were migrated, so they can order token detection
        if len(to_add_accounts) != 0:
            rotki.msg_aggregator.add_message(
                message_type=WSMessageType.EVM_ADDRESS_MIGRATION,
                data=[{'evm_chain': str(x[0]), 'address': x[1]} for x in to_add_accounts],
            )
    else:  # The only step is updating the spam assets
        progress_handler.set_total_steps(1)

    # Also update the spam assets
    progress_handler.new_step('Update the list of spam assets')
    update_spam_assets(db=rotki.data.db)
    log.debug('Exit data_migration_8')
