from typing import TYPE_CHECKING

from rotkehlchen.data_migrations.utils import update_data_and_detect_accounts
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.logging import enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_10(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at polygon addition. v1.29.0
    This migration duplicates accounts if active at polygon only. The reason is to
    start the new release with polygon already detected

    It also supersedes migration 8 which is removed since this one is added.
    """
    # steps are: ethereum accounts + 4 (potentially write to db + updating spam assets + polygon rpc + new round msg)  # noqa: E501
    progress_handler.set_total_steps(len(rotki.chains_aggregator.accounts.eth) + 4)

    # we published a data version of the rpc nodes that contained a wrong etherscan name for
    # polygon. this ensure that the name is correct both in the globaldb and the user db
    # after the upgrade
    progress_handler.new_step('Ensuring polygon node consistency')
    with GlobalDBHandler().conn.write_ctx() as write_cursor:
        # Update the default nodes, stored in the global DB. It is either the correct name
        # or the wrong name since when updating nodes in the globaldb we delete all the nodes
        write_cursor.execute("UPDATE default_rpc_nodes SET name='polygon pos etherscan' WHERE name='polygon etherscan'")  # noqa: E501

    update_data_and_detect_accounts(
        chains=None,
        rotki=rotki,
        progress_handler=progress_handler,
    )
