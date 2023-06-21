import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.updates import UpdateType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ApiKey, ExternalService, ExternalServiceApiCredentials

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_migration_10(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at polygon addition. v1.29.0
    This migration duplicates accounts if active at polygon only. The reason is to
    start the new release with polygon already detected

    It also supersedes migration 8 which is removed since this one is added.
    """
    log.debug('Enter data_migration_10')
    # Check updates for spam assets. This happens before accounts detection to avoid
    # detecting accounts that only have spam assets.
    rotki.data_updater.check_for_updates(updates=[UpdateType.SPAM_ASSETS])
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)

    # when we sync a remote database the migrations are executed but the chain_manager
    # has not been created yet
    if (chains_aggregator := getattr(rotki, 'chains_aggregator', None)) is not None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            rotki.data.db.add_external_service_credentials(
                write_cursor=write_cursor,  # add temporary etherscan polygon key
                credentials=[ExternalServiceApiCredentials(
                    service=ExternalService.POLYGON_POS_ETHERSCAN,
                    api_key=ApiKey('1M4TM28QKJHED9QPDWXFCBEX5CK5ID3ESG'),  # same one in tests
                )])

        # steps are: ethereum accounts + potentially write to db
        progress_handler.set_total_steps(len(accounts.eth) + 1)
        chains_aggregator.detect_evm_accounts(progress_handler)

        # remove temporary etherscan polygon key
        rotki.data.db.delete_external_service_credentials([ExternalService.POLYGON_POS_ETHERSCAN])

    log.debug('Exit data_migration_10')
