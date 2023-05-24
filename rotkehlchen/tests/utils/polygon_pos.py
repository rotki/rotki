from rotkehlchen.chain.evm.types import NodeName, WeightedNode
from rotkehlchen.constants import ONE
from rotkehlchen.types import SupportedBlockchain

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
            weight=ONE,
        ), WeightedNode(
            node_info=NodeName(
                name='ankr',
                endpoint='https://rpc.ankr.com/polygon',
                owned=False,
                blockchain=SupportedBlockchain.POLYGON_POS,
            ),
            active=True,
            weight=ONE,
        ), WeightedNode(
            node_info=NodeName(
                name='alchemy',
                endpoint='https://polygon-mainnet.g.alchemy.com/v2/uNdnI7_6XXc7ayswOxtd_RuTBGojJhIf',
                owned=False,
                blockchain=SupportedBlockchain.POLYGON_POS,
            ),
            active=True,
            weight=ONE,
        ),
    )],
)
