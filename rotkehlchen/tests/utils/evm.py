
from rotkehlchen.chain.evm.types import Web3Node
from rotkehlchen.tests.utils.mock import patch_web3_request


def maybe_mock_evm_inquirer(
        should_mock,
        parent_stack,
        evm_inquirer,
        manager_connect_at_start,
        mock_data,
):
    if should_mock is False:
        return

    # we have to mock connect to given nodes, and patch their requests
    for mocked_node in manager_connect_at_start:
        web3, _ = evm_inquirer._init_web3(mocked_node.node_info)
        evm_inquirer.web3_mapping[mocked_node.node_info] = Web3Node(
            web3_instance=web3,
            is_pruned=False,
            is_archive=True,
        )
        parent_stack.enter_context(patch_web3_request(web3, mock_data))
