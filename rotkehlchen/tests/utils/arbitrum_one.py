from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain


def get_arbitrum_allthatnode(weight: FVal) -> WeightedNode:
    return WeightedNode(
        node_info=NodeName(
            name='allthatnode',
            endpoint='https://arbitrum-one-archive.allthatnode.com',
            owned=False,
            blockchain=SupportedBlockchain.ARBITRUM_ONE,
        ),
        active=True,
        weight=weight,
    )


ARBITRUM_ONE_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'arbitrum_one_manager_connect_at_start',
    [(
        get_arbitrum_allthatnode(FVal('0.5')),
        WeightedNode(
            node_info=NodeName(
                name='blockpi',
                endpoint='https://arbitrum.blockpi.network/v1/rpc/public',
                owned=False,
                blockchain=SupportedBlockchain.ARBITRUM_ONE,
            ),
            active=True,
            weight=FVal('0.5'),
        ),
    )],
)
