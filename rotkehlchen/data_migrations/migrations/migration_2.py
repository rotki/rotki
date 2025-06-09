from typing import TYPE_CHECKING

from rotkehlchen.utils.mixins.common import function_sig_key

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


def _do_query_validator_data(rotki: 'Rotkehlchen') -> None:
    """Queries validator data if needed. Also captures the lock of beacon chain
    balance queries so that they do not start unless this is finished"""
    eth2 = rotki.chains_aggregator.get_module('eth2')
    if eth2 is None:
        return

    lock_key = function_sig_key('query_eth2_balances', arguments_matter=False, skip_ignore_cache=False)  # noqa: E501
    lock = rotki.chains_aggregator.query_locks_map[lock_key]

    with lock:
        addresses = rotki.chains_aggregator.queried_addresses_for_module('eth2')
        eth2.detect_and_refresh_validators(addresses)


def data_migration_2(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:  # pylint: disable=unused-argument
    """
    At v1.23.0 we added a new eth2 validators table and all validators are detected
    from there. But for already existing addresses there is no validators detected
    and they can only be detected if balances are force queried without cache (which
    for ETH2 also detects validator deposits for all addresses)

    This migration does the same thing so that users can still see their eth2 validators
    when downloading v1.23.0 without having to do anything special

    Since this function happens at user unlock we spawn a task to do the work
    asynchronously to not slow down unlock too much.
    """
    rotki.task_manager.spawn_and_track(
        after_seconds=None,
        task_name='data migration 2',
        exception_is_error=False,
        method=_do_query_validator_data,
        rotki=rotki,
    )
