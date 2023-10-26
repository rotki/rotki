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


def data_migration_13(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.31.0

    Detects Gnosis and Base chain accounts that have activity and are not yet tracked.
    """
    log.debug('Enter data_migration_13')
    # steps are: ethereum accounts + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
    progress_handler.set_total_steps(len(rotki.chains_aggregator.accounts.eth) + 3)
    update_data_and_detect_accounts(
        chains=[SupportedBlockchain.GNOSIS, SupportedBlockchain.BASE],
        external_service_credentials=[  # Same api keys as in tests
            ExternalServiceApiCredentials(
                service=ExternalService.GNOSIS_ETHERSCAN,
                api_key=ApiKey('J3XEY27VIT7377G34PVPHKWG74NG9PXNSM'),
            ), ExternalServiceApiCredentials(
                service=ExternalService.BASE_ETHERSCAN,
                api_key=ApiKey('7UXQPEFX2RIQPN42VPTG72XD4E1HJS8IS6'),
            ),
        ],
        rotki=rotki,
        progress_handler=progress_handler,
    )
    log.debug('Exit data_migration_13')
