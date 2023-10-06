from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

GNOSIS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'gnosis_manager_connect_at_start',
    [(WeightedNode(
        node_info=NodeName(
            name='1rpc',
            endpoint='https://1rpc.io/gnosis',
            owned=False,
            blockchain=SupportedBlockchain.GNOSIS,
        ),
        active=True,
        weight=FVal('0.25'),
    ), WeightedNode(
        node_info=NodeName(
            name='blockpi',
            endpoint='https://gnosis.blockpi.network/v1/rpc/public',
            owned=False,
            blockchain=SupportedBlockchain.GNOSIS,
        ),
        active=True,
        weight=FVal('0.25'),
    ), WeightedNode(
        node_info=NodeName(
            name='public node',
            endpoint='https://gnosis.publicnode.com',
            owned=False,
            blockchain=SupportedBlockchain.GNOSIS,
        ),
        active=True,
        weight=FVal('0.25'),
    ), WeightedNode(
        node_info=NodeName(
            name='ankr',
            endpoint='https://rpc.ankr.com/gnosis',
            owned=False,
            blockchain=SupportedBlockchain.GNOSIS,
        ),
        active=True,
        weight=FVal('0.25'),
    ))],
)
