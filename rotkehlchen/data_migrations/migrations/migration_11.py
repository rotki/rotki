import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import UpdateType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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

    # steps are: ethereum accounts + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
    progress_handler.set_total_steps(len(rotki.chains_aggregator.accounts.eth) + 3)
    _detect_arbitrum_one_accounts(rotki, progress_handler)
    log.debug('Exit data_migration_11')
