import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.chain.ethereum.modules.lido_csm.constants import LidoCsmStakingModule
    from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmMetricsFetcher
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.lido_csm import LidoCsmNodeOperator
    from rotkehlchen.types import ChecksumEvmAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def follow_node_operator_addresses(
        db: DBLidoCsm,
        stored_address: ChecksumEvmAddress,
        followed: bool,
        node_operator_id: int,
        staking_module: LidoCsmStakingModule,
        manager: ChecksumEvmAddress,
        reward: ChecksumEvmAddress,
        is_tracked: Callable[[ChecksumEvmAddress], bool],
) -> None:
    """Keep a followed node operator under its tracked manager or, failing that, reward
    address, and drop it if neither is tracked any more.

    One added by hand under another address, such as one that only deposited bond, is left
    as it is, and is followed from then on once it is stored under one of the two.
    """
    if stored_address in (manager, reward):
        if not followed:
            db.set_node_operator_followed(
                node_operator_id=node_operator_id,
                staking_module=staking_module,
            )
        return

    if not followed:
        return

    tracked = [x for x in (manager, reward) if is_tracked(x)]
    db.move_node_operator(
        address=tracked[0] if len(tracked) != 0 else None,
        node_operator_id=node_operator_id,
        staking_module=staking_module,
    )


def follow_stored_node_operators(
        evm_inquirer: EvmNodeInquirer,
        database: DBHandler,
        metrics_fetchers: dict[LidoCsmStakingModule, LidoCsmMetricsFetcher],
        node_operators: Sequence[LidoCsmNodeOperator],
) -> None:
    """Move or drop the stored node operators whose manager or reward address changed.

    A change is only emitted by the new address's confirm transaction, which is not in the
    history of a user who handed the operator off, so it is checked here against the module.
    """
    if len(node_operators) == 0:
        return

    calls = [(
        (contract := metrics_fetchers[entry.staking_module].module_contract).address,
        contract.encode(
            method_name='getNodeOperatorManagementProperties',
            arguments=[entry.node_operator_id],
        ),
    ) for entry in node_operators]
    try:
        results = evm_inquirer.multicall_2(calls=calls, require_success=False)
    except RemoteError as e:
        log.error('Failed to query the addresses of the Lido CSM node operators due to %s', e)
        return

    db = DBLidoCsm(database)
    followed = db.get_followed_node_operators()
    with database.conn.read_ctx() as cursor:
        tracked = set(database.get_blockchain_accounts(cursor).eth)

    for entry, (success, output) in zip(node_operators, results, strict=True):
        if not success:
            log.error(
                'Failed to query the addresses of Lido CSM node operator %s (%s)',
                entry.node_operator_id,
                entry.staking_module.name,
            )
            continue

        manager, reward, _ = metrics_fetchers[entry.staking_module].module_contract.decode(
            result=output,
            method_name='getNodeOperatorManagementProperties',
            arguments=[entry.node_operator_id],
        )
        follow_node_operator_addresses(
            db=db,
            stored_address=entry.address,
            followed=(entry.staking_module, entry.node_operator_id) in followed,
            node_operator_id=entry.node_operator_id,
            staking_module=entry.staking_module,
            manager=manager,
            reward=reward,
            is_tracked=tracked.__contains__,
        )
