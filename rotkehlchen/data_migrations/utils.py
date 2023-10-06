import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import UpdateType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SUPPORTED_EVM_CHAINS, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def update_data_and_detect_accounts(
        chains: list[SUPPORTED_EVM_CHAINS],
        external_service_credentials: list[ExternalServiceApiCredentials],
        rotki: 'Rotkehlchen',
        progress_handler: 'MigrationProgressHandler',
) -> None:
    """
    Detect accounts that have activity in other evm chains and are not yet tracked.
    The reason is to start the new release with the given chain accounts already detected.

    Initially we check updates for spam assets and rpc nodes. Spam assets are updated before
    accounts detection to avoid detecting accounts that only have spam assets. We also check
    for rpc nodes updates here, to avoid an edge case where a call to rpc nodes happens before the
    rpc node update task has finished.
    """
    progress_handler.new_step('Fetching new spam assets and rpc data info')
    rotki.data_updater.check_for_updates(updates=[UpdateType.SPAM_ASSETS, UpdateType.RPC_NODES])

    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.data.db.add_external_service_credentials(
            write_cursor=write_cursor,  # add temporary etherscan key for the given chains
            credentials=external_service_credentials,
        )

    rotki.chains_aggregator.detect_evm_accounts(progress_handler, chains=chains)
    external_services = []
    for external_service, _ in external_service_credentials:
        external_services.append(external_service)

    rotki.data.db.delete_external_service_credentials(external_services)
