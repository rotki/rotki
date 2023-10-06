import logging
from typing import TYPE_CHECKING

from rotkehlchen.data_migrations.utils import update_data_and_detect_accounts
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


def data_migration_11(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.30.0
    """
    log.debug('Enter data_migration_11')

    # steps are: ethereum accounts + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
    progress_handler.set_total_steps(len(rotki.chains_aggregator.accounts.eth) + 3)
    update_data_and_detect_accounts(
        chains=[SupportedBlockchain.ARBITRUM_ONE],
        external_service_credentials=[
            ExternalServiceApiCredentials(
                service=ExternalService.ARBITRUM_ONE_ETHERSCAN,
                api_key=ApiKey('VQUFYKKJR4RK8HFHYIJ9I93FIUVP44TN99'),  # Same api key as in tests
            ),
        ],
        rotki=rotki,
        progress_handler=progress_handler,
    )
    log.debug('Exit data_migration_11')
