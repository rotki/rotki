from typing import TYPE_CHECKING

from rotkehlchen.data_migrations.utils import update_data_and_detect_accounts
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import (
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_13(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.31.0

    Detects Gnosis and Base chain accounts that have activity and are not yet tracked.
    """
    # steps are: ethereum accounts + 3 (potentially write to db + updating spam assets and rpc nodes + new round msg)  # noqa: E501
    progress_handler.set_total_steps(len(rotki.chains_aggregator.accounts.eth) + 3)
    update_data_and_detect_accounts(
        chains=[SupportedBlockchain.GNOSIS, SupportedBlockchain.BASE],
        rotki=rotki,
        progress_handler=progress_handler,
    )
