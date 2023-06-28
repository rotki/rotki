import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.updates import UpdateType
from rotkehlchen.globaldb.handler import GlobalDBHandler
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
    with rotki.data.db.conn.read_ctx() as cursor:
        accounts = rotki.data.db.get_blockchain_accounts(cursor)
    # steps are: ethereum accounts + potentially write to db + updating spam assets + polygon rpc
    progress_handler.set_total_steps(len(accounts.eth) + 4)

    # Check updates for spam assets. This happens before accounts detection to avoid
    # detecting accounts that only have spam assets.
    progress_handler.new_step('Fetching new spam assets info')
    rotki.data_updater.check_for_updates(updates=[UpdateType.SPAM_ASSETS])

    # we published a data version of the rpc nodes that contained a wrong etherscan name for
    # polygon. this ensure that the name is correct both in the globaldb and the user db
    # after the upgrade
    progress_handler.new_step('Ensuring polygon node consistency')
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # Update the default nodes, stored in the global DB. It is either the correct name
        # or the wrong name since when updating nodes in the globaldb we delete all the nodes
        write_cursor.execute('UPDATE default_rpc_nodes SET name="polygon pos etherscan" WHERE name="polygon etherscan"')  # noqa: E501
    with rotki.data.db.conn.write_ctx() as write_cursor:
        # "polygon pos etherscan" exists here because it has been added by the db
        #  upgrade. We only need to delete the bad node if exists
        write_cursor.execute('DELETE FROM rpc_nodes WHERE name="polygon etherscan"')

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
        chains_aggregator.detect_evm_accounts(progress_handler)

        # remove temporary etherscan polygon key
        rotki.data.db.delete_external_service_credentials([ExternalService.POLYGON_POS_ETHERSCAN])

    log.debug('Exit data_migration_10')
