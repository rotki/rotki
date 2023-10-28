from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.fval import FVal
from rotkehlchen.types import SupportedBlockchain

ALCHEMY_RPC_ENDPOINT = 'https://polygon-mainnet.g.alchemy.com/v2/L_vbxARvJVmxp92NMQ1V5Qw-DDEL0t59'  # added by LEF  # noqa: E501
POLYGON_POS_NODES_PARAMETERS_WITH_PRUNED_AND_NOT_ARCHIVED: tuple[str, list[tuple]] = (
    'polygon_pos_manager_connect_at_start',
    [(
        WeightedNode(
            node_info=NodeName(
                name='public node',
                endpoint='https://polygon-bor.publicnode.com',
                owned=False,
                blockchain=SupportedBlockchain.POLYGON_POS,
            ),
            active=True,
            weight=FVal('0.4'),
        ), WeightedNode(
            node_info=NodeName(
                name='ankr',
                endpoint='https://rpc.ankr.com/polygon',
                owned=False,
                blockchain=SupportedBlockchain.POLYGON_POS,
            ),
            active=True,
            weight=FVal('0.3'),
        ), WeightedNode(
            node_info=NodeName(
                name='alchemy',
                endpoint=ALCHEMY_RPC_ENDPOINT,
                owned=False,
                blockchain=SupportedBlockchain.POLYGON_POS,
            ),
            active=True,
            weight=FVal('0.3'),
        ),
    )],
)
