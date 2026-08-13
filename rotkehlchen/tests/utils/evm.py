
from typing import Any

from rotkehlchen.chain.mixins.rpc_nodes import RPCNode
from rotkehlchen.tests.utils.mock import patch_web3_request


def maybe_mock_evm_inquirer(
        should_mock: bool,
        parent_stack: Any,
        evm_inquirer: Any,
        manager_connect_at_start: Any,
        mock_data: Any,
) -> None:
    if should_mock is False:
        return

    # we have to mock connect to given nodes, and patch their requests
    for mocked_node in manager_connect_at_start:
        web3, _ = evm_inquirer._init_web3(mocked_node.node_info)
        evm_inquirer.rpc_mapping[mocked_node.node_info] = RPCNode(
            rpc_client=web3,
            is_pruned=False,
            is_archive=True,
        )
        parent_stack.enter_context(patch_web3_request(web3, mock_data))
